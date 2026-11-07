from types import SimpleNamespace

from system_monitor.core import disk


def test_inaccessible_partition_is_reported_empty(monkeypatch):
    monkeypatch.setattr(
        disk.psutil,
        'disk_partitions',
        lambda all: [SimpleNamespace(mountpoint='/'), SimpleNamespace(mountpoint='/media/gone')],
    )

    def disk_usage(mountpoint):
        if mountpoint == '/media/gone':
            raise FileNotFoundError(mountpoint)
        return SimpleNamespace(total=100, used=25, free=75, percent=25.0)

    monkeypatch.setattr(disk.psutil, 'disk_usage', disk_usage)

    assert disk.get_disk_usage_per_partition() == [
        {
            'mountpoint': '/',
            'total_bytes': 100,
            'used_bytes': 25,
            'free_bytes': 75,
            'percent': 25.0,
            'accessible': True,
        },
        {
            'mountpoint': '/media/gone',
            'total_bytes': 0,
            'used_bytes': 0,
            'free_bytes': 0,
            'percent': 0.0,
            'accessible': False,
        },
    ]


def test_io_total_maps_psutil_fields(monkeypatch):
    io = SimpleNamespace(
        read_count=1,
        write_count=2,
        read_bytes=3,
        write_bytes=4,
        read_time=5,
        write_time=6,
        busy_time=7,
    )
    monkeypatch.setattr(disk.psutil, 'disk_io_counters', lambda perdisk: io)

    assert disk.get_disk_io_total() == {
        'io_read_count': 1,
        'io_write_count': 2,
        'io_read_bytes': 3,
        'io_write_bytes': 4,
        'io_read_time_ms': 5,
        'io_write_time_ms': 6,
        'io_busy_time_ms': 7,
    }
