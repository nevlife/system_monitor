import math

from system_monitor.core.map_frame import UtmMapFrame


def test_datum_is_the_origin_and_axes_point_east_and_north():
    frame = UtmMapFrame(35.9, 128.8)
    x, y = frame.to_map(35.9, 128.8)
    assert abs(x) < 1e-6 and abs(y) < 1e-6
    x, y = frame.to_map(35.9 + 0.001, 128.8)
    assert math.isclose(y, 110.9, rel_tol=0.01) and abs(x) < 3.0
    x, y = frame.to_map(35.9, 128.8 + 0.001)
    assert math.isclose(x, 90.2, rel_tol=0.01) and abs(y) < 3.0
