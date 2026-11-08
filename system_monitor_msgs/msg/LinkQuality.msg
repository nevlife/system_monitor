# Link to the remote echo server over the probe window, with the modem's view and the last GPS fix.
# Values that are not available (no reply yet, no modem, no fix) are NaN or empty.
builtin_interfaces/Time stamp
string target

uint32 probes_sent
uint32 probes_lost
float64 loss_percent
float64 rtt_p50_ms
float64 rtt_p95_ms
float64 rtt_max_ms
float64 rtt_min_ever_ms
float64 jitter_ms
float64 longest_outage_ms
# One-way delay above its own minimum, per direction (the echo's clock offset cancels out).
float64 uplink_queue_p95_ms
float64 downlink_queue_p95_ms

string access_technology
string operator_name
string cell_id
float64 rsrp_dbm
float64 rsrq_db
float64 sinr_db

# RTK correction stream: age of the newest correction and the longest gap in the window (s),
# and FIXED, CORRECTIONS_LATE (the link), SKY_OR_RECEIVER, NO_CORRECTIONS, or empty without a fix.
float64 rtcm_age_s
float64 rtcm_max_gap_s
string rtk

float64 latitude
float64 longitude

# Prediction from the radio map along the current velocity (NaN or 0 without map data ahead).
float64 predicted_degraded_in_s
float64 predicted_rtt_p95_ms
float64 predicted_loss_percent
float64 predicted_outage_ms
uint32 map_samples_ahead
# route (along the planned route) or velocity (straight ahead at the current velocity).
string prediction_source

# OK, NO_LINK, HANDOVER, WEAK_SIGNAL, INTERFERENCE, CONGESTION, or DEGRADED (cause unknown).
string diagnosis
