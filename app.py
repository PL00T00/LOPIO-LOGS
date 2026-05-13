import os
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

CHANNEL_ID = os.environ["LOPIO_CHANNEL_ID"]
JAME_ID = os.environ["JAME_ID"]

app = App(token=os.environ["SLACK_BOT_TOKEN"])

def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes, seconds = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m {seconds}s"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def get_bot_user_id(client) -> str:
    return client.auth_test()["user_id"]

def is_bot_user(client, user_id: str) -> bool:
    try:
        info = client.users_info(user=user_id)
        return info["user"].get("is_bot", False)