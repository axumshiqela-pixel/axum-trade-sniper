import os
import datetime
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import database as db

try:
    from tx_verify import verify_telebirr
    VERIFIER_READY = True
except ImportError:
    print("WARNING: tx-verify not installed. Using mock verification.")
    VERIFIER_READY = False

BOT_TOKEN = "9106860212:AAF2eR2ML1It8pIhYnU4jtcki86jR4-_k8U"
YOUR_TELEBIRR_NUMBER = "0964235209"
WEB_APP_URL = "https://axum-trade-sniper.onrender.com"
REQUIRED_AMOUNT = 200.0

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

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

    # 1. CHECK IF ALREADY USED
    if db.is_receipt_used(trx):
        await update.message.reply_text("❌ *Security Alert*\n\nThis Transaction ID has already been used to activate a subscription. You cannot reuse a receipt.")
        return

    msg = await update.message.reply_text("⏳ Verifying your Telebirr transaction... Please wait.")

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
                reason = "Transaction not found or receipt is invalid."
        except Exception as e:
            reason = f"Verification error: {str(e)}"
    else:
        await asyncio.sleep(2)
        is_valid = True # Mock mode for local testing

    if is_valid:
        # 2. SAVE TO DATABASE SO IT CAN'T BE USED AGAIN
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

def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trx))
    print("🤖 Bot is running with Replay Protection...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
