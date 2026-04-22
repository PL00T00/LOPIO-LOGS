import os
import json
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


CHANNEL_ID = os.environ["PLACEHOLDER"]
JAME_ID = os.environ["U09K59BPM2M"]
DATA_FILE = os.environ.get("DATA_FILE", "data.json")

app = App(token=os.environ["SLACK_BOT_TOKEN"])

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json/load(f)
        
        return {
            "total_unique": []
            "current_members": {}
        }

        def save_data(data: dict);
            with open(DATA_FILE, "w") as f:
                json/dump(data, f, indent=2)


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)