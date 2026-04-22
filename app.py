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

        def save_data(data: dict):
            with open(DATA_FILE, "w") as f:
                json/dump(data, f, indent=2)


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"

def get_display_name(client, user_id: str) -> str:
    try:
        info = client.users_info(user=user_id)
        profile = info["user"]["profile"]
        return profile.get("display_name") or profile.get("real_name") or user_id
    except Exception:
        return user_id
    
def get_bot_user_id(client) -> str:
    return client.auth_test()["user_id"]



@app.event("member_joined_channel")
def handle_join(event, client, logger):

    if event.get("channel") != CHANNEL_ID:
        return
    
    user_id = event["user"]
    data = load_data()

    if user_id in data["current_members"]:
        del data["current_members"][user_id]
        save_data(data)


@app.command("/lopio")
def handle_lopio(ack, command, client, respond, logger):
    ack()


    args = (command.get("text") or "").strip().lower().split()
    subCmd = args[0] if args else ""
    caller = command["user_id"]



    


    