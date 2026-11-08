import math

from system_monitor.core import link

NO_MODEM = {'rsrp_dbm': math.nan, 'sinr_db': math.nan}
MINS = {'rtt': 20.0, 'up': 15.0, 'down': 5.0}


def test_steady_link():
    probes = [(i * 0.1, 20.0 + i % 2, 15.0 + i % 2, 5.0) for i in range(10)]
    s = link.summarize(probes, now=1.0, mins=MINS)
    assert s['loss_percent'] == 0.0
    assert s['rtt_p50_ms'] == 21.0
    assert s['jitter_ms'] == 1.0
    assert s['longest_outage_ms'] < 150
    assert link.diagnose(s, NO_MODEM, cell_changed=False) == 'OK'


def test_unanswered_probe_counts_as_lost_only_after_the_timeout():
    probes = [(0.0, 20.0, 15.0, 5.0), (0.1, None, None, None), (1.5, None, None, None)]
    s = link.summarize(probes, now=1.6, mins=MINS)
    assert s['probes_lost'] == 1
    assert s['loss_percent'] == 50.0


def test_outage_runs_to_now_while_replies_are_missing():
    probes = [(0.0, 20.0, 15.0, 5.0), (0.1, None, None, None), (0.2, None, None, None)]
    s = link.summarize(probes, now=2.02, mins=MINS)
    assert math.isclose(s['longest_outage_ms'], 2000.0)


def test_no_reply_at_all_is_no_link():
    none = (None, None, None)
    s = link.summarize([(0.0, *none), (0.1, *none)], now=3.0,
                       mins={'rtt': math.inf, 'up': math.inf, 'down': math.inf})
    assert link.diagnose(s, NO_MODEM, cell_changed=False) == 'NO_LINK'


def test_causes_follow_the_modem_view():
    bad = link.summarize([(0.0, 20.0, 15.0, 5.0), (0.1, 400.0, 395.0, 5.0)], now=1.0, mins=MINS)
    assert bad['uplink_queue_p95_ms'] == 380.0
    assert bad['downlink_queue_p95_ms'] == 0.0
    assert link.diagnose(bad, NO_MODEM, cell_changed=True) == 'HANDOVER'
    assert link.diagnose(bad, {'rsrp_dbm': -118.0, 'sinr_db': 5.0}, False) == 'WEAK_SIGNAL'
    assert link.diagnose(bad, {'rsrp_dbm': -90.0, 'sinr_db': -3.0}, False) == 'INTERFERENCE'
    assert link.diagnose(bad, {'rsrp_dbm': -90.0, 'sinr_db': 12.0}, False) == 'CONGESTION'
    assert link.diagnose(bad, NO_MODEM, cell_changed=False) == 'DEGRADED'


def test_probes_round_trip_through_an_echo_socket():
    import socket
    import struct
    import time

    echo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    echo.bind(('127.0.0.1', 0))
    echo.settimeout(0.05)
    prober = link.LinkProber('127.0.0.1', echo.getsockname()[1], rate_hz=50, window_s=5)
    end = time.monotonic() + 0.5
    while time.monotonic() < end:
        try:
            data, addr = echo.recvfrom(64)
            echo.sendto(data + struct.pack('<Q', time.time_ns()), addr)
        except socket.timeout:
            pass
    s = prober.sample()
    prober.close()
    echo.close()
    assert s['probes_replied'] >= 20
    assert s['probes_lost'] == 0
