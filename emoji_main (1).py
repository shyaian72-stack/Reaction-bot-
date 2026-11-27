import telebot
from telebot import types
from telebot.types import MessageEntity, InputMediaPhoto
from telebot.apihelper import ApiTelegramException
import random
import string
import emoji
import json
import os
import hashlib
import time

# --- CONFIGURATION ---
TOKEN = "8396145721:AAE1x4t6352dnKIO6lIplhBu3zQmnmprDzs"
ADMIN_ID = 7350349936
bot = telebot.TeleBot(TOKEN)

# --- PERSISTED FILES ---
USERS_FILE = "users.json"
BANNED_FILE = "banned.json"
FORCE_JOIN_FILE = "force_join.json"
EMOJI_MAP_FILE = "emoji.json"
THEME_FILE = "theme.json"

# --- SMALL CAPS CONVERTER ---
SMALL_CAPS_MAP = {
    'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E',
    'F': 'F', 'G': 'G', 'H': 'H', 'I': 'I', 'J': 'J',
    'K': 'K', 'L': 'L', 'M': 'M', 'N': 'N', 'O': 'O',
    'P': 'P', 'Q': 'Q', 'R': 'R', 'S': 'S', 'T': 'T',
    'U': 'U', 'V': 'V', 'W': 'W', 'X': 'X', 'Y': 'Y', 'Z': 'Z',
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ',
    'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ',
    'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ',
    'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ',
    'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
    '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
    ' ': ' ', '.': '.', ',': ',', '!': '!', '?': '?',
    "'": "'", '"': '"', '(': '(', ')': ')', '-': '-',
    '_': '_', '=': '=', '+': '+', '/': '/', '\\': '\\',
    '@': '@', '#': '#', '$': '$', '%': '%', '^': '^',
    '&': '&', '*': '*', ':': ':', ';': ';', '<': '<',
    '>': '>', '`': '`', '~': '~'
}

def to_small_caps(text):
    """Convert text to stylish small caps format"""
    if not text:
        return text
    result = []
    for char in text:
        result.append(SMALL_CAPS_MAP.get(char, char))
    return ''.join(result)

def to_title_small_caps(text):
    """Convert title to small caps with first letter bigger"""
    words = text.split()
    result = []
    for word in words:
        if word:
            first = word[0].upper()
            rest = to_small_caps(word[1:])
            result.append(first + rest)
        else:
            result.append('')
    return ' '.join(result)

# --- THEME FUNCTIONS ---
DEFAULT_THEME = "light"

def load_user_theme(user_id):
    if os.path.exists(THEME_FILE):
        with open(THEME_FILE, "r") as f:
            themes = json.load(f)
            return themes.get(str(user_id), DEFAULT_THEME)
    return DEFAULT_THEME

def save_user_theme(user_id, theme):
    themes = {}
    if os.path.exists(THEME_FILE):
        with open(THEME_FILE, "r") as f:
            themes = json.load(f)
    themes[str(user_id)] = theme
    with open(THEME_FILE, "w") as f:
        json.dump(themes, f)

# --- LOAD JSON FUNCTIONS ---
def load_json_set(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return set(json.load(f))
    return set(default)

def load_json_list(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return list(json.load(f))
    return list(default)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(list(data), f)

registered_users = load_json_set(USERS_FILE, [])
banned_users = load_json_set(BANNED_FILE, [])
MUST_JOIN = load_json_list(FORCE_JOIN_FILE,["@SIAM_CoDeXFILE"])

def save_users(): save_json(USERS_FILE, registered_users)
def save_banned(): save_json(BANNED_FILE, banned_users)
def save_force_join(): save_json(FORCE_JOIN_FILE, MUST_JOIN)

# --- LOAD PREMIUM EMOJI MAP ---
EMOJI_TO_PREMIUM = {}
ALL_PREMIUM_IDS = []
DEAD_IDS = set()

def load_emoji_map():
    global EMOJI_TO_PREMIUM, ALL_PREMIUM_IDS
    EMOJI_TO_PREMIUM, ALL_PREMIUM_IDS = {}, []
    if not os.path.exists(EMOJI_MAP_FILE):
        return
    with open(EMOJI_MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    buckets = {}
    for pack in data.get("combined_packs", []):
        for item in pack.get("emojis", []):
            char, eid = item.get("emoji"), item.get("id")
            if not char or not eid:
                continue
            buckets.setdefault(char, []).append(eid)
            ALL_PREMIUM_IDS.append(eid)
    for char, ids in buckets.items():
        rng = random.Random(char)
        EMOJI_TO_PREMIUM[char] = rng.choice(ids)

load_emoji_map()

def get_premium_id(char):
    mapped = EMOJI_TO_PREMIUM.get(char)
    if mapped and mapped not in DEAD_IDS:
        return mapped
    pool = [i for i in ALL_PREMIUM_IDS if i not in DEAD_IDS]
    if pool:
        rng = random.Random(char)
        return rng.choice(pool)
    return None

# --- GLOBAL VARIABLES ---
posts_db = {}
user_channels = {}
temp_data = {}

# --- UTILITY FUNCTIONS ---
def generate_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def is_banned(chat_id):
    return chat_id in banned_users

def check_must_join(user_id):
    for channel in MUST_JOIN:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

# --- CONVERT EVERY EMOJI TO PREMIUM ---
def build_entities_for_text(input_text, original_entities=None):
    original_entities = original_entities or []
    final_text, new_entities = "", []
    offset_map = {}
    current_old_offset, current_new_offset = 0, 0

    fallback_pool = [i for i in ALL_PREMIUM_IDS if i not in DEAD_IDS]

    for char in input_text:
        offset_map[current_old_offset] = current_new_offset
        if emoji.is_emoji(char):
            pid = get_premium_id(char)
            
            if not pid and fallback_pool:
                char_hash = int(hashlib.md5(char.encode('utf-8')).hexdigest(), 16)
                random.seed(char_hash)
                pid = random.choice(fallback_pool)
                random.seed()
            
            placeholder = "✨"
            if pid:
                new_entities.append(MessageEntity(
                    type="custom_emoji", 
                    offset=current_new_offset, 
                    length=len(placeholder), 
                    custom_emoji_id=pid
                ))
                final_text += placeholder
                char_len = len(char.encode('utf-16-le')) // 2
                current_old_offset += char_len
                current_new_offset += len(placeholder)
            else:
                final_text += char
                char_len = len(char.encode('utf-16-le')) // 2
                current_old_offset += char_len
                current_new_offset += len(char)
        else:
            final_text += char
            current_old_offset += 1
            current_new_offset += 1

    offset_map[current_old_offset] = current_new_offset
    for ent in original_entities:
        if ent.type == "custom_emoji":
            continue
        new_start, new_end = offset_map.get(ent.offset), offset_map.get(ent.offset + ent.length)
        if new_start is not None and new_end is not None:
            new_entities.append(MessageEntity(
                type=ent.type, 
                offset=new_start, 
                length=new_end - new_start, 
                url=ent.url, 
                user=ent.user, 
                language=ent.language, 
                custom_emoji_id=ent.custom_emoji_id
            ))
    return final_text, new_entities

def process_text_and_entities(message):
    input_text = message.text or message.caption or ""
    original_entities = message.entities or message.caption_entities or []
    return build_entities_for_text(input_text, original_entities)

def strip_custom_emoji(entities):
    return [e for e in entities if e.type != "custom_emoji"]

# --- SAFE SEND WRAPPERS ---
def _mark_dead_ids_from_error(entities, error_text):
    for e in entities:
        if e.type == "custom_emoji" and e.custom_emoji_id:
            DEAD_IDS.add(e.custom_emoji_id)

def _is_custom_emoji_error(e):
    s = str(e).upper()
    return "CUSTOM_EMOJI" in s or "CUSTOM EMOJI" in s

def safe_send_message(chat_id, text, entities=None, reply_markup=None, parse_mode=None):
    entities = entities or []
    kwargs = {"entities": entities} if entities else {"parse_mode": parse_mode}
    try:
        return bot.send_message(chat_id, text, reply_markup=reply_markup, **kwargs)
    except ApiTelegramException as e:
        if _is_custom_emoji_error(e):
            _mark_dead_ids_from_error(entities, str(e))
            stripped = strip_custom_emoji(entities)
            kwargs2 = {"entities": stripped} if stripped else {}
            return bot.send_message(chat_id, text, reply_markup=reply_markup, **kwargs2)
        raise

def safe_send_photo(chat_id, photo_id, caption, entities=None, reply_markup=None):
    entities = entities or []
    kwargs = {"caption_entities": entities} if entities else {}
    try:
        return bot.send_photo(chat_id, photo_id, caption=caption, reply_markup=reply_markup, **kwargs)
    except ApiTelegramException as e:
        if _is_custom_emoji_error(e):
            _mark_dead_ids_from_error(entities, str(e))
            stripped = strip_custom_emoji(entities)
            kwargs2 = {"caption_entities": stripped} if stripped else {}
            return bot.send_photo(chat_id, photo_id, caption=caption, reply_markup=reply_markup, **kwargs2)
        raise

def safe_send_document(chat_id, doc_id, caption, entities=None, reply_markup=None):
    entities = entities or []
    kwargs = {"caption_entities": entities} if entities else {}
    try:
        return bot.send_document(chat_id, doc_id, caption=caption, reply_markup=reply_markup, **kwargs)
    except ApiTelegramException as e:
        if _is_custom_emoji_error(e):
            _mark_dead_ids_from_error(entities, str(e))
            stripped = strip_custom_emoji(entities)
            kwargs2 = {"caption_entities": stripped} if stripped else {}
            return bot.send_document(chat_id, doc_id, caption=caption, reply_markup=reply_markup, **kwargs2)
        raise

def safe_send_video(chat_id, video_id, caption, entities=None, reply_markup=None):
    entities = entities or []
    kwargs = {"caption_entities": entities} if entities else {}
    try:
        return bot.send_video(chat_id, video_id, caption=caption, reply_markup=reply_markup, **kwargs)
    except ApiTelegramException as e:
        if _is_custom_emoji_error(e):
            _mark_dead_ids_from_error(entities, str(e))
            stripped = strip_custom_emoji(entities)
            kwargs2 = {"caption_entities": stripped} if stripped else {}
            return bot.send_video(chat_id, video_id, caption=caption, reply_markup=reply_markup, **kwargs2)
        raise

# --- SEND CARD WITH STYLISH TEXT ---
def send_card(chat_id, icon_left, icon_right, title, body, reply_markup=None, theme=None):
    if theme is None:
        theme = load_user_theme(chat_id)
    
    title_stylish = to_title_small_caps(title)
    body_stylish = to_small_caps(body)
    
    if theme == "dark":
        bar = "━" * 12
        raw = f"{icon_left} {bar} {icon_right}\n{title_stylish}\n{icon_right} {bar} {icon_left}\n\n{body_stylish}"
        raw += "\n\n🌙 Dᴀʀᴋ Mᴏᴅᴇ"
    else:
        bar = "━" * 12
        raw = f"{icon_left} {bar} {icon_right}\n{title_stylish}\n{icon_right} {bar} {icon_left}\n\n{body_stylish}"
    
    text, entities = build_entities_for_text(raw)
    
    title_start = text.index(title_stylish) if title_stylish in text else 0
    entities.append(MessageEntity(type="bold", offset=title_start, length=len(title_stylish)))
    
    return safe_send_message(chat_id, text, entities=entities, reply_markup=reply_markup)

# ==============================
# ✅ BUTTON LABELS TEXT
# ==============================
BTN_MAKE_POST_TEXT = "Make Post"
BTN_CONNECT_TEXT = "Connect"
BTN_SEND_TEXT = "Send"
BTN_HELP_TEXT = "Help"
BTN_ABOUT_TEXT = "About"
BTN_STATS_TEXT = "Stats"
BTN_ADMIN_TEXT = "Admin"
BTN_THEME_TEXT = "Change Theme"
BTN_TEMPLATES_TEXT = "Templates"

# প্রিমিয়াম ইমোজি আইডিসমূহ
EMOJI_POST = "6339079894458179573"       # 📝 Create Post
EMOJI_CONNECT = "6052991826518873591"    # 📡 Connect
EMOJI_SEND = "6246919169120408471"       # 📤 Send
EMOJI_HELP = "6053275839821257175"       # ℹ️ Help / Info
EMOJI_ABOUT = "6253402340649345001"      # 🤩 About
EMOJI_STATS = "6053234303192537471"      # 📊 Stats
EMOJI_ADMIN = "6316699945160153819"      # 🛠 Admin
EMOJI_THEME = "6244762094810436779"      # 🎨 Theme
EMOJI_TEMPLATES = "6339280615459789282"  # 📂 Templates

# বাটন টেক্সট (Small Caps)
BTN_MAKE_POST = f"{to_title_small_caps(BTN_MAKE_POST_TEXT)}"
BTN_CONNECT = f"{to_title_small_caps(BTN_CONNECT_TEXT)}"
BTN_SEND = f"{to_title_small_caps(BTN_SEND_TEXT)}"
BTN_HELP = f"{to_title_small_caps(BTN_HELP_TEXT)}"
BTN_ABOUT = f"{to_title_small_caps(BTN_ABOUT_TEXT)}"
BTN_STATS = f"{to_title_small_caps(BTN_STATS_TEXT)}"
BTN_ADMIN = f"{to_title_small_caps(BTN_ADMIN_TEXT)}"
BTN_THEME = f"{to_title_small_caps(BTN_THEME_TEXT)}"
BTN_TEMPLATES = f"{to_title_small_caps(BTN_TEMPLATES_TEXT)}"


def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🔥 𝗖𝗵𝗼𝗼𝘀𝗲 𝗮𝗻 𝗼𝗽𝘁𝗶𝗼𝗻..."
    )

    # 🔵 Primary Buttons (নীল বাটন)
    btn_post = types.KeyboardButton(
        text=BTN_MAKE_POST,
        icon_custom_emoji_id=EMOJI_POST,
        style="primary"
    )
    btn_connect = types.KeyboardButton(
        text=BTN_CONNECT,
        icon_custom_emoji_id=EMOJI_CONNECT,
        style="primary"
    )

    # 🟢 Success Buttons (সবুজ বাটন)
    btn_send = types.KeyboardButton(
        text=BTN_SEND,
        icon_custom_emoji_id=EMOJI_SEND,
        style="success"
    )
    btn_help = types.KeyboardButton(
        text=BTN_HELP,
        icon_custom_emoji_id=EMOJI_HELP,
        style="success"
    )
    btn_about = types.KeyboardButton(
        text=BTN_ABOUT,
        icon_custom_emoji_id=EMOJI_ABOUT,
        style="success"
    )
    btn_stats = types.KeyboardButton(
        text=BTN_STATS,
        icon_custom_emoji_id=EMOJI_STATS,
        style="success"
    )

    # 🔵 Primary Buttons (Theme & Templates)
    btn_theme = types.KeyboardButton(
        text=BTN_THEME,
        icon_custom_emoji_id=EMOJI_THEME,
        style="primary"
    )
    btn_templates = types.KeyboardButton(
        text=BTN_TEMPLATES,
        icon_custom_emoji_id=EMOJI_TEMPLATES,
        style="primary"
    )

    # 🔴 Danger Button (Admin Panel - লাল বাটন)
    btn_admin = types.KeyboardButton(
        text=BTN_ADMIN,
        icon_custom_emoji_id=EMOJI_ADMIN,
        style="danger"
    )

    # রিপ্লাই কীবোর্ডে রো অনুযায়ী বাটন সাজানো
    markup.add(btn_post, btn_help)
    markup.add(btn_about, btn_stats)
    markup.add(btn_connect, btn_send)
    markup.add(btn_theme, btn_templates)

    if user_id == ADMIN_ID:
        markup.add(btn_admin)

    return markup

def add_button_choice_keyboard():
    """Inline buttons with color options"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.row(
        types.InlineKeyboardButton(
            text="⚪ Normal",
            callback_data="post_add_btn_normal"
        ),
        types.InlineKeyboardButton(
            text="🔵 Blue",
            callback_data="post_add_btn_blue",
            style="primary"
        )
    )
    markup.row(
        types.InlineKeyboardButton(
            text="🟢 Green",
            callback_data="post_add_btn_green",
            style="success"
        ),
        types.InlineKeyboardButton(
            text="⏭ Skip",
            callback_data="post_skip_btn",
            style="primary"
        )
    )
    return markup

def build_colored_post_markup(data):
    """Build colored inline button markup"""
    if not data.get("btn_name") or not data.get("btn_url"):
        return None
    
    btn_color = data.get("btn_color", "normal")
    btn_text = data["btn_name"]
    
    markup = types.InlineKeyboardMarkup()
    
    if btn_color == "blue":
        btn_text = f"🔵 {btn_text}"
    elif btn_color == "green":
        btn_text = f"🟢 {btn_text}"
    
    btn = types.InlineKeyboardButton(
        text=btn_text,
        url=data["btn_url"]
    )
    
    markup.add(btn)
    return markup

def theme_keyboard(user_id):
    current_theme = load_user_theme(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    light_btn = types.InlineKeyboardButton(
        text="☀️ Light",
        callback_data="theme_light",
        style="primary"
    )
    dark_btn = types.InlineKeyboardButton(
        text="🌙 Dark",
        callback_data="theme_dark",
        style="primary"
    )
    
    if current_theme == "light":
        light_btn = types.InlineKeyboardButton(
            text="☀️ Light ✅",
            callback_data="theme_light",
            style="primary"
        )
    else:
        dark_btn = types.InlineKeyboardButton(
            text="🌙 Dark ✅",
            callback_data="theme_dark",
            style="primary"
        )
    
    markup.add(light_btn, dark_btn)
    return markup

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Status", callback_data="admin_status", style="primary"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast", style="primary"),
    )
    markup.add(
        types.InlineKeyboardButton("👥 Export Users", callback_data="admin_export_users", style="primary"),
        types.InlineKeyboardButton("🗒 List Posts", callback_data="admin_list_posts", style="primary"),
    )
    markup.add(
        types.InlineKeyboardButton("📡 All Channels", callback_data="admin_all_channels", style="primary"),
        types.InlineKeyboardButton("🗑 Delete Post", callback_data="admin_delete_post", style="primary"),
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user", style="danger"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_user", style="success"),
    )
    markup.add(
        types.InlineKeyboardButton("➕ Add Force-Join", callback_data="admin_add_forcejoin", style="primary"),
        types.InlineKeyboardButton("➖ Remove Force-Join", callback_data="admin_remove_forcejoin", style="primary"),
    )
    markup.add(
        types.InlineKeyboardButton("📋 Force-Join List", callback_data="admin_list_forcejoin", style="primary"),
        types.InlineKeyboardButton("🔁 Reload Emoji Map", callback_data="admin_reload_emoji", style="primary"),
    )
    markup.row(
        types.InlineKeyboardButton("🎨 Set Default Theme", callback_data="admin_set_theme", style="primary")
    )
    return markup
    
# --- BLOCK BANNED USERS ---
def blocked(message):
    if is_banned(message.chat.id) and message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "🚫 Yᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.")
        return True
    return False

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(message):
    if blocked(message):
        return
    if message.chat.id not in registered_users:
        registered_users.add(message.chat.id)
        save_users()

    if not check_must_join(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in MUST_JOIN:
            markup.row(types.InlineKeyboardButton(f"Jᴏɪɴ {ch}", url=f"https://t.me/{ch.lstrip('@')}"))
        markup.row(types.InlineKeyboardButton("Vᴇʀɪғʏ Jᴏɪɴ ✅", callback_data="check_join"))
        return send_card(
            message.chat.id,
            "❌", "🔒",
            "Aᴄᴄᴇsꜱ Dᴇɴɪᴇᴅ",
            "Tᴏ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ, ᴊᴏɪɴ ᴀʟʟ ᴛʜᴇ ᴄʜᴀɴɴᴇʟs ʙᴇʟᴏᴡ ᴀɴᴅ ᴛᴀᴘ Vᴇʀɪғʏ Jᴏɪɴ.",
            reply_markup=markup
        )

    send_card(
        message.chat.id,
        "👑", "✨",
        "Wᴇʟᴄᴏᴍᴇ Tᴏ SIAM Emoji Bot",
        "Tʜɪs ʙᴏᴛ ᴄᴏɴᴠᴇʀᴛs ʏᴏᴜʀ ɴᴏʀᴍᴀʟ ᴇᴍᴏᴊɪs ɪɴᴛᴏ ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪs.",
        reply_markup=main_menu(message.chat.id)
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_callback(call):
    if check_must_join(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Vᴇʀɪғɪᴇᴅ!")
        bot.send_message(call.message.chat.id, "✅ Vᴇʀɪғɪᴇᴅ! Sᴇɴᴅ /sᴛᴀʀᴛ ᴛᴏ ʙᴇɢɪɴ.", reply_markup=main_menu(call.message.chat.id))
    else:
        bot.answer_callback_query(call.id, "❌ Yᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟs ʏᴇᴛ", show_alert=True)

@bot.message_handler(func=lambda m: m.text == BTN_HELP)
def help_handler(message):
    if blocked(message):
        return
    body = (
        f"📝 Mᴀᴋᴇ Pᴏsᴛ — Cʀᴇᴀᴛᴇ ᴀ ᴘᴏsᴛ (ᴛᴇxᴛ/ᴘʜᴏᴛᴏ/ᴅᴏᴄᴜᴍᴇɴᴛ + ᴏᴘᴛɪᴏɴᴀʟ ʙᴜᴛᴛᴏɴ)\n"
        f"📡 Cᴏɴɴᴇᴄᴛ — Cᴏɴɴᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ʏᴏᴜ ᴀᴅᴍɪɴ\n"
        f"📤 Sᴇɴᴅ — Sᴇɴᴅ ᴀ sᴀᴠᴇᴅ ᴘᴏsᴛ ᴛᴏ ᴀ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴄʜᴀɴɴᴇʟ\n"
        "/ᴄᴀɴᴄᴇʟ — Cᴀɴᴄᴇʟ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ᴀᴄᴛɪᴏɴ"
    )
    send_card(
        message.chat.id,
        "❓", "📖",
        "Hᴇʟᴘ",
        body
    )

@bot.message_handler(func=lambda m: m.text == BTN_ABOUT)
def about_handler(message):
    if blocked(message):
        return
    body = "• Sᴀᴍᴇ ᴇᴍᴏᴊɪ = sᴀᴍᴇ ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ\n• Mᴜʟᴛɪ-ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ᴄʀᴇᴀᴛᴏʀ\n• Oᴘᴛɪᴏɴᴀʟ ɪɴʟɪɴᴇ ʙᴜᴛᴛᴏɴs ᴏɴ ᴘᴏsᴛs\n\nDᴇᴠᴇʟᴏᴘᴇʀ: @SIAM_CODEX"
    send_card(
        message.chat.id,
        "ℹ️", "✨",
        "Aʙᴏᴜᴛ Bᴏᴛ",
        body
    )

@bot.message_handler(func=lambda m: m.text == BTN_STATS)
def stats_handler(message):
    if blocked(message):
        return
    body = (
        f"👤 Tᴏᴛᴀʟ Usᴇʀs: {len(registered_users)}\n"
        f"🗃 Sᴀᴠᴇᴅ Pᴏsᴛs: {len(posts_db)}\n"
        f"📡 Cᴏɴɴᴇᴄᴛᴇᴅ Cʜᴀɴɴᴇʟs (ʏᴏᴜ): {len(user_channels.get(message.chat.id, []))}"
    )
    send_card(
        message.chat.id,
        "📊", "🗂",
        "Sᴛᴀᴛs",
        body
    )

@bot.message_handler(func=lambda m: m.text == BTN_THEME)
def theme_settings(message):
    if blocked(message):
        return
    
    current_theme = load_user_theme(message.chat.id)
    theme_preview = "☀️ Lɪɢʜᴛ" if current_theme == "light" else "🌙 Dᴀʀᴋ"
    
    markup = theme_keyboard(message.chat.id)
    send_card(
        message.chat.id,
        "🎨", "🌈",
        "Tʜᴇᴍᴇ Sᴇᴛᴛɪɴɢs",
        f"Cᴜʀʀᴇɴᴛ Tʜᴇᴍᴇ: {theme_preview}\n\nCʜᴏᴏsᴇ ʏᴏᴜʀ ᴘʀᴇғᴇʀʀᴇᴅ ᴛʜᴇᴍᴇ:",
        reply_markup=markup,
        theme=current_theme
    )

@bot.message_handler(func=lambda m: m.text == BTN_TEMPLATES)
def template_list(message):
    if blocked(message):
        return
    send_card(
        message.chat.id,
        "📂", "📋",
        "Tᴇᴍᴘʟᴀᴛᴇs",
        "📌 Fᴇᴀᴛᴜʀᴇ Cᴏᴍɪɴɢ Sᴏᴏɴ!\n\nSᴀᴠᴇ ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ ᴘᴏsᴛ ғᴏʀᴍᴀᴛs.",
        reply_markup=main_menu(message.chat.id),
        theme=load_user_theme(message.chat.id)
    )

# --- ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == BTN_ADMIN and m.chat.id == ADMIN_ID)
def admin_panel(message):
    send_card(
        message.chat.id,
        "🛠", "👑",
        "Aᴅᴍɪɴ Pᴀɴᴇʟ",
        "Wᴇʟᴄᴏᴍᴇ, ᴀᴅᴍɪɴ. Cʜᴏᴏsᴇ ᴀ ғᴇᴀᴛᴜʀᴇ ʙᴇʟᴏᴡ.",
        reply_markup=admin_keyboard(),
        theme=load_user_theme(message.chat.id)
    )

def admin_only(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Aᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
        return True
    return False

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback(call):
    if admin_only(call):
        return
    bot.answer_callback_query(call.id)
    cid = call.message.chat.id

    if call.data == "admin_status":
        send_card(cid, "📊", "👑", "Bᴏᴛ Sᴛᴀᴛᴜs",
                   f"Usᴇʀs: {len(registered_users)}\nBᴀɴɴᴇᴅ: {len(banned_users)}\nPᴏsᴛs sᴀᴠᴇᴅ: {len(posts_db)}\nDᴇᴀᴅ ᴇᴍᴏᴊɪ IDs sᴋɪᴘᴘᴇᴅ: {len(DEAD_IDS)}")

    elif call.data == "admin_broadcast":
        sent = bot.send_message(cid, "Sᴇɴᴅ ᴛʜᴇ ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇ (ᴛᴇxᴛ/ᴘʜᴏᴛᴏ/ᴠɪᴅᴇᴏ):")
        bot.register_next_step_handler(sent, perform_broadcast)

    elif call.data == "admin_export_users":
        if not registered_users:
            return bot.send_message(cid, "Nᴏ ᴜsᴇʀs ʏᴇᴛ.")
        chunk = "\n".join(str(u) for u in list(registered_users)[:200])
        bot.send_message(cid, f"👥 Usᴇʀs ({len(registered_users)} ᴛᴏᴛᴀʟ, sʜᴏᴡɪɴɢ ᴜᴘ ᴛᴏ 200):\n<code>{chunk}</code>", parse_mode="HTML")

    elif call.data == "admin_list_posts":
        if not posts_db:
            return bot.send_message(cid, "Nᴏ sᴀᴠᴇᴅ ᴘᴏsᴛs.")
        lines = [f"• {pid} — {'ᴘʜᴏᴛᴏ' if d['photo_id'] else 'ᴅᴏᴄᴜᴍᴇɴᴛ' if d['document_id'] else 'ᴛᴇxᴛ'}" for pid, d in posts_db.items()]
        bot.send_message(cid, "🗒 Sᴀᴠᴇᴅ Pᴏsᴛs:\n" + "\n".join(lines))

    elif call.data == "admin_all_channels":
        if not user_channels:
            return bot.send_message(cid, "Nᴏ ᴄʜᴀɴɴᴇʟs ᴄᴏɴɴᴇᴄᴛᴇᴅ ʙʏ ᴀɴʏᴏɴᴇ ʏᴇᴛ.")
        lines = []
        for owner, chans in user_channels.items():
            for c in chans:
                lines.append(f"• {c['title']} (ᴏᴡɴᴇʀ: {owner})")
        bot.send_message(cid, "📡 Aʟʟ Cᴏɴɴᴇᴄᴛᴇᴅ Cʜᴀɴɴᴇʟs:\n" + "\n".join(lines))

    elif call.data == "admin_delete_post":
        sent = bot.send_message(cid, "Sᴇɴᴅ ᴛʜᴇ Pᴏsᴛ ID ᴛᴏ ᴅᴇʟᴇᴛᴇ:")
        bot.register_next_step_handler(sent, admin_do_delete_post)

    elif call.data == "admin_ban_user":
        sent = bot.send_message(cid, "Sᴇɴᴅ ᴛʜᴇ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ID ᴛᴏ ʙᴀɴ:")
        bot.register_next_step_handler(sent, admin_do_ban)

    elif call.data == "admin_unban_user":
        sent = bot.send_message(cid, "Sᴇɴᴅ ᴛʜᴇ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ID ᴛᴏ ᴜɴʙᴀɴ:")
        bot.register_next_step_handler(sent, admin_do_unban)

    elif call.data == "admin_add_forcejoin":
        sent = bot.send_message(cid, "Sᴇɴᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ @ᴜsᴇʀɴᴀᴍᴇ ᴛᴏ ADD ᴛᴏ ғᴏʀᴄᴇ-ᴊᴏɪɴ ʟɪsᴛ:")
        bot.register_next_step_handler(sent, admin_do_add_forcejoin)

    elif call.data == "admin_remove_forcejoin":
        sent = bot.send_message(cid, "Sᴇɴᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ @ᴜsᴇʀɴᴀᴍᴇ ᴛᴏ REMOVE ғʀᴏᴍ ғᴏʀᴄᴇ-ᴊᴏɪɴ ʟɪsᴛ:")
        bot.register_next_step_handler(sent, admin_do_remove_forcejoin)

    elif call.data == "admin_list_forcejoin":
        bot.send_message(cid, "📋 Fᴏʀᴄᴇ-Jᴏɪɴ Cʜᴀɴɴᴇʟs:\n" + ("\n".join(MUST_JOIN) if MUST_JOIN else "Nᴏɴᴇ sᴇᴛ."))

    elif call.data == "admin_reload_emoji":
        load_emoji_map()
        DEAD_IDS.clear()
        bot.send_message(cid, f"🔁 Rᴇʟᴏᴀᴅᴇᴅ. {len(ALL_PREMIUM_IDS)} ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ IDs ʟᴏᴀᴅᴇᴅ, {len(EMOJI_TO_PREMIUM)} ᴜɴɪǫᴜᴇ ᴍᴀᴘᴘᴇᴅ ᴄʜᴀʀs.")

    elif call.data == "admin_set_theme":
        sent = bot.send_message(cid, "Sᴇᴛ ᴅᴇғᴀᴜʟᴛ ᴛʜᴇᴍᴇ ғᴏʀ ᴀʟʟ ᴜsᴇʀs:\nTʏᴘᴇ: 'ʟɪɢʜᴛ' ᴏʀ 'ᴅᴀʀᴋ'")
        bot.register_next_step_handler(sent, admin_do_set_theme)

def admin_do_set_theme(message):
    theme = message.text.strip().lower()
    if theme not in ["light", "dark"]:
        return bot.send_message(message.chat.id, "❌ Pʟᴇᴀsᴇ ᴛʏᴘᴇ 'ʟɪɢʜᴛ' ᴏʀ 'ᴅᴀʀᴋ'")
    
    count = 0
    for user_id in registered_users:
        save_user_theme(user_id, theme)
        count += 1
    
    bot.send_message(message.chat.id, f"✅ Dᴇғᴀᴜʟᴛ ᴛʜᴇᴍᴇ sᴇᴛ ᴛᴏ {theme.upper()} ғᴏʀ {count} ᴜsᴇʀs.")

# --- ADMIN ACTIONS ---
def perform_broadcast(message):
    success, fail = 0, 0
    for user_id in registered_users:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id)
            success += 1
        except Exception:
            fail += 1
    bot.send_message(ADMIN_ID, f"📢 Bʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ.\n✅ Sᴜᴄᴄᴇss: {success}\n❌ Fᴀɪʟᴇᴅ: {fail}")

def admin_do_delete_post(message):
    pid = message.text.strip().upper()
    if pid in posts_db:
        del posts_db[pid]
        bot.send_message(message.chat.id, f"🗑 Dᴇʟᴇᴛᴇᴅ ᴘᴏsᴛ {pid}.")
    else:
        bot.send_message(message.chat.id, "❌ Pᴏsᴛ ID ɴᴏᴛ ғᴏᴜɴᴅ.")

def admin_do_ban(message):
    try:
        uid = int(message.text.strip())
        banned_users.add(uid)
        save_banned()
        bot.send_message(message.chat.id, f"🚫 Bᴀɴɴᴇᴅ ᴜsᴇʀ {uid}.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ID.")

def admin_do_unban(message):
    try:
        uid = int(message.text.strip())
        banned_users.discard(uid)
        save_banned()
        bot.send_message(message.chat.id, f"✅ Uɴʙᴀɴɴᴇᴅ ᴜsᴇʀ {uid}.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ID.")

def admin_do_add_forcejoin(message):
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch
    if ch not in MUST_JOIN:
        MUST_JOIN.append(ch)
        save_force_join()
    bot.send_message(message.chat.id, f"➕ Aᴅᴅᴇᴅ {ch} ᴛᴏ ғᴏʀᴄᴇ-ᴊᴏɪɴ ʟɪsᴛ.")

def admin_do_remove_forcejoin(message):
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch
    if ch in MUST_JOIN:
        MUST_JOIN.remove(ch)
        save_force_join()
        bot.send_message(message.chat.id, f"➖ Rᴇᴍᴏᴠᴇᴅ {ch} ғʀᴏᴍ ғᴏʀᴄᴇ-ᴊᴏɪɴ ʟɪsᴛ.")
    else:
        bot.send_message(message.chat.id, "❌ Tʜᴀᴛ ᴄʜᴀɴɴᴇʟ ɪsɴ'ᴛ ɪɴ ᴛʜᴇ ʟɪsᴛ.")

# --- THEME CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("theme_"))
def theme_callback(call):
    if call.from_user.id != call.message.chat.id:
        bot.answer_callback_query(call.id, "❌ Tʜɪs ɪs ғᴏʀ ʏᴏᴜ ᴏɴʟʏ!")
        return
    
    theme = call.data.split("_")[1]
    save_user_theme(call.from_user.id, theme)
    
    bot.answer_callback_query(call.id, f"✅ Tʜᴇᴍᴇ sᴇᴛ ᴛᴏ {theme.upper()}!")
    
    send_card(
        call.message.chat.id,
        "✅", "🎨",
        f"Tʜᴇᴍᴇ: {theme.upper()}",
        f"Yᴏᴜʀ ᴛʜᴇᴍᴇ ʜᴀs ʙᴇᴇɴ sᴇᴛ ᴛᴏ {theme.upper()} ᴍᴏᴅᴇ!",
        reply_markup=theme_keyboard(call.from_user.id),
        theme=theme
    )

# ============================================================
# ✅ FIXED: POST CREATION WITH PROPER ERROR HANDLING
# ============================================================

@bot.message_handler(func=lambda m: m.text == BTN_MAKE_POST)
def start_post(message):
    if blocked(message):
        return
    sent_card_text = (
        "Sᴇɴᴅ ʏᴏᴜʀ ᴘᴏsᴛ ᴄᴏɴᴛᴇɴᴛ ɴᴏᴡ\n\n"
        "➡️ Sᴜᴘᴘᴏʀᴛᴇᴅ ᴛʏᴘᴇs:\n"
        "• Tᴇxᴛ ᴍᴇssᴀɢᴇ\n"
        "• Pʜᴏᴛᴏ + ᴄᴀᴘᴛɪᴏɴ\n"
        "• Dᴏᴄᴜᴍᴇɴᴛ + ᴄᴀᴘᴛɪᴏɴ\n"
        "• Vɪᴅᴇᴏ + ᴄᴀᴘᴛɪᴏɴ\n\n"
        "✨ Sᴀᴍᴇ ᴇᴍᴏᴊɪ = sᴀᴍᴇ ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ ✨\n\n"
        "Cᴀɴᴄᴇʟ: /ᴄᴀɴᴄᴇʟ"
    )
    send_card(
        message.chat.id,
        "⭐", "📢",
        "Pᴏsᴛ Cʀᴇᴀᴛᴏʀ",
        sent_card_text
    )
    sent = bot.send_message(message.chat.id, "👇 Sᴇɴᴅ ɪᴛ ɴᴏᴡ:")
    bot.register_next_step_handler(sent, process_post_content)

def process_post_content(message):
    """Process post content with proper error handling"""
    if message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Cᴀɴᴄᴇʟʟᴇᴅ.", reply_markup=main_menu(message.chat.id))
    
    photo_id = None
    document_id = None
    video_id = None
    
    # Log what we received
    print(f"📨 Content Type: {message.content_type}")
    
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
        print(f"📸 Photo ID: {photo_id}")
    
    elif message.content_type == 'document':
        document_id = message.document.file_id
        print(f"📄 Document ID: {document_id}")
    
    elif message.content_type == 'video':
        video_id = message.video.file_id
        print(f"🎬 Video ID: {video_id}")
    
    elif message.content_type == 'text':
        print(f"📝 Text: {message.text[:50]}...")
    
    else:
        bot.send_message(
            message.chat.id, 
            f"❌ Uɴsᴜᴘᴘᴏʀᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ ᴛʏᴘᴇ: {message.content_type}\n\nPʟᴇᴀsᴇ sᴇɴᴅ ᴛᴇxᴛ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, ᴏʀ ᴅᴏᴄᴜᴍᴇɴᴛ."
        )
        return
    
    # Process text and entities
    processed_text, entities = process_text_and_entities(message)
    
    # If no content was provided (empty text), use default
    if not processed_text and not photo_id and not document_id and not video_id:
        processed_text = "📝 Nᴏ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏᴠɪᴅᴇᴅ"
    
    temp_data[message.chat.id] = {
        "id": generate_id(),
        "content": processed_text,
        "entities": entities,
        "photo_id": photo_id,
        "document_id": document_id,
        "video_id": video_id,
        "media_group": [],
        "btn_name": None,
        "btn_url": None,
        "btn_color": "normal"
    }
    
    # Show button options
    send_card(
        message.chat.id,
        "✨", "🌙",
        "Iɴʟɪɴᴇ Bᴜᴛᴛᴏɴ",
        "Dᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴀᴅᴅ ᴀ ʙᴜᴛᴛᴏɴ ᴛᴏ ʏᴏᴜʀ ᴘᴏsᴛ?",
        reply_markup=add_button_choice_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("post_add_btn_"))
def post_button_choice(call):
    chat_id = call.message.chat.id
    if chat_id not in temp_data:
        return bot.answer_callback_query(call.id, "Sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ, sᴛᴀʀᴛ ᴀɢᴀɪɴ ᴡɪᴛʜ Mᴀᴋᴇ Pᴏsᴛ.", show_alert=True)
    
    bot.answer_callback_query(call.id)
    
    color = call.data.replace("post_add_btn_", "")
    temp_data[chat_id]["btn_color"] = color if color in ["normal", "blue", "green"] else "normal"
    
    send_card(
        chat_id,
        "👑", "🏷",
        "Bᴜᴛᴛᴏɴ Nᴀᴍᴇ",
        f"Sᴇʟᴇᴄᴛᴇᴅ: {color.upper()} ʙᴜᴛᴛᴏɴ\n\nSᴇɴᴅ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʟᴀʙᴇʟ ᴛᴇxᴛ.\nExᴀᴍᴘʟᴇ: Jᴏɪɴ Oᴜʀ Cʜᴀɴɴᴇʟ\n\n/cᴀɴᴄᴇʟ ᴛᴏ sᴛᴏᴘ.",
        theme=load_user_theme(chat_id)
    )
    sent = bot.send_message(chat_id, "👇")
    bot.register_next_step_handler(sent, process_button_name)

@bot.callback_query_handler(func=lambda call: call.data == "post_skip_btn")
def post_skip_button(call):
    chat_id = call.message.chat.id
    if chat_id not in temp_data:
        return bot.answer_callback_query(call.id, "Sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ.", show_alert=True)
    bot.answer_callback_query(call.id)
    finalize_post(chat_id)

def process_button_name(message):
    chat_id = message.chat.id
    if message.text == "/cancel":
        return bot.send_message(chat_id, "❌ Cᴀɴᴄᴇʟʟᴇᴅ.", reply_markup=main_menu(chat_id))
    temp_data[chat_id]["btn_name"] = message.text
    send_card(
        chat_id,
        "🔗", "🌐",
        "Bᴜᴛᴛᴏɴ Lɪɴᴋ",
        "Sᴇɴᴅ ᴛʜᴇ ʙᴜᴛᴛᴏɴ URL (ᴍᴜsᴛ sᴛᴀʀᴛ ᴡɪᴛʜ ʜᴛᴛᴘ:// ᴏʀ ʜᴛᴛᴘs://).\n\n/cᴀɴᴄᴇʟ ᴛᴏ sᴛᴏᴘ.",
        theme=load_user_theme(chat_id)
    )
    sent = bot.send_message(chat_id, "👇")
    bot.register_next_step_handler(sent, process_button_link)

def process_button_link(message):
    chat_id = message.chat.id
    if message.text == "/cancel":
        return bot.send_message(chat_id, "❌ Cᴀɴᴄᴇʟʟᴇᴅ.", reply_markup=main_menu(chat_id))
    if not (message.text.startswith("http://") or message.text.startswith("https://")):
        sent = bot.send_message(chat_id, "❌ Tʜᴀᴛ ᴅᴏᴇsɴ'ᴛ ʟᴏᴏᴋ ʟɪᴋᴇ ᴀ ᴠᴀʟɪᴅ URL. Sᴇɴᴅ ᴛʜᴇ ʙᴜᴛᴛᴏɴ URL ᴀɢᴀɪɴ:")
        return bot.register_next_step_handler(sent, process_button_link)
    temp_data[chat_id]["btn_url"] = message.text
    finalize_post(chat_id)

def finalize_post(chat_id):
    """Finalize and send post with proper error handling"""
    data = temp_data[chat_id]
    posts_db[data["id"]] = data
    markup = build_colored_post_markup(data)
    
    # Send saved confirmation
    send_card(
        chat_id,
        "✅", "🆔",
        "Pᴏsᴛ Sᴀᴠᴇᴅ",
        f"Pᴏsᴛ ID: {data['id']}\nPʀᴇᴠɪᴇᴡ ʙᴇʟᴏᴡ 👇",
        theme=load_user_theme(chat_id)
    )
    
    # Small delay to ensure message is sent
    time.sleep(0.5)
    
    has_content = False
    
    # Try to send photo
    if data.get("photo_id"):
        try:
            safe_send_photo(
                chat_id, 
                data["photo_id"], 
                data["content"], 
                entities=data.get("entities", []), 
                reply_markup=markup
            )
            has_content = True
            print("✅ Photo sent successfully")
        except Exception as e:
            print(f"❌ Photo send error: {e}")
            bot.send_message(chat_id, f"❌ Pʜᴏᴛᴏ sᴇɴᴅ ᴋʀᴛᴇ ᴘᴀʀʟᴀᴍ ɴᴀ!\nEʀʀᴏʀ: {str(e)[:80]}")
    
    # Try to send video
    elif data.get("video_id"):
        try:
            safe_send_video(
                chat_id, 
                data["video_id"], 
                data["content"], 
                entities=data.get("entities", []), 
                reply_markup=markup
            )
            has_content = True
            print("✅ Video sent successfully")
        except Exception as e:
            print(f"❌ Video send error: {e}")
            bot.send_message(chat_id, f"❌ Vɪᴅᴇᴏ sᴇɴᴅ ᴋʀᴛᴇ ᴘᴀʀʟᴀᴍ ɴᴀ!\nEʀʀᴏʀ: {str(e)[:80]}")
    
    # Try to send document
    elif data.get("document_id"):
        try:
            safe_send_document(
                chat_id, 
                data["document_id"], 
                data["content"], 
                entities=data.get("entities", []), 
                reply_markup=markup
            )
            has_content = True
            print("✅ Document sent successfully")
        except Exception as e:
            print(f"❌ Document send error: {e}")
            bot.send_message(chat_id, f"❌ Dᴏᴄᴜᴍᴇɴᴛ sᴇɴᴅ ᴋʀᴛᴇ ᴘᴀʀʟᴀᴍ ɴᴀ!\nEʀʀᴏʀ: {str(e)[:80]}")
    
    # Text only
    else:
        try:
            safe_send_message(
                chat_id, 
                data["content"], 
                entities=data.get("entities", []), 
                reply_markup=markup
            )
            has_content = True
            print("✅ Text sent successfully")
        except Exception as e:
            print(f"❌ Text send error: {e}")
            bot.send_message(chat_id, f"❌ Tᴇxᴛ sᴇɴᴅ ᴋʀᴛᴇ ᴘᴀʀʟᴀᴍ ɴᴀ!\nEʀʀᴏʀ: {str(e)[:80]}")
    
    # If nothing was sent, show error
    if not has_content:
        bot.send_message(
            chat_id, 
            "❌ Pᴏsᴛ sᴇɴᴅ ᴋʀᴛᴇ ᴘᴀʀʟᴀᴍ ɴᴀ!\n\n"
            "➡️ Pʟᴇᴀsᴇ ᴄʜᴇᴄᴋ:\n"
            "1. Fɪʟᴇ ɪs sᴛɪʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ\n"
            "2. Tʀʏ ᴀɢᴀɪɴ ᴡɪᴛʜ ᴅɪғғᴇʀᴇɴᴛ ғɪʟᴇ\n"
            "3. Usᴇ /sᴛᴀʀᴛ ᴛᴏ ʀᴇsᴛᴀʀᴛ"
        )
    
    # Clean up temp data
    if chat_id in temp_data:
        del temp_data[chat_id]

# --- CONNECT CHANNEL ---
@bot.message_handler(func=lambda m: m.text == BTN_CONNECT)
def ask_channel(message):
    if blocked(message):
        return
    send_card(
        message.chat.id,
        "📡", "🔗",
        "Cᴏɴɴᴇᴄᴛ Cʜᴀɴɴᴇʟ",
        "Fᴏʀᴡᴀʀᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ʜᴇʀᴇ, Oʀ ᴊᴜsᴛ ᴛʏᴘᴇ ɪᴛs @ᴜsᴇʀɴᴀᴍᴇ.\n\n"
        "⚠️ Mᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴅᴇᴅ ᴀs ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ.\n\n"
        "Cᴀɴᴄᴇʟ: /ᴄᴀɴᴄᴇʟ"
    )
    sent = bot.send_message(message.chat.id, "👇")
    bot.register_next_step_handler(sent, verify_channel)

def verify_channel(message):
    chat_id_user = message.chat.id
    if message.text == "/cancel":
        return bot.send_message(chat_id_user, "❌ Cᴀɴᴄᴇʟʟᴇᴅ.", reply_markup=main_menu(chat_id_user))

    target = None
    if message.forward_from_chat:
        target = message.forward_from_chat.id
    elif getattr(message, "forward_origin", None) and getattr(message.forward_origin, "chat", None):
        target = message.forward_origin.chat.id
    elif message.text:
        target = message.text.strip()
        if not target.startswith("@") and not target.lstrip("-").isdigit():
            target = "@" + target

    if target is None:
        return bot.send_message(chat_id_user, "❌ Pʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴀ ᴄʜᴀɴɴᴇʟ ᴍᴇssᴀɢᴇ ᴏʀ sᴇɴᴅ ɪᴛs @ᴜsᴇʀɴᴀᴍᴇ.")

    try:
        chat_info = bot.get_chat(target)
        member = bot.get_chat_member(chat_info.id, bot.get_me().id)
        if member.status in ['administrator', 'creator']:
            user_channels.setdefault(chat_id_user, [])
            if not any(c["id"] == chat_info.id for c in user_channels[chat_id_user]):
                user_channels[chat_id_user].append({"id": chat_info.id, "title": chat_info.title})
            send_card(
                chat_id_user,
                "✅", "📡",
                "Cʜᴀɴɴᴇʟ Cᴏɴɴᴇᴄᴛᴇᴅ",
                f"Cᴏɴɴᴇᴄᴛᴇᴅ: {chat_info.title}"
            )
        else:
            bot.send_message(chat_id_user, "❌ Tʜᴇ ʙᴏᴛ ɴᴇᴇᴅs ᴛᴏ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ.")
    except Exception as e:
        bot.send_message(chat_id_user, f"❌ Cʜᴀɴɴᴇʟ ɴᴏᴛ ғᴏᴜɴᴅ ᴏʀ ʙᴏᴛ ʜᴀs ɴᴏ ᴀᴄᴄᴇss.\n{e}")

# --- SEND TO CHANNEL ---
@bot.message_handler(func=lambda m: m.text == BTN_SEND)
def ask_post_id(message):
    if blocked(message):
        return
    if not user_channels.get(message.chat.id):
        return bot.send_message(
            message.chat.id,
            f"❌ Yᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴀɴʏ ᴄʜᴀɴɴᴇʟ ʏᴇᴛ. Usᴇ {BTN_CONNECT} ғɪʀsᴛ."
        )
    if not posts_db:
        return bot.send_message(
            message.chat.id,
            f"❌ Nᴏ sᴀᴠᴇᴅ ᴘᴏsᴛs ʏᴇᴛ. Usᴇ {BTN_MAKE_POST} ғɪʀsᴛ."
        )
    send_card(
        message.chat.id,
        "🆔", "📤",
        "Sᴇɴᴅ Tᴏ Cʜᴀɴɴᴇʟ",
        "Eɴᴛᴇʀ ᴛʜᴇ Pᴏsᴛ ID ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴇɴᴅ:"
    )
    sent = bot.send_message(message.chat.id, "👇")
    bot.register_next_step_handler(sent, select_channel)

def select_channel(message):
    post_id = message.text.strip().upper()
    if post_id not in posts_db or not user_channels.get(message.chat.id):
        bot.send_message(message.chat.id, "❌ Iɴᴠᴀʟɪᴅ ID ᴏʀ ɴᴏ ᴄʜᴀɴɴᴇʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ.")
        return
    markup = types.InlineKeyboardMarkup()
    for chan in user_channels[message.chat.id]:
        markup.add(types.InlineKeyboardButton(text=chan["title"], callback_data=f"send_{post_id}_{chan['id']}"))
    bot.send_message(message.chat.id, "Cʜᴏᴏsᴇ ᴀ ᴄʜᴀɴɴᴇʟ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def perform_send(call):
    _, pid, cid = call.data.split("_")
    data = posts_db.get(pid)
    if not data:
        return bot.answer_callback_query(call.id, "❌ Pᴏsᴛ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
    markup = build_colored_post_markup(data)
    try:
        if data.get("photo_id"):
            safe_send_photo(cid, data["photo_id"], data["content"], entities=data.get("entities", []), reply_markup=markup)
        elif data.get("video_id"):
            safe_send_video(cid, data["video_id"], data["content"], entities=data.get("entities", []), reply_markup=markup)
        elif data.get("document_id"):
            safe_send_document(cid, data["document_id"], data["content"], entities=data.get("entities", []), reply_markup=markup)
        else:
            safe_send_message(cid, data["content"], entities=data.get("entities", []), reply_markup=markup)
        bot.edit_message_text("✅ Sᴇɴᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Eʀʀᴏʀ: {e}", show_alert=True)

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    temp_data.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "❌ Cᴀɴᴄᴇʟʟᴇᴅ.", reply_markup=main_menu(message.chat.id))

print("✨ Pʀᴇᴍɪᴜᴍ Bᴏᴛ ɪs ᴀᴄᴛɪᴠᴇ...")
print("👑 Bot started successfully!")
bot.infinity_polling()