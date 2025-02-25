from shared.metrics import Counter

AMPLITUDE_PUBLISH_COUNTER = Counter(
    "amplitude_publish",
    "Total Amplitude publish calls",
    [
        "event_type",  # AmplitudeEventType
    ],
)

AMPLITUDE_PUBLISH_FAILURE_COUNTER = Counter(
    "amplitude_publish_failure",
    "Total Amplitude publish calls that failed",
    [
        "event_type",  # AmplitudeEventType
        "error",  # Exception class name
    ],
)
