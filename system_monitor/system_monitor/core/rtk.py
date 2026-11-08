"""RTK corrections arrive over the cellular link about once a second; late ones blame the link."""

from collections import deque
import math

STALE_S = 2.0
# NavSatStatus.STATUS_GBAS_FIX, which the u-blox driver reports for RTK fixed.
STATUS_RTK_FIXED = 2


class RtcmTracker:
    def __init__(self, window_s):
        self.window_s = window_s
        self.arrivals = deque()

    def add(self, t):
        self.arrivals.append(t)

    def sample(self, now):
        """Return the age of the newest correction and the longest gap in the window, in s."""
        while self.arrivals and now - self.arrivals[0] > self.window_s:
            self.arrivals.popleft()
        if not self.arrivals:
            return {'rtcm_age_s': math.nan, 'rtcm_max_gap_s': math.nan}
        edges = list(self.arrivals) + [now]
        return {
            'rtcm_age_s': now - self.arrivals[-1],
            'rtcm_max_gap_s': max(b - a for a, b in zip(edges, edges[1:])),
        }


def rtk_cause(fix_status, rtcm_age_s):
    """Name why the fix is not RTK fixed, or FIXED; empty without a fix yet."""
    if fix_status is None:
        return ''
    if fix_status == STATUS_RTK_FIXED:
        return 'FIXED'
    if math.isnan(rtcm_age_s):
        return 'NO_CORRECTIONS'
    if rtcm_age_s > STALE_S:
        return 'CORRECTIONS_LATE'
    return 'SKY_OR_RECEIVER'
