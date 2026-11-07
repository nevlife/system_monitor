from types import SimpleNamespace

from system_monitor.core import network


def counters(recv, sent):
    return SimpleNamespace(
        bytes_recv=recv,
        bytes_sent=sent,
        packets_recv=0,
        packets_sent=0,
        errin=0,
        errout=0,
        dropin=0,
        dropout=0,
    )


def test_rates_come_from_the_previous_sample(monkeypatch):
    io = {'eth0': counters(1000, 500), 'lo': counters(0, 0)}
    now = [10.0]
    monkeypatch.setattr(network.psutil, 'net_io_counters', lambda pernic: dict(io))
    monkeypatch.setattr(network.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(
        network.psutil,
        'net_if_stats',
        lambda: {
            'eth0': SimpleNamespace(isup=True, mtu=1500, speed=1000),
            'lo': SimpleNamespace(isup=False, mtu=65536, speed=0),
        },
    )
    sampler = network.NetworkSampler()

    io['eth0'] = counters(3000, 1500)
    now[0] = 12.0
    data = sampler.sample()

    eth0 = data['interfaces']['eth0']
    assert eth0['input_bytes_per_sec'] == 1000.0
    assert eth0['output_bytes_per_sec'] == 500.0
    assert data['summary'] == {'total_interfaces': 2, 'active_interfaces': 1, 'down_interfaces': 1}
