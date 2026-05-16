import json
import os
from datetime import datetime


LOG_DIR = "logs"
LOG_FILE = f"{LOG_DIR}/traces.jsonl"


class ObservabilityTracker:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)

    def initialize(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        print("Observability initialized")

    def log_event(self, run_id, tenant_id, event_type, details):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "details": details
        }

        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")

    def log_trace(self, data):
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(data) + "\n")


# global helper instance
tracker = ObservabilityTracker()


def log_event(run_id, event_type, details):
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "event_type": event_type,
        "details": details
    }

    os.makedirs(LOG_DIR, exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

    print(f"Logged event: {event_type}")
    

def log_trace(data):
    os.makedirs(LOG_DIR, exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")