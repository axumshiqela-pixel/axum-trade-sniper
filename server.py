import datetime
import os
import requests
import asyncio
import logging
import threading
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from data_feed import get_price, get_candles
import database as db

try:
    from tx_verify import verify_telebirr
    VERIFIER_READY = True
except ImportError:
    print("WARNING: tx-verify not installed. Using mock verification.")
    VERIFIER_READY = False

app = FastAPI()

BOT_TOKEN = "9106860212:AAF2eR2ML1It8pIhYnU4jtcki86jR4-_k8U"
YOUR_TELEBIRR_NUMBER = "0964235209"
WEB_APP_URL = "https://axum-trade-sniper.onrender.com"
REQUIRED_AMOUNT = 200.0

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- TELEGRAM BOT LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_user(user.id)
    if db_user:
        expiry = datetime.datetime.strptime(db_user["expiry"], "%Y-%m-%d").date()
        if datetime.date.today() <= expiry:
            await update.message.reply_text(
                f"Welcome back, {user.first_name}!\n\nYour VIP pass is active until {db_user['expiry']}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Open Dashboard", web_app={"url": WEB_APP_URL})]])
            )
            return

    text = (
        f"Welcome to AXUM TRADE, {user.first_name}! 🚀\n\n"
        f"To activate your 30-day VIP pass, please send exactly *{int(REQUIRED_AMOUNT)} ETB* via Telebirr to:\n"
        f"📱 *{YOUR_TELEBIRR_NUMBER}*\n\n"
        f"After paying, copy the *Transaction ID (TRX)* from your Telebirr SMS and paste it here."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx = update.message.text.strip()
    user = update.effective_user
    if len(trx) < 6:
        await update.message.reply_text("⚠️ Invalid TRX format.")
        return
    if db.is_receipt_used(trx):
        await update.message.reply_text("❌ *Security Alert*\n\nThis Transaction ID has already been used.")
        return

    msg = await update.message.reply_text("⏳ Verifying your Telebirr transaction...")
    is_valid = False
    reason = "Verification failed."

    if VERIFIER_READY:
        try:
            result = await asyncio.to_thread(verify_telebirr, trx)
            if result and result.get("success"):
                paid_amount = float(result.get("amount", 0))
                if paid_amount >= REQUIRED_AMOUNT:
                    is_valid = True
                else:
                    reason = f"Paid amount ({paid_amount} ETB) is less than required ({REQUIRED_AMOUNT} ETB)."
            else:
                reason = "Transaction not found."
        except Exception as e:
            reason = f"Verification error: {str(e)}"
    else:
        await asyncio.sleep(1)
        is_valid = True # Mock mode for testing

    if is_valid:
        db.save_used_receipt(trx, user.id)
        expiry_str = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        username = f"@{user.username}" if user.username else user.first_name
        db.add_user(user.id, username, expiry_str, "VIP")
        await msg.edit_text(
            f"🎉 *Payment Verified!*\n\nYour VIP pass is active until *{expiry_str}*.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Open Dashboard", web_app={"url": WEB_APP_URL})]])
        )
    else:
        await msg.edit_text(f"❌ *Verification Failed*\n\n{reason}")

# --- FASTAPI SERVER LOGIC ---
@app.on_event("startup")
async def startup_event():
    db.init_db()
    def run_bot():
        bot_app = Application.builder().token(BOT_TOKEN).build()
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trx))
        bot_app.run_polling(allowed_updates=Update.ALL_TYPES)
    
    threading.Thread(target=run_bot, daemon=True).start()
    print("🤖 Telegram Bot is running in background thread!")

@app.get("/check-access/{telegram_id}")
def check_access(telegram_id: int):
    user = db.get_user(telegram_id)
    if not user: return {"access": False}
    expiry = datetime.datetime.strptime(user["expiry"], "%Y-%m-%d").date()
    if datetime.date.today() > expiry:
        return {"access": False}
    return {"access": True, "tier": user["tier"]}

@app.get("/live-price/{pair}")
def live_price(pair: str):
    price = get_price(pair.replace("-", "/"))
    if price is None: raise HTTPException(status_code=503, detail="Unavailable")
    return {"pair": pair, "price": price}

@app.get("/latest-signal/{pair}")
def latest_signal(pair: str):
    pair = pair.replace("-", "/")
    history = db.get_recent_signals(50)
    for sig in history:
        if sig["Symbol"] == pair:
            return sig
    return {"Action": "WAIT", "Entry Price": "0", "Take Profit": "0", "Stop Loss": "0", "RSI": "50", "Confidence": "50%", "Reasoning": "Scanning... no recent signal."}

@app.get("/get-signal-history")
def get_signal_history():
    return {"history": db.get_recent_signals(10)}

app.mount("/", StaticFiles(directory=".", html=True), name="static")
