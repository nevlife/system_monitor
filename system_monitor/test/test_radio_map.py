import math

from system_monitor.core import link
from system_monitor.core.radio_map import predict
from system_monitor.core.radio_map import RadioMap
from system_monitor.core.radio_map import route_offsets
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


def test_route_turns_where_a_straight_line_would_not():
    rmap = RadioMap(cell_m=5.0, max_age_s=100.0, origin=(LAT0, LON0))
    east = 111320.0 * math.cos(math.radians(LAT0))
    # Driving north, the route turns east at 10 m; the bad cell is 20 m east of the corner.
    for m in range(0, 40):
        # Half a metre in, so no sample sits on a cell border.
        rmap.add(0.0, north(10.5), LON0 + (m + 0.5) / east, 1.0, BAD if 20 <= m < 25 else GOOD)
        rmap.add(0.0, north(m + 0.5), LON0 + 0.5 / east, 1.0, GOOD)
    route = [(0.0, float(y)) for y in range(0, 11)] + [(float(x), 10.0) for x in range(1, 40)]
    here = (0.0, 2.0)
    along = predict(rmap, 1.0, north(2), LON0, route_offsets(route, here, 2.0, 20.0, 1.0),
                    degraded)
    straight = predict(rmap, 1.0, north(2), LON0, velocity_offsets(0.0, 2.0, 20.0, 1.0), degraded)
    assert along['degraded_in_s'] == 14.0
    assert math.isnan(straight['degraded_in_s'])


def test_far_from_the_route_gives_no_offsets():
    assert route_offsets([(0.0, 0.0), (0.0, 10.0)], (50.0, 0.0), 1.0, 5.0, 1.0) is None
