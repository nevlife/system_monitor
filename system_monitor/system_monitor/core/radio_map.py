"""
Radio environment map: link samples kept per grid cell of latitude and longitude.

Drive tests map coverage this way, and predictive QoS for tele-operated driving (5GAA) builds on
such maps. Each cell keeps its newest samples and ignores old ones, as networks change over weeks.
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

    def add(self, t, lat, lon, link):
        if self.origin is None:
            self.origin = (lat, lon)
        key = self.cell_of(lat, lon)
        cell = self.cells.setdefault(key, deque(maxlen=self.per_cell))
        cell.append([t] + [link[m] for m in METRICS])

    def stats(self, key, now):
        """Return the 90th percentile of each metric over the cell's recent samples, or None."""
        rows = [r for r in self.cells.get(key, ()) if now - r[0] <= self.max_age_s]
        if not rows:
            return None
        out = {'samples': len(rows)}
        for i, m in enumerate(METRICS):
            values = sorted(r[1 + i] for r in rows if not math.isnan(r[1 + i]))
            out[m] = values[min(len(values) - 1, int(0.9 * len(values)))] if values else math.nan
        return out

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
