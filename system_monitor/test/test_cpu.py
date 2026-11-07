from types import SimpleNamespace

from system_monitor.core import cpu


def sensor(current):
    return [SimpleNamespace(current=current)]


def test_temperature_takes_the_first_known_sensor():
    temps = {'acpitz': sensor(30.0), 'k10temp': sensor(55.0), 'zenpower': sensor(60.0)}
    assert cpu.cpu_temperature(temps) == 55.0


def test_temperature_is_minus_one_without_a_known_sensor():
    assert cpu.cpu_temperature({'acpitz': sensor(30.0), 'coretemp': []}) == -1.0


def test_dynamic_metrics_map_psutil_fields(monkeypatch):
    monkeypatch.setattr(
        cpu.psutil,
        'cpu_times',
        lambda: SimpleNamespace(user=1.0, system=2.0, idle=3.0, iowait=4.0),
    )
    monkeypatch.setattr(
        cpu.psutil,
        'cpu_stats',
        lambda: SimpleNamespace(ctx_switches=5, interrupts=6, soft_interrupts=7),
    )
    monkeypatch.setattr(cpu.psutil, 'cpu_freq', lambda: SimpleNamespace(current=2400.0))
    monkeypatch.setattr(cpu.psutil, 'getloadavg', lambda: (0.5, 0.25, 0.125))
    monkeypatch.setattr(cpu.psutil, 'sensors_temperatures', lambda: {'coretemp': sensor(42.0)})
    monkeypatch.setattr(cpu.psutil, 'cpu_percent', lambda interval: 12.5)

    data = cpu.get_cpu_dynamic_metrics()

    assert data == {
        'usage_percent': 12.5,
        'freq_current_mhz': 2400.0,
        'temperature_celsius': 42.0,
        'load_avg_1m': 0.5,
        'load_avg_5m': 0.25,
        'load_avg_15m': 0.125,
        'iowait_seconds': 4.0,
        'user_seconds': 1.0,
        'system_seconds': 2.0,
        'idle_seconds': 3.0,
        'ctx_switches': 5,
        'interrupts': 6,
        'soft_interrupts': 7,
    }
