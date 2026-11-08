"""
Cellular modem state from ModemManager (mmcli JSON output).

The key names are unchecked against a real modem; a phone used as a USB tether exposes none.
Needs `mmcli -m any --signal-setup=<s>` and `--location-enable-3gpp` once.
"""

import json
import math
import subprocess

EMPTY = {
    'access_technology': '',
    'operator_name': '',
    'cell_id': '',
    'rsrp_dbm': math.nan,
    'rsrq_db': math.nan,
    'sinr_db': math.nan,
}


def read():
    """Return the modem state, or EMPTY when ModemManager reports no modem."""
    status = _mmcli([])
    if status is None:
        return dict(EMPTY)
    return parse(status, _mmcli(['--signal-get']) or {}, _mmcli(['--location-get']) or {})


def _mmcli(extra):
    result = subprocess.run(
        ['mmcli', '-J', '-m', 'any', *extra], capture_output=True, text=True, timeout=2
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def parse(status, signal, location):
    modem = status.get('modem', {})
    techs = modem.get('generic', {}).get('access-technologies', [])
    sig = signal.get('modem', {}).get('signal', {})
    # 5G NR when the modem reports it (NSA keeps LTE alongside), else LTE.
    nr, lte = sig.get('5g', {}), sig.get('lte', {})
    cell = lte if math.isnan(_number(nr.get('rsrp'))) else nr
    loc = location.get('modem', {}).get('location', {}).get('3gpp', {})
    return {
        'access_technology': ','.join(techs),
        'operator_name': modem.get('3gpp', {}).get('operator-name', ''),
        'cell_id': '' if loc.get('cid', '--') == '--' else loc['cid'],
        'rsrp_dbm': _number(cell.get('rsrp')),
        'rsrq_db': _number(cell.get('rsrq')),
        'sinr_db': _number(cell.get('sinr', cell.get('snr'))),
    }


def _number(text):
    """Convert an mmcli value, which is '--' when the modem does not report it."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return math.nan
