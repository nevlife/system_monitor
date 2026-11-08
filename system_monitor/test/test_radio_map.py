import math

from system_monitor.core import link
from system_monitor.core.radio_map import predict
from system_monitor.core.radio_map import RadioMap
from system_monitor.core.radio_map import velocity_offsets

GOOD = {'rtt_p95_ms': 60.0, 'loss_percent': 0.0, 'longest_outage_ms': 80.0}
BAD = {'rtt_p95_ms': 500.0, 'loss_percent': 10.0, 'longest_outage_ms': 900.0}
LAT0, LON0 = 37.0, 127.0
M_PER_DEG_LAT = 111320.0


def north(m):
    return LAT0 + m / M_PER_DEG_LAT


def degraded(s):
    return link.is_degraded(s, 40.0)


def test_warns_before_a_bad_cell_on_the_way():
    rmap = RadioMap(cell_m=5.0, max_age_s=100.0)
    for m in range(0, 40):
        rmap.add(0.0, north(m), LON0, 1.0, BAD if 20 <= m < 25 else GOOD)
    pr = predict(rmap, 1.0, north(2), LON0, velocity_offsets(0.0, 2.0, 15.0, 1.0), degraded)
    assert pr['degraded_in_s'] == 9.0
    assert pr['worst_longest_outage_ms'] == 900.0
    away = predict(rmap, 1.0, north(2), LON0, velocity_offsets(0.0, -2.0, 15.0, 1.0), degraded)
    assert math.isnan(away['degraded_in_s'])


def test_old_samples_are_forgotten():
    rmap = RadioMap(cell_m=5.0, max_age_s=10.0)
    rmap.add(0.0, LAT0, LON0, 0.0, BAD)
    assert rmap.stats(rmap.cell_of(LAT0, LON0), now=5.0)['samples'] == 1
    assert rmap.stats(rmap.cell_of(LAT0, LON0), now=20.0) is None


def test_save_and_load(tmp_path):
    rmap = RadioMap(cell_m=5.0, max_age_s=100.0)
    rmap.add(0.0, north(7), LON0, 1.0, BAD)
    rmap.save(tmp_path / 'map.json')
    back = RadioMap.load(tmp_path / 'map.json', max_age_s=100.0)
    assert back.stats(back.cell_of(north(7), LON0), 1.0)['rtt_p95_ms'] == 500.0
