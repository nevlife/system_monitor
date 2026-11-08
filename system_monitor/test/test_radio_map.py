from system_monitor.core.radio_map import RadioMap

GOOD = {'rtt_p95_ms': 60.0, 'loss_percent': 0.0, 'longest_outage_ms': 80.0}
BAD = {'rtt_p95_ms': 500.0, 'loss_percent': 10.0, 'longest_outage_ms': 900.0}
LAT0, LON0 = 37.0, 127.0
M_PER_DEG_LAT = 111320.0


def north(m):
    return LAT0 + m / M_PER_DEG_LAT


def test_cells_keep_their_own_samples():
    rmap = RadioMap(cell_m=5.0, max_age_s=100.0, origin=(LAT0, LON0))
    for m in range(0, 20):
        rmap.add(0.0, north(m + 0.5), LON0, BAD if 10 <= m < 15 else GOOD)
    assert rmap.stats(rmap.cell_of(north(12), LON0), 1.0)['rtt_p95_ms'] == 500.0
    assert rmap.stats(rmap.cell_of(north(3), LON0), 1.0)['rtt_p95_ms'] == 60.0
    assert rmap.stats(rmap.cell_of(north(30), LON0), 1.0) is None


def test_old_samples_are_forgotten():
    rmap = RadioMap(cell_m=5.0, max_age_s=10.0)
    rmap.add(0.0, LAT0, LON0, BAD)
    assert rmap.stats(rmap.cell_of(LAT0, LON0), now=5.0)['samples'] == 1
    assert rmap.stats(rmap.cell_of(LAT0, LON0), now=20.0) is None


def test_save_and_load(tmp_path):
    rmap = RadioMap(cell_m=5.0, max_age_s=100.0)
    rmap.add(0.0, north(7), LON0, BAD)
    rmap.save(tmp_path / 'map.json')
    back = RadioMap.load(tmp_path / 'map.json', max_age_s=100.0)
    assert back.stats(back.cell_of(north(7), LON0), 1.0)['rtt_p95_ms'] == 500.0
