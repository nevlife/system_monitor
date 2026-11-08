import math

from system_monitor.core import rtk


def test_age_and_gap():
    tracker = rtk.RtcmTracker(window_s=10.0)
    for t in (0.0, 1.0, 2.0, 6.0):
        tracker.add(t)
    s = tracker.sample(now=6.5)
    assert s['rtcm_age_s'] == 0.5
    assert s['rtcm_max_gap_s'] == 4.0


def test_open_gap_counts_up_to_now():
    tracker = rtk.RtcmTracker(window_s=10.0)
    tracker.add(0.0)
    assert tracker.sample(now=3.0)['rtcm_max_gap_s'] == 3.0


def test_nothing_in_the_window():
    tracker = rtk.RtcmTracker(window_s=5.0)
    tracker.add(0.0)
    assert math.isnan(tracker.sample(now=9.0)['rtcm_age_s'])


def test_causes():
    assert rtk.rtk_cause(None, 0.5) == ''
    assert rtk.rtk_cause(rtk.STATUS_RTK_FIXED, math.nan) == 'FIXED'
    assert rtk.rtk_cause(0, math.nan) == 'NO_CORRECTIONS'
    assert rtk.rtk_cause(0, 5.0) == 'CORRECTIONS_LATE'
    assert rtk.rtk_cause(0, 0.8) == 'SKY_OR_RECEIVER'
