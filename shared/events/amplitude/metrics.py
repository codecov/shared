from shared.metrics import Counter

AMPLITUDE_PUBLISH_COUNTER = Counter(
    "amplitude_publish",
    "Total Amplitude publish calls",
    [
        "state", # 'success' or 'failure'
        "event_type", # AmplitudeEventType
    ]
)
