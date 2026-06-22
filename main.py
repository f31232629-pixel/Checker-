import os
import json
import logging
import asyncio
import random
import string
import re
import requests
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ============== CONFIGURATION ==============
BOT_TOKEN = "8962210629:AAFhB5oNooreoJRhIuG7Frc9kqRxpQ2NWHA"
OWNER_ID = 8570832903

# API Configuration
API_URL = "https://nik.cards/shopify"
DEFAULT_PROXY = "ca-mon.pvdata.host:8080:g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2"
SITE = "https://aha-wrap.myshopify.com/"

# Pricing Plans
PLANS = {
    "basic": {"price": 250, "duration": "1d", "label": "Basic - 1 Day"},
    "monthly": {"price": 500, "duration": "30d", "label": "Monthly - 30 Days"},
    "yearly": {"price": 1000, "duration": "365d", "label": "Yearly - 365 Days"},
    "lifetime": {"price": 2500, "duration": "lifetime", "label": "Lifetime"}
}

# Free limits
FREE_SINGLE_LIMIT = 131
FREE_BULK_LIMIT = 1000

# ============== DATABASE CLASS (JSON-based) ==============
class Database:
    def __init__(self):
        self.db_file = "database.json"
        self.history_file = "history.json"
        self.reports_file = "reports.csv"
        self._initialize_files()
        self.data = self._load_data()
    
    def _initialize_files(self):
        """Create database files if they don't exist"""
        # Main database
        if not os.path.exists(self.db_file):
            initial_data = {
                "users": {},
                "redeem_codes": {},
                "stats": {
                    "total_checks": 0,
                    "total_users": 0,
                    "total_redeems": 0
                }
            }
            with open(self.db_file, 'w') as f:
                json.dump(initial_data, f, indent=4)
            print(f"✅ Created {self.db_file}")
        
        # History file
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump([], f, indent=4)
            print(f"✅ Created {self.history_file}")
        
        # Reports CSV file
        if not os.path.exists(self.reports_file):
            with open(self.reports_file, 'w') as f:
                f.write("Timestamp,User_ID,Username,Card,Status,Charge,Proxy,Type\n")
            print(f"✅ Created {self.reports_file}")
        
        # Create logs directory
        if not os.path.exists("logs"):
            os.makedirs("logs")
            print("✅ Created logs directory")
    
    def _load_data(self):
        """Load data from JSON file"""
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except:
            return {"users": {}, "redeem_codes": {}, "stats": {"total_checks": 0, "total_users": 0, "total_redeems": 0}}
    
    def _save_data(self):
        """Save data to JSON file"""
        with open(self.db_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def _save_history(self, entry):
        """Save history entry"""
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
        
        history.append(entry)
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=4)
    
    def _save_report(self, user_id, username, card, status, charge, proxy, check_type):
        """Save report to CSV"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.reports_file, 'a') as f:
            f.write(f"{timestamp},{user_id},{username},{card},{status},{charge},{proxy},{check_type}\n")
    
    # ===== User Methods =====
    def get_user(self, user_id):
        user_id = str(user_id)
        return self.data["users"].get(user_id)
    
    def create_user(self, user_id, username, first_name, last_name):
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "user_id": user_id,
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
        user_id = str(user_id)
        if user_id in self.data["users"]:
            expiry = None
            if duration != 'lifetime':
                days = int(duration.replace('d', ''))
                expiry = (datetime.now() + timedelta(days=days)).isoformat()
            else:
                expiry = 'lifetime'
            
            self.data["users"][user_id]["plan"] = plan
            self.data["users"][user_id]["expiry_date"] = expiry
            self._save_data()
    
    def add_credits(self, user_id, credits):
        user_id = str(user_id)
        if user_id in self.data["users"]:
            self.data["users"][user_id]["credits"] += credits
            self._save_data()
    
    def deduct_credits(self, user_id, amount):
        user_id = str(user_id)
        if user_id in self.data["users"]:
            self.data["users"][user_id]["credits"] -= amount
            self._save_data()
    
    def get_user_credits(self, user_id):
        user_id = str(user_id)
        user = self.get_user(user_id)
        return user["credits"] if user else 0
    
    def get_user_plan(self, user_id):
        user_id = str(user_id)
        user = self.get_user(user_id)
        if user:
            return (user["plan"], user["expiry_date"])
        return None
    
    def increment_checks(self, user_id):
        user_id = str(user_id)
        if user_id in self.data["users"]:
            self.data["users"][user_id]["total_checks"] += 1
            self.data["stats"]["total_checks"] += 1
            self._save_data()
    
    # ===== Proxy Methods =====
    def add_proxy(self, user_id, proxy_string):
        user_id = str(user_id)
        if user_id in self.data["users"]:
            if proxy_string not in self.data["users"][user_id]["proxies"]:
                self.data["users"][user_id]["proxies"].append(proxy_string)
                if not self.data["users"][user_id]["active_proxy"]:
                    self.data["users"][user_id]["active_proxy"] = proxy_string
                self._save_data()
                return True
        return False
    
    def remove_proxy(self, user_id, proxy_string):
        user_id = str(user_id)
        if user_id in self.data["users"]:
            if proxy_string in self.data["users"][user_id]["proxies"]:
                self.data["users"][user_id]["proxies"].remove(proxy_string)
                if self.data["users"][user_id]["active_proxy"] == proxy_string:
                    self.data["users"][user_id]["active_proxy"] = None
                    if self.data["users"][user_id]["proxies"]:
                        self.data["users"][user_id]["active_proxy"] = self.data["users"][user_id]["proxies"][0]
                self._save_data()
                return True
        return False
    
    def set_active_proxy(self, user_id, proxy_string):
        user_id = str(user_id)
        if user_id in self.data["users"]:
            if proxy_string in self.data["users"][user_id]["proxies"]:
                self.data["users"][user_id]["active_proxy"] = proxy_string
                self._save_data()
                return True
        return False
    
    def get_user_proxies(self, user_id):
        user_id = str(user_id)
        user = self.get_user(user_id)
        if user:
            return user.get("proxies", [])
        return []
    
    def get_active_proxy(self, user_id):
        user_id = str(user_id)
        user = self.get_user(user_id)
        if user:
            return user.get("active_proxy")
        return None
    
    # ===== Redeem Code Methods =====
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
        if code in self.data["redeem_codes"]:
            self.data["redeem_codes"][code]["used_by"] = str(user_id)
            self.data["redeem_codes"][code]["used_date"] = datetime.now().isoformat()
            self.data["redeem_codes"][code]["is_used"] = True
            self.data["stats"]["total_redeems"] += 1
            self._save_data()
            return True
        return False
    
    def get_redeem_code(self, code):
        return self.data["redeem_codes"].get(code)
    
    # ===== History Methods =====
    def add_check_history(self, user_id, card_number, status, charge_amount, proxy, is_bulk=0):
        entry = {
            "user_id": str(user_id),
            "card_number": card_number,
            "status": status,
            "charge_amount": charge_amount,
            "proxy": proxy,
            "checked_date": datetime.now().isoformat(),
            "is_bulk": is_bulk
        }
        self._save_history(entry)
        self.increment_checks(user_id)
        
        user = self.get_user(user_id)
        username = user["username"] if user else "Unknown"
        check_type = "Bulk" if is_bulk else "Single"
        self._save_report(user_id, username, card_number, status, charge_amount, proxy, check_type)
    
    def get_check_count(self, user_id, is_bulk=0):
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            return 0
        
        count = 0
        today = datetime.now().date()
        for entry in history:
            if entry["user_id"] == str(user_id) and entry["is_bulk"] == is_bulk:
                entry_date = datetime.fromisoformat(entry["checked_date"]).date()
                if entry_date == today:
                    count += 1
        return count
    
    def get_user_stats(self, user_id):
        user_id = str(user_id)
        user = self.get_user(user_id)
        if not user:
            return None
        
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
        
        total_checks = 0
        live_count = 0
        dead_count = 0
        unknown_count = 0
        charge_count = 0
        
        for entry in history:
            if entry["user_id"] == user_id:
                total_checks += 1
                status = entry["status"]
                if status == "Live":
                    live_count += 1
                elif status == "Charge":
                    charge_count += 1
                elif status == "Dead":
                    dead_count += 1
                else:
                    unknown_count += 1
        
        return {
            "total_checks": total_checks,
            "live": live_count,
            "dead": dead_count,
            "unknown": unknown_count,
            "charge": charge_count
        }

# ============== CARD CHECKER CLASS ==============
class CardChecker:
    def __init__(self):
        self.api_url = API_URL
        self.site = SITE
    
    def check_card(self, card_number, proxy_string=None):
        try:
            proxy_to_use = proxy_string if proxy_string else DEFAULT_PROXY
            
            proxy_parts = proxy_to_use.split(':')
            if len(proxy_parts) == 4:
                proxy_host, proxy_port, proxy_user, proxy_pass = proxy_parts
                proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
                proxies = {"http": proxy_url, "https": proxy_url}
            else:
                proxies = None
            
            params = {
                'site': self.site,
                'cc': card_number,
                'proxy': proxy_to_use
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            response = requests.get(
                self.api_url,
                params=params,
                proxies=proxies,
                headers=headers,
                timeout=30
            )
            
            data = response.json()
            
            if 'status' in data:
                status = data['status'].lower()
                charge = data.get('charge', '0.00')
                
                if 'shopify' in data.get('gateway', '').lower() or 'shopify' in self.site.lower():
                    if status == 'success' or status == 'live':
                        return ('Live', charge, data, proxy_to_use)
                    elif status == 'charge' or status == 'charged':
                        return ('Charge', charge, data, proxy_to_use)
                    elif status == 'failed' or status == 'dead' or status == 'error':
                        return ('Dead', '0.00', data, proxy_to_use)
                    elif status == 'pending' or status == 'unknown':
                        return ('Unknown', '0.00', data, proxy_to_use)
                    else:
                        if 'invalid' in str(data).lower() or 'declined' in str(data).lower():
                            return ('Dead', '0.00', data, proxy_to_use)
                        elif 'success' in str(data).lower() or 'approved' in str(data).lower():
                            return ('Live', charge, data, proxy_to_use)
                        else:
                            return ('Unknown', '0.00', data, proxy_to_use)
                else:
                    if status == 'live' or status == 'success':
                        return ('Live', charge, data, proxy_to_use)
                    elif status == 'charge' or status == 'charged':
                        return ('Charge', charge, data, proxy_to_use)
                    elif status == 'dead' or status == 'failed' or status == 'error':
                        return ('Dead', '0.00', data, proxy_to_use)
                    else:
                        return ('Unknown', '0.00', data, proxy_to_use)
            else:
                if 'shopify' in str(data).lower() or 'payment' in str(data).lower():
                    if 'status' in str(data).lower():
                        if 'success' in str(data).lower() or 'approved' in str(data).lower():
                            return ('Live', '0.00', data, proxy_to_use)
                        elif 'declined' in str(data).lower() or 'failed' in str(data).lower():
                            return ('Dead', '0.00', data, proxy_to_use)
                        else:
                            return ('Unknown', '0.00', data, proxy_to_use)
                    else:
                        return ('Unknown', '0.00', data, proxy_to_use)
                else:
                    return ('Unknown', '0.00', data, proxy_to_use)
                
        except requests.exceptions.Timeout:
            return ('Unknown', '0.00', {'error': 'Timeout - Gateway may be down'}, proxy_to_use)
        except requests.exceptions.RequestException as e:
            return ('Unknown', '0.00', {'error': f'Request failed: {str(e)}'}, proxy_to_use)
        except json.JSONDecodeError:
            try:
                response_text = response.text.lower()
                if 'success' in response_text or 'approved' in response_text:
                    return ('Live', '0.00', {'response': response_text}, proxy_to_use)
                elif 'declined' in response_text or 'failed' in response_text:
                    return ('Dead', '0.00', {'response': response_text}, proxy_to_use)
                else:
                    return ('Unknown', '0.00', {'response': response_text}, proxy_to_use)
            except:
                return ('Unknown', '0.00', {'error': 'Invalid response format'}, proxy_to_use)
        except Exception as e:
            return ('Unknown', '0.00', {'error': str(e)}, proxy_to_use)
    
    def check_bulk(self, card_numbers, proxy_string=None):
        results = []
        for card in card_numbers:
            status, charge, data, proxy = self.check_card(card, proxy_string)
            results.append({
                'card': card,
                'status': status,
                'charge': charge,
                'data': data,
                'proxy': proxy
            })
            time.sleep(0.5)
        return results

# ============== REDEEM CODE MANAGER ==============
class RedeemCodeManager:
    @staticmethod
    def generate_code(length=12):
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=length))
    
    @staticmethod
    def parse_duration(duration_str):
        if duration_str.endswith('m'):
            months = int(duration_str[:-1])
            return months * 30
        elif duration_str.endswith('y'):
            years = int(duration_str[:-1])
            return years * 365
        else:
            return int(duration_str)

# ============== UTILITY FUNCTIONS ==============
def validate_card(card_number):
    card_number = re.sub(r'\s+', '', card_number)
    if not card_number.isdigit():
        return False
    
    if len(card_number) < 13 or len(card_number) > 19:
        return False
    
    total = 0
    reverse_digits = card_number[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    
    return total % 10 == 0

def format_card_for_display(card):
    if len(card) >= 16:
        return f"{card[:4]}****{card[-4:]}"
    return card

def parse_file_content(content):
    lines = content.split('\n')
    cards = []
    for line in lines:
        line = line.strip()
        if line and validate_card(line):
            cards.append(line)
    return cards

def validate_proxy(proxy_string):
    parts = proxy_string.split(':')
    if len(parts) == 4:
        host, port, username, password = parts
        if host and port.isdigit() and username and password:
            return True
    return False

# ============== TELEGRAM BOT HANDLERS ==============
db = Database()
card_checker = CardChecker()
redeem_manager = RedeemCodeManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.create_user(
        user.id,
        user.username or "Unknown",
        user.first_name or "Unknown",
        user.last_name or ""
    )
    
    welcome_text = f"""
🎯 *Welcome to Shopify Card Checker Bot* 🎯

Hey {user.first_name}! 👋

This bot validates credit/debit cards through Shopify payment gateway:
✅ Live cards (valid and working)
✅ Dead cards (invalid/declined)
✅ Unknown status
✅ Charge amount detection

💳 *Commands:*
• `/sh` - Check single card
• `/msh` - Check multiple cards (free: {FREE_SINGLE_LIMIT} cards)
• `/chk` - Check cards from .txt file
• `/proxy` - Manage your proxies
• `/redeem` - Redeem code for premium
• `/plan` - Check your plan & credits
• `/stats` - Your check statistics
• `/buy` - Premium plan details
• `/help` - Help & support

🛒 *Shopify Gateway:* {SITE}
🌐 *Default Proxy:* {DEFAULT_PROXY[:30]}...

📌 *Free users:* {FREE_SINGLE_LIMIT} single checks per day

🔒 *Premium Features:*
• Unlimited checks
• Bulk file processing
• Priority support

Developed by: @theaadikoder
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""
📚 *Help & Commands Guide*

🛒 *Shopify Gateway:* {SITE}

🔹 `/sh 4111111111111111` - Check single card
🔹 `/msh 4111111111111111|4111111111111112` - Check multiple cards (separate with |)
🔹 `/chk` - Reply to a .txt file to check cards in bulk
🔹 `/proxy` - Manage your proxies
🔹 `/redeem <code>` - Redeem your premium code
🔹 `/plan` - Check your current plan and credits
🔹 `/stats` - View your check statistics
🔹 `/buy` - View premium plan details
🔹 `/get_red <credits> <duration>` - Owner only: Generate redeem code

*Proxy Management:*
• `/proxy add host:port:user:pass` - Add a new proxy
• `/proxy list` - View all your proxies
• `/proxy set host:port:user:pass` - Set active proxy
• `/proxy remove host:port:user:pass` - Remove a proxy
• `/proxy active` - Show current active proxy

*How to use:*
1. For single card: `/sh 4111111111111111`
2. For multiple: `/msh 4111111111111111|4111111111111112|4111111111111113`
3. For file: Send a .txt file with card numbers (one per line)

*Card Status Meanings:*
✅ Live - Card is valid and working
💰 Charge - Card has money, amount shown
❌ Dead - Card is invalid or declined
❓ Unknown - Status could not be determined

*Owner Commands:*
• `/get_red 300 1m` - Generate 1 month premium code with 300 credits
• `/get_red 1000 1y` - Generate 1 year premium code with 1000 credits
• `/stats all` - View bot statistics (owner only)

Contact: @theaadikoder
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def single_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text("❌ Please provide a card number.\nExample: `/sh 4111111111111111`", parse_mode='Markdown')
        return
    
    card = args[0].strip()
    
    if not validate_card(card):
        await update.message.reply_text("❌ Invalid card number. Please check and try again.")
        return
    
    user_plan = db.get_user_plan(user_id)
    credits = db.get_user_credits(user_id)
    
    is_premium = user_plan and user_plan[0] != 'free'
    if not is_premium and credits <= 0:
        await update.message.reply_text(
            "❌ You have no credits left!\n"
            "Use `/buy` to get premium or contact @theaadikoder"
        )
        return
    
    active_proxy = db.get_active_proxy(user_id)
    if not active_proxy:
        active_proxy = DEFAULT_PROXY
    
    if not is_premium:
        db.deduct_credits(user_id, 1)
    
    status_text = await update.message.reply_text(f"🔄 Checking card through Shopify gateway using proxy: `{active_proxy[:30]}...`", parse_mode='Markdown')
    
    status, charge, data, used_proxy = card_checker.check_card(card, active_proxy)
    
    db.add_check_history(user_id, card, status, charge, used_proxy, is_bulk=0)
    
    formatted_card = format_card_for_display(card)
    
    status_emoji = {
        'Live': '✅',
        'Charge': '💰',
        'Dead': '❌',
        'Unknown': '❓'
    }.get(status, '❓')
    
    response = f"""
💳 *Shopify Card Validation Result*

🛒 Gateway: `{SITE}`
🌐 Proxy Used: `{used_proxy[:30]}...`
📇 Card: `{formatted_card}`
{status_emoji} Status: *{status}*

"""

    if status == 'Live':
        response += "✅ Card is VALID and working on Shopify\n"
    elif status == 'Charge':
        response += f"💰 Card has funds! Amount: *${charge}*\n"
    elif status == 'Dead':
        response += "❌ Card is INVALID or declined by Shopify\n"
    else:
        response += "❓ Status could not be determined\n"
    
    response += f"""
📝 Details:
```json
{json.dumps(data, indent=2)}
