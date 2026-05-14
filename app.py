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
    
    bot_id = get_bot_user_id(client)

    def check_and_rescue():
        time.sleep(EMPTY_CHANNEL_GRACE)
        try:
            members = get_channel_members(client)
            human_members = [uid for uid in members if uid != bot_id]
            if not human_members:
                logger.info("Channel is empty - auto-inviting Jame to prevent deletion.")
                global _jame_self_invite_pending
                _jame_self_invite_pending = True
                try:
                    client.conversation_invite(channel=CHANNEL_ID, users=JAME_ID)
                    logger.info("Auto-invited Jame.")
                except Exception as e:
                    _jame_self_invite_pending = False
                    if "already_in_channel" in str(e):
                        logger.info("Jame is in channel, stop panicing")
                    else:
                        logger.error(f"Failed to auto-invite Jame: {e}")
        except Exception as e:
            logger.error(f"Error during empty-channel check: {e}")

    threading.Thread(target=check_and_rescue, daemon=True).start()
    
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
        logger.error(f"Failed to send welcome message to {new_user}: {e}")

@app.event("member_left_channel")
def handle_leave(event, client, logger):
    if event.get("channel") != CHANNEL_ID:
        return
    

@app.command("/lopio")
def handle_lopio(ack, command, client, respond, logger):
    ack()

    args = (command.get("text") or "").strip().lower().split()
    subCmd = args[0] if args else ""
    caller = command["user_id"]
    bot_id = get_bot_user_id(client)

    if subCmd == "log":
        try:
            current_members = get_channel_members(client)
            now = time.time()
            human_members = [uid for uid in current_members if uid != bot_id]

            all_messages = get_all_messages(client)
            join_times: dict[str, float] = {}
            for m in all_messages:
                if m.get("subtype") == "channel_join" and m.get("user"):
                    uid = m["user"]
                    ts = float(m["ts"])
                    if uid not in join_times or ts > join_times[uid]:
                        join_times[uid] = ts

            lines = [
                "*:loll: LOPIO Channel Stats*",
                f"*Currently in channel:* {len(human_members)}",
                "",
            ]

            if human_members:
                lines.append("*Current members:*")
                for uid in human_members:
                    ts = join_times.get(uid, now)
                    duration = fmt_duration(now - ts)
                    lines.append(f"• <@{uid}> (joined {duration} ago)")
            
            else:
                lines.append("_Ahhh fuck, no humans here, fucking channel gone again. Wall of shame: ingo._")

            respond("\n".join(lines), response_type="ephemeral")

        except Exception as e:
            logger.error(f"/lopio log error: {e}")
            respond(f":jame-goog: Couldn't fetch log. Error: `{e}`", response_type="ephemeral")


    elif subCmd == "history":
        try: 
            all_messages = get_all_messages(client)

            user_messages = [
                m for m in all_messages
                if m.get("type") == "message"
                and m.get("subtype") is None
                and m.get("user")
                and m["user"] != bot_id
            ]

            if not user_messages:
                respond(":sadge: I couldn't find any messages - I swear I looked!", response_type="ephemeral")
                return
            
            user_messages.sort(key=lambda m: float(m["ts"]))

            seen = set()
            timeline = []
            for m in user_messages:
                uid = m["user"]
                if uid not in seen:
                    seen.add(uid)
                    timeline.append(f"<@{uid}>")

            chain = "→".join(timeline)
            respond(
                f":ultrafastparrot: Channel Timeline ({len(timeline)} people)*\n{chain}",
                response_type="ephemeral"
            )

        except Exception as e:
            logger.error(f"/lopio history error: {e}")
            respond(f":jame-goog: Couldn't fetch history. Error: `{e}`", response_type="ephemeral")


    elif subCmd == "invite":
        if caller != JAME_ID:
            respond(
                ":jame-holdonnow: You can't use this command. This has been reported to Zachery Hackery himself.",
                response_type="ephemeral"
            )
            return
        try:

            global _jame_self_invite_pending
            _jame_self_invite_pending = True
            client.conversations_invite(channel=CHANNEL_ID, users=JAME_ID)
            respond(":jame-goog-67: Welcome back, master!", response_type="ephemeral")
        except Exception as e:
            _jame_self_invite_pending = False
            if "already_in_channel" in str(e):
                respond(":jame-hehe: You're already in the channel!", response_type="ephemeral")
            else:
                respond(f":jame-holdonnow: FUCK FUCK FUCK failed to invite. Error: `{e}`", response_type="ephemeral")

    elif subCmd == "prompt":
        respond(
            "Welcome to LOPIO! LOPIO stands for \"Leave one pass it on\" which pretty much describes the premise of this. "
            "Please read the entirety of the following before doing anything. If you lose this message run `/lopio prompt` to get it again.\n\n"
            "Lopio is simple: you send a message, then add someone else.\n\n"
            "You should send something meaningful, deep and special... ORRR just something goofy, meaningless and confusing. "
            "Please only send one message though. After you've sent your message, ping someone to add them — once they've been invited the bot should kick you. "
            "(If that doesn't happen, please leave the channel and dm @jame to let him know)\n\n"
            "Now you know everything there is to learn... at least you think you do :jame-hehe: "
            "Go send a message and spread the channel!\n\n"
            "- Jame", 
            response_type="ephemeral"
        )

    else:
        respond(
            ":jame-hehe: Not a valid command! Try onw of these:\n"
            " - `/lopio log` - see who's currently in the channel\n"
            " - `/lopio history` - see the full chain of people in the channel\n"
            " - `/lopio prompt` - get the welcome message",
            response_type="ephemeral"
        )


if __name__ == "__main__":
    bot_id = get_bot_user_id(app.client)
    print(f"[lopio] Bot user ID: {bot_id}")

    try:
        members = get_channel_members(app.client)
        human_members = [uid for uid in members if uid != bot_id]
        print(f"[lopio] {len(human_members)} human(s) currently in channel: {human_members}")
    except Exception as e:
        print(f"[lopio] Failed to fetch members on startup: {e}")

    print("[lopio] V2 starting - stateless, no data.json needed.")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

# Made by Jame - github.com/PL00T00
# V2!