import datetime
import csv
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# Database tracking user subscriptions, tiers, and selected markets
subscriptions_db = {
    7480888438: {
        "expiry": "2026-12-12",
        "tier": "VIP",
        "username": "@miki_trader",
        "selected_market": "GBP/USD"
    }
}

TELEGRAM_BOT_TOKEN = "9106860212:AAF2eR2ML1It8pIhYnU4jtcki86jR4-_k8U"
JOURNAL_FILE = "trade_journal.csv"

class PaymentVerification(BaseModel):
    telegram_id: int
    telegram_username: str
    transaction_id: str
    plan: str

class MarketUpdate(BaseModel):
    telegram_id: int
    market: str

def send_telegram_msg(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

@app.post("/verify-payment")
def verify_payment(data: PaymentVerification):
    trx = data.transaction_id.strip()
    if len(trx) < 6:
        raise HTTPException(status_code=400, detail="Invalid Transaction ID format.")
    
    today = datetime.date.today()
    expiry_date = today + datetime.timedelta(days=30)
    expiry_str = expiry_date.strftime("%Y-%m-%d")
    
    tier_name = "Premium Pro Pass (20+ Markets)" if data.plan == "PRO" else "VIP Monthly Pass (5 Core Markets)"
    price_paid = "1,499 ETB" if data.plan == "PRO" else "699 ETB"

    subscriptions_db[data.telegram_id] = {
        "expiry": expiry_str,
        "tier": data.plan,
        "username": data.telegram_username,
        "selected_market": "GBP/USD"
    }
    
    success_msg = (
        f"🎉 *Subscription Activated Successfully!*\n\n"
        f"User: `{data.telegram_username}`\n"
        f"Plan: *{tier_name}*\n"
        f"Amount Paid: `{price_paid}` via Telebirr\n"
        f"Transaction ID: `{trx}`\n"
        f"Access Valid Until: **{expiry_str}**\n\n"
        f"⚡ _Your terminal and automated Telegram signal dispatch are now fully unlocked!_"
    )
    send_telegram_msg(data.telegram_id, success_msg)
    
    return {"success": True, "message": f"{tier_name} activated until {expiry_str}!"}

@app.post("/update-market")
def update_market(data: MarketUpdate):
    if data.telegram_id in subscriptions_db:
        # Validate market access based on tier
        user_tier = subscriptions_db[data.telegram_id].get("tier", "VIP")
        core_markets = ["GBP/USD", "XAU/USD", "EUR/USD", "NASDAQ", "AUD/USD"]
        
        if user_tier == "VIP" and data.market not in core_markets:
            raise HTTPException(status_code=403, detail="Upgrade to Premium Pro to access 20+ markets.")
            
        subscriptions_db[data.telegram_id]["selected_market"] = data.market
        return {"success": True, "market": data.market}
    raise HTTPException(status_code=404, detail="User not found.")

@app.get("/get-user-market/{telegram_id}")
def get_user_market(telegram_id: int):
    if telegram_id in subscriptions_db:
        return {"market": subscriptions_db[telegram_id].get("selected_market", "GBP/USD")}
    return {"market": "GBP/USD"}

@app.get("/check-access/{telegram_id}")
def check_access(telegram_id: int):
    if telegram_id not in subscriptions_db:
        return {"access": False, "tier": None, "message": "No active subscription found."}
    
    user_info = subscriptions_db[telegram_id]
    expiry_date = datetime.datetime.strptime(user_info["expiry"], "%Y-%m-%d").date()
    
    if datetime.date.today() > expiry_date:
        return {"access": False, "tier": user_info["tier"], "message": "Subscription expired."}
    
    return {"access": True, "tier": user_info["tier"], "message": f"Active {user_info['tier']} pass."}

app.mount("/", StaticFiles(directory=".", html=True), name="static")
