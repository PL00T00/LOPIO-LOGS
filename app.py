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
            return json.load(f)
        
        return {
            "total_unique": [],
            "current_members": {}
        }

        def save_data(data: dict):
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=2)


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
    
    new_user = event["user"]
    bot_id = get_bot_user_id(client)

    if new_user == bot_id:
        return
    

    data = load_data()
    now = time.time()

    if new_user not in data["total_unique"]:
        data["total_unique"].append(new_user)


    data["current_members"][new_user] = now


    for user_id in list(data["current_members"].keys()):
        if user_id == new_user or user_id == bot_id:
            continue
        try:
            client.conversations_kick(channel=CHANNEL_ID, user=user_id)
            logger.info(f"Kicked {user_id} because {new_user} joined")
        except Exception as e:
            logger.error(f"Failed to kick {user_id}: {e}")
            del data["current_members"][user_id]
            
        save_data(data)
    
    user_id = event["user"]
    data = load_data()

    if user_id in data["current_members"]:
        del data["current_members"][user_id]
        save_data(data)


@app.event("member_left_channel")
def handle_leave(event, client, logger):

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


    if subCmd == "log"
        data = load_data()
        now = time.time()

        total = len(data["total_unique"])
        current = data["current_members"]


        lines = [
            f"*:lock: LOPIO Channel Stats*",
            f"*Total unique members ever:* {total}"
            f"*Currently in channel:* {len(current)}",
            "",
        ]

    if current:
        lines.append("*Current members:*")
        for uid, joined_ts in current.items():
            name = get_display_name(client, uid)
            duration = fmt_duration(now - joined_ts)
            lines.append(f" - <@{uid}> ({name}) - in for *{duration}*")
        else:
            lines.append("_No members currently in channel (except the bot hehe)._")

        respond("\n".join(lines), response_type="ephemeral")


    elif subCmd == "invite":

        if caller != JAME_ID:
            respond("You can't use this command, this has been reported to the authorities.", response_type="ephemeral")
            return
        try:
            client.conversations_invite(channel=CHANNEL_ID, users=JAME_ID)
            respond(":jame-goog: Welcome back, master!", response_type="ephemeral")
            except Exception as e:
                respond(f"I dont know what you want from me bro, but I cant do it. Error: {e}", response_type="ephemeral")