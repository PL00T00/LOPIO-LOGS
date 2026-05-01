import os
import json
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ── Config ────────────────────────────────────────────────────────────────────
CHANNEL_ID = os.environ["LOPIO_CHANNEL_ID"]
JAME_ID    = os.environ["JAME_ID"]
DATA_FILE  = os.environ.get("DATA_FILE", "data.json")

app = App(token=os.environ["SLACK_BOT_TOKEN"])

# ── Persistence ───────────────────────────────────────────────────────────────

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

# ── Helpers ───────────────────────────────────────────────────────────────────

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

# ── Event: someone joins ──────────────────────────────────────────────────────

@app.event("member_joined_channel")
def handle_join(event, client, logger):
    if event.get("channel") != CHANNEL_ID:
        return

    new_user = event["user"]
    bot_id   = get_bot_user_id(client)

    if new_user == bot_id:
        return

    data = load_data()
    now  = time.time()

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

    try:
        app.client.chat_postEphemeral(
            channel=CHANNEL_ID,
            user=new_user,
            text=(  "Welcome to LOPIO! LOPIO stands for \"Leave one pass it on\" which pretty much describes the premise of this. "
                "Please read the entirety of the following before doing anything, if you lose this message run `/lopio prompt` to have it send again.\n\n"
                "Lopio is simple, you send a message then add someone else.\n\n"
                "You should send something meaningful, deep and special... ORRR just something goofy, meaningless and confusing. "
                "Please only send one message though. After you've sent your message ping someone to add them, once they've been invited the bot should kick you. "
                "(If that doesnt happen please leave the channel and dm @jame to let him know)\n\n"
                "Now you know everything there is to learn... atleast you think you do :jame-hehe: go and send a message and spread the channel!\n\n"
                "- Jame"
            )
        )
    
    except Exception as e:
        logger.error(f"Failed to send welcome message to {new_user}: {e}")
        )

    save_data(data)

# ── Event: someone leaves ─────────────────────────────────────────────────────

@app.event("member_left_channel")
def handle_leave(event, client, logger):
    if event.get("channel") != CHANNEL_ID:
        return

    user_id = event["user"]
    data    = load_data()

    if user_id in data["current_members"]:
        del data["current_members"][user_id]
        save_data(data)

# ── Slash command: /lopio ─────────────────────────────────────────────────────

@app.command("/lopio")
def handle_lopio(ack, command, client, respond, logger):
    ack()

    args   = (command.get("text") or "").strip().lower().split()
    subCmd = args[0] if args else ""
    caller = command["user_id"]

    if subCmd == "log":
        data    = load_data()
        now     = time.time()
        total   = len(data["total_unique"])
        current = data["current_members"]

        lines = [
            f"*:lock: LOPIO Channel Stats*",
            f"*Total unique members ever:* {total}",
            f"*Currently in channel:* {len(current)}",
            "",
        ]

        if current:
            lines.append("*Current members:*")
            for uid, joined_ts in current.items():
                name     = get_display_name(client, uid)
                duration = fmt_duration(now - joined_ts)
                lines.append(f" - <@{uid}> ({name}) - in for *{duration}*")
        else:
            lines.append("_No members currently in channel (except the bot hehe)._")

        respond("\n".join(lines), response_type="ephemeral")

    elif subCmd == "invite":
        if caller != JAME_ID:
            respond(":jame-holdonnow:You can't use this command, this has been reported to the authorities.", response_type="ephemeral")
            return
        try:
            client.conversations_invite(channel=CHANNEL_ID, users=JAME_ID)
            respond(":jame-goog: Welcome back, master!", response_type="ephemeral")
        except Exception as e:
            respond(f":jame-goog:I dont know what you want from me bro, but I cant do it. Error: {e}", response_type="ephemeral")

    elif subCmd =="history":
        try:
            messages = []
            cursor =None

            while True:
                kwargs = {"channel": CHANNEL_ID, "limit": 200}
                if cursor:
                    kwargs["cursor"] = cursor
                result = client.conversations_history(**kwargs)
                messages.extend(result["messages"])

                if result.get("response_metadata", {}).get("next_cursor"):
                    cursor = result["response_metadata"]["next_cursor"]
                else:
                    break

            user_messages = [
                m for m in messages
                if m.get("type") == "message"
                and m.get("subtype") is None
                and m.get("user")
            ]
            
            if not user_messages:
                respond(":cryin: No messages found, I swear I looked!", response_type ="ephemeral")
                return
            
            user_messages.sort(key=lambda m: float(m["ts"]))

            timeline = []
            for m in user_messages:
                timeline.append(f"<@{m['user']}>")

            respond(
                f"*:scroll: Channel Timeline*\n{'->'.join(timeline)}",
                response_type="ephemeral"
               )
            
        except Exception as e:
            respond(f":Ahh fuck, I forgot how to get the history. pls ping @jame (error): `{e}`", response_type="ephemeral")

    elif subCmd == "prompt":
        respond(  "Welcome to LOPIO! LOPIO stands for \"Leave one pass it on\" which pretty much describes the premise of this. "
                "Please read the entirety of the following before doing anything, if you lose this message run `/lopio prompt` to have it send again.\n\n"
                "Lopio is simple, you send a message then add someone else.\n\n"
                "You should send something meaningful, deep and special... ORRR just something goofy, meaningless and confusing. "
                "Please only send one message though. After you've sent your message ping someone to add them, once they've been invited the bot should kick you. "
                "(If that doesnt happen please leave the channel and dm @jame to let him know)\n\n"
                "Now you know everything there is to learn... atleast you think you do :jame-hehe: go and send a message and spread the channel!\n\n"
                "- Jame",
                response_type="ephemeral"   
            )

    else:
        respond(
            ":jame-hehe: That's not how you use the command! Try `/lopio log` to see stats or '/lopio history' to see a timeline of everyone in the channel! :jame-hehe:",
            response_type="ephemeral"
        )

# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot_id = get_bot_user_id(app.client)
    data   = load_data()
    now    = time.time()

    try:
        result = app.client.conversations_members(channel=CHANNEL_ID)
        for uid in result["members"]:
            if uid == bot_id:
                continue
            if uid not in data["total_unique"]:
                data["total_unique"].append(uid)
            if uid not in data["current_members"]:
                data["current_members"][uid] = now
        save_data(data)
        print(f"[lopio] Synced {len(result['members'])} members on startup.")
    except Exception as e:
        print(f"[lopio] Failed to sync members on startup: {e}")

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

# this bot was made by Jame on slack, please support it by starring it on github: https://github.com/PL00T00/LOPIO-LOGS or contributing!
# It's currently in V1, so expect some bugs and missing features. If you have any suggestions or want to contribute, feel free to!