"""
Radio environment map: link samples kept per grid cell, for predicting the link ahead.

Predictive QoS for tele-operated driving (5GAA) looks up the quality measured earlier at the
places the vehicle is about to reach. Each cell keeps its newest samples and drops old ones, as
networks change over weeks. Location alone predicts poorly (Lumos5G), so samples also keep the
speed they were taken at. The lookahead follows the current velocity.
"""

from collections import deque
import json
import math

METRICS = ('rtt_p95_ms', 'loss_percent', 'longest_outage_ms')
EARTH_M_PER_DEG = 111320.0


class RadioMap:
    def __init__(self, cell_m, max_age_s, per_cell=50, origin=None):
        self.cell_m = cell_m
        self.max_age_s = max_age_s
        self.per_cell = per_cell
        self.origin = origin
        self.cells = {}

    def _xy(self, lat, lon):
        """Metres east and north of the origin; flat-earth, fine over a few kilometres."""
        lat0, lon0 = self.origin
        return ((lon - lon0) * EARTH_M_PER_DEG * math.cos(math.radians(lat0)),
                (lat - lat0) * EARTH_M_PER_DEG)

    def cell_of(self, lat, lon):
        x, y = self._xy(lat, lon)
        return int(math.floor(x / self.cell_m)), int(math.floor(y / self.cell_m))

    def add(self, t, lat, lon, speed_mps, link):
        if self.origin is None:
            self.origin = (lat, lon)
        key = self.cell_of(lat, lon)
        cell = self.cells.setdefault(key, deque(maxlen=self.per_cell))
        cell.append([t, speed_mps] + [link[m] for m in METRICS])

    def stats(self, key, now):
        """Return the 90th percentile of each metric over the cell's recent samples, or None."""
        rows = [r for r in self.cells.get(key, ()) if now - r[0] <= self.max_age_s]
        if not rows:
            return None
        out = {'samples': len(rows)}
        for i, m in enumerate(METRICS):
            values = sorted(r[2 + i] for r in rows if not math.isnan(r[2 + i]))
            out[m] = values[min(len(values) - 1, int(0.9 * len(values)))] if values else math.nan
        return out

    def lookahead(self, now, lat, lon, offsets):
        """Yield (seconds ahead, cell stats or None) for (dt, east m, north m) offsets."""
        if self.origin is None:
            return
        x, y = self._xy(lat, lon)
        seen = set()
        for dt, east, north in offsets:
            key = (int(math.floor((x + east) / self.cell_m)),
                   int(math.floor((y + north) / self.cell_m)))
            if key not in seen:
                seen.add(key)
                yield dt, self.stats(key, now)

    def save(self, path):
        with open(path, 'w') as f:
            json.dump({'cell_m': self.cell_m, 'origin': self.origin,
                       'cells': [[k[0], k[1], list(v)] for k, v in self.cells.items()]}, f)

    @classmethod
    def load(cls, path, max_age_s, per_cell=50):
        with open(path) as f:
            data = json.load(f)
        m = cls(data['cell_m'], max_age_s, per_cell, tuple(data['origin']))
        for i, j, rows in data['cells']:
            m.cells[(i, j)] = deque(rows, maxlen=per_cell)
        return m


def velocity_offsets(east_mps, north_mps, horizon_s, step_s):
    """Offsets along a straight line at the current velocity."""
    return [(k * step_s, east_mps * k * step_s, north_mps * k * step_s)
            for k in range(int(horizon_s / step_s) + 1)]


def predict(radio_map, now, lat, lon, offsets, degraded):
    """Summarize the cells at the offsets ahead; degraded(stats) decides when trouble starts."""
    first = math.nan
    worst = {m: math.nan for m in METRICS}
    known = 0
    for dt, s in radio_map.lookahead(now, lat, lon, offsets):
        if s is None:
            continue
        known += s['samples']
        for m in METRICS:
            worst[m] = max(worst[m], s[m]) if not math.isnan(worst[m]) else s[m]
        if math.isnan(first) and degraded(s):
            first = dt
    return {'degraded_in_s': first, 'samples_ahead': known, **{'worst_' + m: worst[m]
                                                               for m in METRICS}}
