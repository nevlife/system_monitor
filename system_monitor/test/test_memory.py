from types import SimpleNamespace

from system_monitor.core import memory


def test_dynamic_metrics_map_psutil_fields(monkeypatch):
    vm = SimpleNamespace(
        total=100,
        available=60,
        used=30,
        free=10,
        percent=40.0,
        active=20,
        inactive=5,
        buffers=1,
        cached=2,
        shared=3,
        slab=4,
    )
    swap = SimpleNamespace(total=50, used=10, free=40, percent=20.0, sin=7, sout=8)
    monkeypatch.setattr(memory.psutil, 'virtual_memory', lambda: vm)
    monkeypatch.setattr(memory.psutil, 'swap_memory', lambda: swap)

    data = memory.get_memory_dynamic_metrics()

    assert data == {
        'total': 100,
        'available': 60,
        'used': 30,
        'free': 10,
        'percent': 40.0,
        'active': 20,
        'inactive': 5,
        'buffers': 1,
        'cached': 2,
        'shared': 3,
        'slab': 4,
        'swap_total': 50,
        'swap_used': 10,
        'swap_free': 40,
        'swap_percent': 20.0,
        'swap_sin': 7,
        'swap_sout': 8,
    }
