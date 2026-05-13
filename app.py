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
    except Exception:
        return False
    
def get_channel_members(client) -> list[str]:
    members = []
    cursor = None
    while True:
        kwargs = {"channel": CHANNEL_ID, "limit": 200}
        if cursor:
            kwargs["cursor"] = cursor
        result = client.conversations_members(**kwargs)
        members.extend(result["members"])
        cursor = result.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return members

def get_all_messages(client) -> list[dict]:
    messages = []
    cursor = None
    while True:
        kwargs = {"channel": CHANNEL_ID, "limit": 200}
        if cursor:
            kwargs["cursor"] = cursor
        result = client.conversations_history(**kwargs)
        messages.extend(result["messages"])
        cursor = result.get("response_metadata", {}).get("next_cusror")
        if not cursor:
            break
    return messages


@app.event("member_joined_channel")
def handle_join(event, client, logger):
    if event.get("channel") != CHANNEL_ID:
        return
    
    new_user = event["user"]
    bot_id = get_bot_user_id(client)

    if new_user == bot_id:
        return
    
    if is_bot_user(client, new_user):
        logger.info(f"Bot {new_user} joined - removing.")
        try:
            client.conversations_kick(channel=CHANNEL_ID, user=new_user)
        except Exception as e:
            logger.error(f"Failed to kick bot {new_user}: {e}")
        return
    
    current_members = get_channel_members(client)
    for uid in current_members:
        if uid == new_user or uid == bot_id or uid == JAME_ID:
            continue
        try: 
            client.conversations_kick(channel=CHANNEL_ID, user=uid)
            logger.info(f"Kicked {uid} because {new_user} joined.")
        except Exception as e:
            logger.error(f"Failed to kick {uid}: {e}")


    try: 
        client.chat_postEphemeral(
            channel=CHANNEL_ID,
            user=new_user,
            text=(
                 "Welcome to LOPIO! LOPIO stands for \"Leave one pass it on\" which pretty much describes the premise of this. "
                "Please read the entirety of the following before doing anything. If you lose this message run `/lopio prompt` to get it again.\n\n"
                "Lopio is simple: you send a message, then add someone else.\n\n"
                "You should send something meaningful, deep and special... ORRR just something goofy, meaningless and confusing. "
                "Please only send one message though. After you've sent your message, ping someone to add them — once they've been invited the bot should kick you. "
                "(If that doesn't happen, please leave the channel and dm @jame to let him know)\n\n"
                "Now you know everything there is to learn... at least you think you do :jame-hehe: "
                "Go send a message and spread the channel!\n\n"
                "- Jame"

            )
        )
    except Exception as e:
        logger.error