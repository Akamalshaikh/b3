import telebot
import re
import threading
import time
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from p import check_card  # Make sure check_card(cc_line) is in p.py

# BOT Configuration
BOT_TOKEN = '7939333845:AAGtCSoIUFQPXH94-35h7lWcIuPD30tRyYY'
ADMIN_ID = 6994528708  # Replace with your Telegram user ID (int)
AUTHORIZED_GROUP_CHAT_LINK = "https://t.me/b3_solox_bot" # Replace with your group chat link

bot = telebot.TeleBot(BOT_TOKEN)

AUTHORIZED_USERS = {} # Stores user_id: expiry_timestamp or "forever"
AUTHORIZED_CHATS = {} # Stores chat_id: expiry_timestamp or "forever" for groups/channels

# ---------------- Helper Functions ---------------- #

def load_auth():
    try:
        with open("authorized.json", "r") as f:
            data = json.load(f)
            # Separate users and chats if they were mixed previously
            users = {k: v for k, v in data.items() if int(k) > 0}
            chats = {k: v for k, v in data.items() if int(k) < 0}
            return users, chats
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}

def save_auth(users_data, chats_data):
    # Combine users and chats into one dictionary for storage
    combined_data = {**users_data, **chats_data}
    with open("authorized.json", "w") as f:
        json.dump(combined_data, f)

# Load data at startup
AUTHORIZED_USERS, AUTHORIZED_CHATS = load_auth()

def is_authorized(chat_id):
    # Admin is always authorized
    if chat_id == ADMIN_ID:
        return True

    # Check for individual user authorization
    if str(chat_id) in AUTHORIZED_USERS:
        expiry = AUTHORIZED_USERS[str(chat_id)]
        if expiry == "forever":
            return True
        if time.time() < expiry:
            return True
        else:
            # User authorization expired
            del AUTHORIZED_USERS[str(chat_id)]
            save_auth(AUTHORIZED_USERS, AUTHORIZED_CHATS)
            return False

    # Check for group chat authorization
    if chat_id < 0 and str(chat_id) in AUTHORIZED_CHATS: # Negative chat_id for groups/channels
        expiry = AUTHORIZED_CHATS[str(chat_id)]
        if expiry == "forever":
            return True
        if time.time() < expiry:
            return True
        else:
            # Group authorization expired
            del AUTHORIZED_CHATS[str(chat_id)]
            save_auth(AUTHORIZED_USERS, AUTHORIZED_CHATS)
            return False

    return False

def normalize_card(text):
    """
    Normalize credit card from any format to cc|mm|yy|cvv
    Improved to handle common variations more robustly.
    """
    if not text:
        return None

    # Replace common separators with a single space
    text = text.replace('\n', ' ').replace('/', ' ').replace(':', ' ').replace('-', ' ')

    # Regex to find potential card parts
    # CC: 13-16 digits
    # MM: 01-12 (2 digits)
    # YY: 2 or 4 digits (e.g., 26 or 2026)
    # CVV: 3 or 4 digits

    # Attempt to find the full pattern first
    match = re.search(r'(\d{13,16})\s*\|\s*(\d{1,2})\s*\|\s*(\d{2,4})\s*\|\s*(\d{3,4})', text)
    if match:
        cc, mm, yy, cvv = match.groups()
        # Ensure MM is two digits
        mm = mm.zfill(2)
        # Convert 2-digit year to 4-digit if necessary
        if len(yy) == 2:
            current_year_prefix = str(datetime.now().year)[:2] # e.g., "20"
            yy = current_year_prefix + yy
        return f"{cc}|{mm}|{yy}|{cvv}"

    # If direct match fails, try to extract parts individually
    numbers = re.findall(r'\d+', text)
    cc = ''
    mm = ''
    yy = ''
    cvv = ''

    for part in numbers:
        if len(part) >= 13 and len(part) <= 16 and not cc: # Credit card number
            cc = part
        elif len(part) == 2 and 1 <= int(part) <= 12 and not mm: # Month (2 digits, 1-12)
            mm = part
        elif len(part) == 4 and part.startswith('20') and not yy: # 4-digit year starting with 20
            yy = part
        elif len(part) == 2 and not part.startswith('20') and not yy: # 2-digit year
            current_year_prefix = str(datetime.now().year)[:2]
            yy = current_year_prefix + part
        elif len(part) in [3, 4] and not cvv: # CVV (3-4 digits)
            cvv = part
        # A more robust approach would be to look for month/year pairs together if possible

    # Final check for validity and re-assemble
    if cc and mm and yy and cvv:
        # Additional validation: year should be in the future or current
        try:
            exp_year = int(yy)
            exp_month = int(mm)
            current_year = datetime.now().year
            current_month = datetime.now().month

            if exp_year < current_year or (exp_year == current_year and exp_month < current_month):
                return None # Card is expired
        except ValueError:
            return None # Invalid month/year format

        return f"{cc}|{mm}|{yy}|{cvv}"

    return None

# ---------------- Bot Commands ---------------- #

@bot.message_handler(commands=['start'])
def start_handler(msg):
    bot.reply_to(msg, """✦━━━[ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄᴄ ᴄʜᴇᴄᴋᴇʀ ʙᴏᴛ ]━━━✦

⟡ ᴏɴʟʏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴍᴇᴍʙᴇʀꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ
⟡ ᴜꜱᴇ /b3 ᴛᴏ ᴄʜᴇᴄᴋ ꜱɪɴɢʟᴇ ᴄᴀʀᴅ
⟡ ꜰᴏʀ ᴍᴀꜱꜱ ᴄʜᴇᴄᴋ, ʀᴇᴘʟʏ ᴄᴄ ꜰɪʟᴇ ᴡɪᴛʜ /mb3

ʙᴏᴛ ᴘᴏᴡᴇʀᴇᴅ ʙʏ @its_soloz""")

@bot.message_handler(commands=['admin'])
def admin_commands_handler(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    bot.reply_to(msg, """✦━━━[ ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅꜱ ]━━━✦

⟡ `/auth <user_id_or_chat_id> [days]` - Authorize a user or group (days optional, "forever" if not specified)
⟡ `/rm <user_id_or_chat_id>` - Remove authorization for a user or group
⟡ `/broadcast <message>` - Send a message to all authorized DMs and groups
⟡ `/stats` - Show authorization statistics (future enhancement if needed)

Example:
`/auth 123456789 30` (Authorizes user 123456789 for 30 days)
`/auth -1001234567890 forever` (Authorizes group -1001234567890 forever)
`/broadcast Hello everyone!` (Broadcasts "Hello everyone!")
""")

@bot.message_handler(commands=['auth'])
def authorize_user_or_chat(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            return bot.reply_to(msg, "❌ Usage: /auth <user_id_or_chat_id> [days]")

        target_id_str = parts[1]
        
        # Determine if it's a user or chat ID
        if target_id_str.startswith('@'):
            return bot.reply_to(msg, "❌ Use numeric Telegram ID, not @username.")
        
        target_id = int(target_id_str)

        days = int(parts[2]) if len(parts) > 2 else None
        expiry = "forever" if not days else time.time() + (days * 86400)

        if target_id > 0: # It's a user ID
            AUTHORIZED_USERS[str(target_id)] = expiry
            save_auth(AUTHORIZED_USERS, AUTHORIZED_CHATS)
            msg_text = f"✅ Authorized user {target_id} for {days} days." if days else f"✅ Authorized user {target_id} forever."
        else: # It's a group/channel ID (negative)
            AUTHORIZED_CHATS[str(target_id)] = expiry
            save_auth(AUTHORIZED_USERS, AUTHORIZED_CHATS)
            msg_text = f"✅ Authorized group/channel {target_id} for {days} days." if days else f"✅ Authorized group/channel {target_id} forever."
        
        bot.reply_to(msg, msg_text)
    except ValueError:
        bot.reply_to(msg, "❌ Invalid ID or days format. Please use numeric ID and integer for days.")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}")

@bot.message_handler(commands=['rm'])
def remove_auth(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            return bot.reply_to(msg, "❌ Usage: /rm <user_id_or_chat_id>")
        
        target_id_str = parts[1]
        target_id = int(target_id_str)

        if target_id > 0: # It's a user ID
            if str(target_id) in AUTHORIZED_USERS:
                del AUTHORIZED_USERS[str(target_id)]
                save_auth(AUTHORIZED_USERS, AUTHORIZED_CHATS)
                bot.reply_to(msg, f"✅ Removed user {target_id} from authorized users.")
            else:
                bot.reply_to(msg, "❌ User is not authorized.")
        else: # It's a group/channel ID
            if str(target_id) in AUTHORIZED_CHATS:
                del AUTHORIZED_CHATS[str(target_id)]
                save_auth(AUTHORIZED_USERS, AUTHORIZED_CHATS)
                bot.reply_to(msg, f"✅ Removed group/channel {target_id} from authorized chats.")
            else:
                bot.reply_to(msg, "❌ Group/channel is not authorized.")
    except ValueError:
        bot.reply_to(msg, "❌ Invalid ID format. Please use a numeric ID.")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        message_to_send = msg.text.split(None, 1)
        if len(message_to_send) < 2:
            return bot.reply_to(msg, "❌ Usage: /broadcast <your message>")
        
        message_to_send = message_to_send[1]

        # Broadcast to authorized users (DMs)
        for user_id_str in list(AUTHORIZED_USERS.keys()):
            user_id = int(user_id_str)
            if is_authorized(user_id): # Check if still authorized before sending
                try:
                    bot.send_message(user_id, f"📢 Broadcast Message:\n\n{message_to_send}")
                    time.sleep(0.1) # Small delay to avoid hitting Telegram API limits
                except Exception as e:
                    print(f"Failed to send broadcast to user {user_id}: {e}")
                    # Optionally, remove users who have blocked the bot
                    # if "bot was blocked by the user" in str(e).lower():
                    #     del AUTHORIZED_USERS[user_id_str]
                    #     save_auth(AUTHORIZED_USERS, AUTHORIZED_CHATS)

        # Broadcast to authorized group chats
        for chat_id_str in list(AUTHORIZED_CHATS.keys()):
            chat_id = int(chat_id_str)
            if is_authorized(chat_id): # Check if still authorized before sending
                try:
                    bot.send_message(chat_id, f"📢 Broadcast Message:\n\n{message_to_send}")
                    time.sleep(0.1) # Small delay
                except Exception as e:
                    print(f"Failed to send broadcast to chat {chat_id}: {e}")

        bot.reply_to(msg, "✅ Broadcast message sent to all authorized users and groups.")

    except Exception as e:
        bot.reply_to(msg, f"❌ Error during broadcast: {e}")

# This handler should be placed BEFORE other command handlers that require authorization,
# to catch unauthorized users trying to use any command in a private chat.
@bot.message_handler(func=lambda message: message.chat.type == 'private' and not is_authorized(message.from_user.id))
def unauthorized_private_chat_handler(msg):
    bot.reply_to(msg, f"""✦━━━[  ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ ]━━━✦

⟡ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ ɪɴ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ.
⟡ ᴘʟᴇᴀꜱᴇ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ ɪɴ ᴛʜᴇ ᴏꜰꜰɪᴄɪᴀʟ ɢʀᴏᴜᴘ ᴄʜᴀᴛ ꜰᴏʀ ꜰʀᴇᴇ ᴜꜱᴀɢᴇ: {AUTHORIZED_GROUP_CHAT_LINK}

✧ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ꜰᴏʀ ᴀᴜᴛʜᴏʀɪᴢᴀᴛɪᴏɴ: @its_soloz""")


@bot.message_handler(commands=['b3'])
def b3_handler(msg):
    # For group chats, authorization is based on the chat_id, not individual user_id
    current_chat_id = msg.chat.id
    if not is_authorized(current_chat_id):
        return bot.reply_to(msg, """✦━━━[  ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ ]━━━✦

⟡ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ
⟡ ᴏɴʟʏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴍᴇᴍʙᴇʀꜱ/ɢʀᴏᴜᴘꜱ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ

✧ ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ꜰᴏʀ ᴀᴜᴛʜᴏʀɪᴢᴀᴛɪᴏɴ: @its_soloz""")

    cc = None

    # Check if user replied to a message
    if msg.reply_to_message:
        # Extract CC from replied message
        replied_text = msg.reply_to_message.text or ""
        cc = normalize_card(replied_text)

        if not cc:
            return bot.reply_to(msg, "✦━━━[ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ ]━━━✦\n\n"
"⟡ ᴄᴏᴜʟᴅɴ'ᴛ ᴇxᴛʀᴀᴄᴛ ᴠᴀʟɪᴅ ᴄᴀʀᴅ ɪɴꜰᴏ ꜰʀᴏᴍ ʀᴇᴘʟɪᴇᴅ ᴍᴇꜱꜱᴀɢᴇ\n\n"
"ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ\n\n"
"`/b3 4556737586899855|12|2026|123`\n\n"
"✧ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ɪꜰ ʏᴏᴜ ɴᴇᴇᴅ ʜᴇʟᴘ")
    else:
        # Check if CC is provided as argument
        args = msg.text.split(None, 1)
        if len(args) < 2:
            return bot.reply_to(msg, "✦━━━[ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ ]━━━✦\n\n"
"⟡ ᴘʟᴇᴀꜱᴇ ᴜꜱᴇ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴛᴏ ᴄʜᴇᴄᴋ ᴄᴀʀᴅꜱ\n\n"
"ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ\n\n"
"`/b3 4556737586899855|12|2026|123`\n\n"
"ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴄᴏɴᴛᴀɪɴɪɴɢ ᴄᴄ ᴡɪᴛʜ `/b3`\n\n"
"✧ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ɪꜰ ʏᴏᴜ ɴᴇᴇᴅ ʜᴇʟᴘ")

        # Try to normalize the provided CC
        raw_input = args[1]

        # Directly normalize, the function is now more robust
        cc = normalize_card(raw_input)

        if not cc:
            return bot.reply_to(msg, "✦━━━[ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ ]━━━✦\n\n"
"⟡ ᴘʟᴇᴀꜱᴇ ᴜꜱᴇ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴛᴏ ᴄʜᴇᴄᴋ ᴄᴀʀᴅꜱ\n\n"
"ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ\n\n"
"`/b3 4556737586899855|12|2026|123`\n\n"
"ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴄᴏɴᴛᴀɪɴɪɴɢ ᴄᴄ ᴡɪᴛʜ `/b3`\n\n"
"✧ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ɪꜰ ʏᴏᴜ ɴᴇᴇᴅ ʜᴇʟᴘ")


    processing = bot.reply_to(msg, "✦━━━[  ᴘʀᴏᴄᴇꜱꜱɪɴɢ ]━━━✦\n\n"
"⟡ ʏᴏᴜʀ ᴄᴀʀᴅ ɪꜱ ʙᴇɪɴɢ ᴄʜᴇᴄᴋ...\n"
"⟡ ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴀ ꜰᴇᴡ ꜱᴇᴄᴏɴᴅꜱ\n\n"
"✧ ᴅᴏ ɴᴏᴛ ꜱᴘᴀᴍ ᴏʀ ʀᴇꜱᴜʙᴍɪᴛ ✧")

    def check_and_reply():
        try:
            result = check_card(cc)  # This function must be in your p.py
            bot.edit_message_text(result, msg.chat.id, processing.message_id, parse_mode='HTML')
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", msg.chat.id, processing.message_id)

    threading.Thread(target=check_and_reply).start()

@bot.message_handler(commands=['mb3'])
def mb3_handler(msg):
    current_chat_id = msg.chat.id
    if not is_authorized(current_chat_id):
        return bot.reply_to(msg, """✦━━━[  ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ ]━━━✦

⟡ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ
⟡ ᴏɴʟʏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴍᴇᴍʙᴇʀꜱ/ɢʀᴏᴜᴘꜱ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ

✧ ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ꜰᴏʀ ᴀᴜᴛʜᴏʀɪᴢᴀᴛɪᴏɴ: @its_soloz""")

    if not msg.reply_to_message:
        return bot.reply_to(msg, "✦━━━[ ᴡʀᴏɴɢ ᴜꜱᴀɢᴇ ]━━━✦\n\n"
"⟡ ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ `.txt` ꜰɪʟᴇ ᴏʀ ᴄʀᴇᴅɪᴛ ᴄᴀʀᴅ ᴛᴇxᴛ\n\n"
"✧ ᴏɴʟʏ ᴠᴀʟɪᴅ ᴄᴀʀᴅꜱ ᴡɪʟʟ ʙᴇ ᴄʜᴇᴄᴋᴇᴅ & ᴀᴘᴘʀᴏᴠᴇᴅ ᴄᴀʀᴅꜱ ꜱʜᴏᴡɴ ✧")

    reply = msg.reply_to_message

    # Detect whether it's file or raw text
    text = ""
    if reply.document:
        if reply.document.file_size > 1 * 1024 * 1024: # Limit to 1MB to prevent large file processing
            return bot.reply_to(msg, "❌ File too large. Maximum 1MB allowed for CC lists.")
        file_info = bot.get_file(reply.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        text = downloaded_file.decode('utf-8', errors='ignore')
    elif reply.text:
        text = reply.text
    
    if not text.strip():
        return bot.reply_to(msg, "❌ Empty text message or file.")

    # Extract CCs using improved normalization
    cc_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        
        normalized_cc = normalize_card(line)
        if normalized_cc:
            cc_lines.append(normalized_cc)

    if not cc_lines:
        return bot.reply_to(msg, "✦━━━[ ⚠️ ɴᴏ ᴠᴀʟɪᴅ ᴄᴀʀᴅꜱ ꜰᴏᴜɴᴅ ]━━━✦\n\n"
"⟡ ɴᴏ ᴠᴀʟɪᴅ ᴄʀᴇᴅɪᴛ ᴄᴀʀᴅꜱ ᴅᴇᴛᴇᴄᴛᴇᴅ ɪɴ ᴛʜᴇ ꜰɪʟᴇ\n"
"⟡ ᴘʟᴇᴀꜱᴇ ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴇ ᴄᴀʀᴅꜱ ᴀʀᴇ ɪɴ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ\n\n"
"ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ\n"
"`4556737586899855|12|2026|123`\n\n"
"✧ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ɪꜰ ʏᴏᴜ ɴᴇᴇᴅ ʜᴇʟᴘ")

    if not reply.document and len(cc_lines) > 15:
        return bot.reply_to(msg, "✦━━━[ ⚠️ ʟɪᴍɪᴛ ᴇxᴄᴇᴇᴅᴇᴅ ]━━━✦\n\n"
"⟡ ᴏɴʟʏ 15 ᴄᴀʀᴅꜱ ᴀʟʟᴏᴡᴇᴅ ɪɴ ʀᴀᴡ ᴘᴀꜱᴛᴇ\n"
"⟡ ꜰᴏʀ ᴍᴏʀᴇ ᴄᴀʀᴅꜱ, ᴘʟᴇᴀꜱᴇ ᴜᴘʟᴏᴀᴅ ᴀ `.txt` ꜰɪʟᴇ")

    total = len(cc_lines)
    user_id = msg.from_user.id # This is the user who initiated the command
    chat_id = msg.chat.id # This is the chat where the command was initiated

    # Initial Message with Inline Buttons
    kb = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(f"ᴀᴘᴘʀᴏᴠᴇᴅ 0 ✅", callback_data="none"),
        InlineKeyboardButton(f"ᴅᴇᴄʟɪɴᴇᴅ 0 ❌", callback_data="none"),
        InlineKeyboardButton(f"ᴛᴏᴛᴀʟ ᴄʜᴇᴄᴋᴇᴅ 0", callback_data="none"),
        InlineKeyboardButton(f"ᴛᴏᴛᴀʟ {total} ✅", callback_data="none"),
    ]
    for btn in buttons:
        kb.add(btn)

    status_msg = bot.send_message(chat_id, f"✦━━━[  ᴍᴀꜱꜱ ᴄʜᴇᴄᴋ ꜱᴛᴀʀᴛᴇᴅ ]━━━✦\n\n"
"⟡ ᴘʀᴏᴄᴇꜱꜱɪɴɢ ʏᴏᴜʀ ᴄᴀʀᴅꜱ...\n"
"⟡ ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴀ ꜰᴇᴡ ᴍᴏᴍᴇɴᴛꜱ\n\n"
" ʟɪᴠᴇ ꜱᴛᴀᴛᴜꜱ ᴡɪʟʟ ʙᴇ ᴜᴘᴅᴀᴛᴇᴅ ʙᴇʟᴏᴡ", reply_markup=kb)

    approved, declined, checked = 0, 0, 0

    def process_all():
        nonlocal approved, declined, checked
        for cc in cc_lines:
            try:
                checked += 1
                result = check_card(cc.strip())
                if "[APPROVED]" in result:
                    approved += 1
                    # Send approved card to the chat where the command was initiated
                    bot.send_message(chat_id, result, parse_mode='HTML')
                    # Send approved card to ADMIN_ID if not the same chat
                    if ADMIN_ID != user_id and ADMIN_ID != chat_id: # Avoid double send if admin is in the group
                        try:
                            bot.send_message(ADMIN_ID, f"✅ Approved by {msg.from_user.first_name} ({user_id}) in chat {chat_id}:\n{result}", parse_mode='HTML')
                        except Exception as admin_send_e:
                            print(f"Failed to send approved card to admin: {admin_send_e}")
                else:
                    declined += 1

                # Update inline buttons
                new_kb = InlineKeyboardMarkup(row_width=1)
                new_kb.add(
                    InlineKeyboardButton(f"ᴀᴘᴘʀᴏᴠᴇᴅ {approved} 🔥", callback_data="none"),
                    InlineKeyboardButton(f"ᴅᴇᴄʟɪɴᴇᴅ {declined} ❌", callback_data="none"),
                    InlineKeyboardButton(f"ᴛᴏᴛᴀʟ ᴄʜᴇᴄᴋᴇᴅ {checked} ✔️", callback_data="none"),
                    InlineKeyboardButton(f"ᴛᴏᴛᴀʟ {total} ✅", callback_data="none"),
                )
                try:
                    bot.edit_message_reply_markup(chat_id, status_msg.message_id, reply_markup=new_kb)
                except telebot.apihelper.ApiTelegramException as e:
                    if "message is not modified" in str(e):
                        pass # Ignore if no change in markup
                    else:
                        print(f"Error updating message markup: {e}")
                time.sleep(1) # Reduced sleep to 1 second for faster updates

            except Exception as e:
                bot.send_message(chat_id, f"❌ Error processing card '{cc}': {e}")
                # You might want to log this error more specifically

        bot.send_message(chat_id, "✦━━━[ ᴄʜᴇᴄᴋɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ]━━━✦\n\n"
"⟡ ᴀʟʟ ᴄᴀʀᴅꜱ ʜᴀᴠᴇ ʙᴇᴇɴ ᴘʀᴏᴄᴇꜱꜱᴇᴅ\n"
"⟡ ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴜꜱɪɴɢ ᴍᴀꜱꜱ ᴄʜᴇᴄᴋ\n\n"
" ᴏɴʟʏ ᴀᴘᴘʀᴏᴠᴇᴅ ᴄᴀʀᴅꜱ ᴡᴇʀᴇ ꜱʜᴏᴡɴ ᴛᴏ ʏᴏᴜ\n"
" ʏᴏᴜ ᴄᴀɴ ʀᴜɴ /mb3 ᴀɢᴀɪɴ ᴡɪᴛʜ ᴀ ɴᴇᴡ ʟɪꜱᴛ")
    threading.Thread(target=process_all).start()

# ---------------- Start Bot ---------------- #
bot.infinity_polling()