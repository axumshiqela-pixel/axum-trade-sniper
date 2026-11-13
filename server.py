import datetime
import csv
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

subscriptions_db = {
    7480888438: {
        "expiry": "2026-12-12",
        "tier": "PRO",
        "username": "@miki_trader",
        "selected_market": "GBP/USD"
    }
}

# Updated with your new BotFather API Token
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
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

@app.post("/verify-payment")
def verify_payment(data: PaymentVerification):
    trx = data.transaction_id.strip()
    if len(trx) < 6:
        raise HTTPException(status_code=400, detail="Invalid Transaction ID format.")
    
    today = datetime.date.today()
    expiry_date = today + datetime.timedelta(days=30)
    expiry_str = expiry_date.strftime("%Y-%m-%d")
    
    tier_name = "Premium Pro (20+ Markets)" if data.plan == "PRO" else "Monthly VIP (5 Core Markets)"
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
        f"Amount: `{price_paid}` via Telebirr\n"
        f"Transaction ID: `{trx}`\n"
        f"Access Valid Until: **{expiry_str}**"
    )
    send_telegram_msg(data.telegram_id, success_msg)
    
    return {"success": True, "message": f"{tier_name} activated until {expiry_str}!"}

@app.post("/update-market")
def update_market(data: MarketUpdate):
    if data.telegram_id in subscriptions_db:
        subscriptions_db[data.telegram_id]["selected_market"] = data.market
        return {"success": True, "market": data.market}
    raise HTTPException(status_code=404, detail="User not found.")

@app.get("/get-user-market/{telegram_id}")
def get_user_market(telegram_id: int):
    if telegram_id in subscriptions_db:
        return {"market": subscriptions_db[telegram_id].get("selected_market", "GBP/USD")}
    return {"market": "GBP/USD"}

@app.get("/get-signal-history")
def get_signal_history():
    history = []
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append(row)
    return {"history": history[::-1][:10]}

@app.get("/check-access/{telegram_id}")
def check_access(telegram_id: int):
    if telegram_id not in subscriptions_db:
        return {"access": False, "tier": None, "message": "No subscription found."}
    
    user_info = subscriptions_db[telegram_id]
    expiry_date = datetime.datetime.strptime(user_info["expiry"], "%Y-%m-%d").date()
    
    if datetime.date.today() > expiry_date:
        return {"access": False, "tier": user_info["tier"], "message": "Subscription expired."}
    
    return {"access": True, "tier": user_info["tier"], "message": f"Active {user_info['tier']} pass."}

app.mount("/", StaticFiles(directory=".", html=True), name="static")