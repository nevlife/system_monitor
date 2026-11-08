"""
Link quality towards a remote echo server, measured like irtt.

UDP probes leave on a fixed period whether or not replies come back, so a stall shows up as a
run of late or missing replies instead of slowing the probing down.

The echo server (link_echo) returns each datagram to its sender, which also works from behind a
cellular NAT, with its own receive time appended as STAMP reflectors do. The two clocks differ by
an unknown offset, but it is the same for every probe, so the one-way delay above its own
minimum is the queueing in that direction without any clock synchronization.
"""

from collections import deque
import math
import socket
import struct
import threading
import time

PROBE = struct.Struct('<IQQ')  # sequence number, send time: monotonic ns, wall clock ns
STAMP = struct.Struct('<Q')  # echo's wall clock ns on receipt

# A reply later than this counts as lost.
REPLY_TIMEOUT_S = 1.0
# Degradation thresholds for diagnose().
LOSS_PERCENT = 2.0
RTT_EXCESS_MS = 100.0
OUTAGE_MS = 300.0
WEAK_RSRP_DBM = -110.0
LOW_SINR_DB = 0.0


class LinkProber:
    def __init__(self, host, port, rate_hz, window_s):
        self.addr = (host, port)
        self.period = 1.0 / rate_hz
        self.window_s = window_s
        self.lock = threading.Lock()
        # seq -> [send time, rtt, uplink, downlink]; delays in ms, None until the reply
        self.probes = {}
        self.order = deque()
        self.mins = {'rtt': math.inf, 'up': math.inf, 'down': math.inf}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.period)
        self.running = True
        self.threads = [
            threading.Thread(target=self._send_loop, daemon=True),
            threading.Thread(target=self._recv_loop, daemon=True),
        ]
        for t in self.threads:
            t.start()

    def close(self):
        self.running = False
        for t in self.threads:
            t.join()
        self.sock.close()

    def _send_loop(self):
        seq = 0
        next_send = time.monotonic()
        while self.running:
            now = time.monotonic()
            with self.lock:
                self.probes[seq] = [now, None, None, None]
                self.order.append(seq)
            try:
                self.sock.sendto(PROBE.pack(seq, time.monotonic_ns(), time.time_ns()), self.addr)
            except OSError:
                # No route while the link is down; the probe counts as lost.
                pass
            seq = (seq + 1) & 0xFFFFFFFF
            next_send += self.period
            time.sleep(max(0.0, next_send - time.monotonic()))

    def _recv_loop(self):
        while self.running:
            try:
                data = self.sock.recv(64)
            except (socket.timeout, OSError):
                continue
            if len(data) < PROBE.size + STAMP.size:
                continue
            seq, sent_mono, sent_wall = PROBE.unpack_from(data)
            (echoed,) = STAMP.unpack_from(data, PROBE.size)
            delays = ((time.monotonic_ns() - sent_mono) / 1e6, (echoed - sent_wall) / 1e6,
                      (time.time_ns() - echoed) / 1e6)
            with self.lock:
                probe = self.probes.get(seq)
                if probe is not None and probe[1] is None:
                    probe[1:] = delays
                    for key, value in zip(('rtt', 'up', 'down'), delays):
                        self.mins[key] = min(self.mins[key], value)

    def sample(self, now=None):
        """Summarize the probes sent within the last window_s."""
        now = time.monotonic() if now is None else now
        with self.lock:
            while self.order and now - self.probes[self.order[0]][0] > self.window_s:
                del self.probes[self.order.popleft()]
            probes = [tuple(self.probes[s]) for s in self.order]
            mins = dict(self.mins)
        return summarize(probes, now, mins)


def summarize(probes, now, mins):
    """Summarize (send time s, rtt, uplink, downlink) probes in send order; mins per delay."""
    settled = [p for p in probes if p[1] is not None or now - p[0] > REPLY_TIMEOUT_S]
    replied = [p for p in settled if p[1] is not None]
    rtts = [p[1] for p in replied]
    lost = len(settled) - len(rtts)
    replies = sorted(p[0] + p[1] / 1000 for p in probes if p[1] is not None)
    # Longest time without a reply, including the open gap up to the oldest unanswered probe.
    edges = ([probes[0][0]] if probes else []) + replies
    pending = [p for p in probes if p[1] is None]
    if pending:
        edges.append(now)
    outage = max((b - a for a, b in zip(edges, edges[1:])), default=0.0)
    ordered = sorted(rtts)
    return {
        'probes_sent': len(probes),
        'probes_lost': lost,
        'probes_replied': len(rtts),
        'loss_percent': 100.0 * lost / len(settled) if settled else math.nan,
        'rtt_p50_ms': percentile(ordered, 0.50),
        'rtt_p95_ms': percentile(ordered, 0.95),
        'rtt_max_ms': ordered[-1] if ordered else math.nan,
        'rtt_min_ever_ms': mins['rtt'] if mins['rtt'] < math.inf else math.nan,
        'uplink_queue_p95_ms': percentile(sorted(p[2] for p in replied), 0.95) - mins['up'],
        'downlink_queue_p95_ms': percentile(sorted(p[3] for p in replied), 0.95) - mins['down'],
        'jitter_ms': (
            sum(abs(b - a) for a, b in zip(rtts, rtts[1:])) / (len(rtts) - 1)
            if len(rtts) > 1
            else math.nan
        ),
        'longest_outage_ms': outage * 1000,
    }


def percentile(ordered, q):
    if not ordered:
        return math.nan
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def is_degraded(stats, baseline_rtt_ms):
    """Tell whether loss, queueing above the baseline round trip, or an outage is too high."""
    return (
        stats['loss_percent'] > LOSS_PERCENT
        or stats['rtt_p95_ms'] - baseline_rtt_ms > RTT_EXCESS_MS
        or stats['longest_outage_ms'] > OUTAGE_MS
    )


def diagnose(link, modem, cell_changed):
    """Name the most likely cause of a degraded link from the probes and the modem's view."""
    if link['probes_lost'] and not link['probes_replied']:
        return 'NO_LINK'
    if not is_degraded(link, link['rtt_min_ever_ms']):
        return 'OK'
    if cell_changed:
        return 'HANDOVER'
    if modem['rsrp_dbm'] < WEAK_RSRP_DBM:
        return 'WEAK_SIGNAL'
    if modem['sinr_db'] < LOW_SINR_DB:
        return 'INTERFERENCE'
    if not math.isnan(modem['rsrp_dbm']):
        # Good signal yet a degraded link: the cell or the core network is busy.
        return 'CONGESTION'
    return 'DEGRADED'
