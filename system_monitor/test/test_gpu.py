import importlib
import sys
from types import ModuleType
from types import SimpleNamespace

import pytest


class NVMLError(Exception):
    pass


class NVMLErrorNotSupported(NVMLError):
    pass


class NVMLErrorUnknown(NVMLError):
    pass


def fake_pynvml(devices):
    nvml = ModuleType('pynvml')
    nvml.NVMLError = NVMLError
    nvml.NVMLError_NotSupported = NVMLErrorNotSupported
    nvml.NVML_TEMPERATURE_GPU = 0
    nvml.calls = []
    nvml.nvmlInit = lambda: nvml.calls.append('init')
    nvml.nvmlShutdown = lambda: nvml.calls.append('shutdown')
    nvml.nvmlDeviceGetCount = lambda: len(devices)
    nvml.nvmlDeviceGetHandleByIndex = lambda i: devices[i]

    def read(field):
        def call(handle, *args):
            value = handle[field]
            if isinstance(value, Exception):
                raise value
            return value

        return call

    nvml.nvmlDeviceGetUtilizationRates = lambda h: SimpleNamespace(gpu=read('util')(h))
    nvml.nvmlDeviceGetMemoryInfo = read('mem')
    nvml.nvmlDeviceGetTemperature = read('temp')
    nvml.nvmlDeviceGetPowerUsage = read('power_mw')
    return nvml


@pytest.fixture
def gpu_module(monkeypatch):
    def load(devices):
        nvml = fake_pynvml(devices)
        monkeypatch.setitem(sys.modules, 'pynvml', nvml)
        monkeypatch.delitem(sys.modules, 'system_monitor.core.gpu', raising=False)
        return importlib.import_module('system_monitor.core.gpu'), nvml

    return load


MIB = 1024 * 1024


def test_sample_converts_units(gpu_module):
    device = {
        'util': 37,
        'mem': SimpleNamespace(used=512 * MIB, total=8192 * MIB),
        'temp': 61,
        'power_mw': 45500,
    }
    gpu, nvml = gpu_module([device])

    sampler = gpu.GpuSampler()
    data = sampler.sample()
    sampler.close()

    assert data == {
        'gpus': [
            {
                'index': 0,
                'utilization_percent': 37.0,
                'memory_used_mb': 512.0,
                'memory_total_mb': 8192.0,
                'temperature_celsius': 61.0,
                'power_watts': 45.5,
            }
        ]
    }
    assert nvml.calls == ['init', 'shutdown']


def test_unsupported_readings_are_minus_one(gpu_module):
    device = {
        'util': NVMLErrorNotSupported(),
        'mem': SimpleNamespace(used=0, total=MIB),
        'temp': NVMLErrorNotSupported(),
        'power_mw': NVMLErrorNotSupported(),
    }
    gpu, _ = gpu_module([device])

    info = gpu.GpuSampler().sample()['gpus'][0]

    assert info['utilization_percent'] == -1.0
    assert info['temperature_celsius'] == -1.0
    assert info['power_watts'] == -1.0


def test_other_nvml_errors_propagate(gpu_module):
    device = {
        'util': NVMLErrorUnknown(),
        'mem': SimpleNamespace(used=0, total=MIB),
        'temp': 50,
        'power_mw': 1000,
    }
    gpu, _ = gpu_module([device])

    with pytest.raises(NVMLErrorUnknown):
        gpu.GpuSampler().sample()
