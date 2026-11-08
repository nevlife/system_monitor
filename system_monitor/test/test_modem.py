import math
from types import SimpleNamespace

from system_monitor.core import modem

STATUS = {'modem': {'generic': {'access-technologies': ['lte', '5gnr']},
                    '3gpp': {'operator-name': 'SKTelecom'}}}
SIGNAL = {'modem': {'signal': {'lte': {'rsrp': '-95.00', 'rsrq': '-11.00', 'snr': '7.20'},
                               '5g': {'rsrp': '-101.00', 'rsrq': '-12.00', 'snr': '3.50'}}}}
LOCATION = {'modem': {'location': {'3gpp': {'cid': '0A1B2C', 'tac': '1234'}}}}


def test_nr_values_win_when_reported():
    m = modem.parse(STATUS, SIGNAL, LOCATION)
    assert m['access_technology'] == 'lte,5gnr'
    assert m['operator_name'] == 'SKTelecom'
    assert m['cell_id'] == '0A1B2C'
    assert (m['rsrp_dbm'], m['rsrq_db'], m['sinr_db']) == (-101.0, -12.0, 3.5)


def test_lte_values_and_unknowns():
    signal = {'modem': {'signal': {'lte': {'rsrp': '-95.00', 'rsrq': '--', 'snr': '7.20'},
                                   '5g': {'rsrp': '--'}}}}
    m = modem.parse(STATUS, signal, {'modem': {'location': {'3gpp': {'cid': '--'}}}})
    assert m['rsrp_dbm'] == -95.0
    assert math.isnan(m['rsrq_db'])
    assert m['cell_id'] == ''


def test_no_modem(monkeypatch):
    monkeypatch.setattr(modem.subprocess, 'run',
                        lambda *a, **k: SimpleNamespace(returncode=1, stdout=''))
    m = modem.read()
    assert m['cell_id'] == '' and math.isnan(m['rsrp_dbm'])
