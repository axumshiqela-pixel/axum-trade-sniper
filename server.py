from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import csv
from datetime import datetime

# Import your custom sniper engine if available
try:
    import sniper_engine
except ImportError:
    sniper_engine = None

app = FastAPI(title="Axum Trade Sniper SaaS")

class PaymentRequest(BaseModel):
    phone: str
    amount: float

@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h2>Axum Trade Sniper Backend is Live!</h2>"

@app.post("/api/pay/telebirr")
def process_telebirr_payment(payload: PaymentRequest):
    # Log the payment attempt and user phone number
    print(f"Received Telebirr payment request: Phone={payload.phone}, Amount={payload.amount} ETB")
    
    # Optional: Save transaction record to CSV or database here
    journal_file = "trade_journal.csv"
    file_exists = os.path.exists(journal_file)
    
    try:
        with open(journal_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Type", "Phone", "Amount", "Status"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Telebirr Subscription", payload.phone, payload.amount, "Initiated"])
    except Exception as e:
        print(f"Error logging transaction: {e}")

    return {
        "status": "success",
        "message": f"Telebirr payment request initiated successfully for {payload.phone}",
        "amount": payload.amount
    }

@app.get("/api/signals")
def get_signals():
    # If sniper_engine exists, pull live data from it
    if sniper_engine and hasattr(sniper_engine, "get_latest_signals"):
        return sniper_engine.get_latest_signals()
    
    return {
        "pair": "XAU/USD",
        "signal": "Bullish Order Block Retest & Liquidity Sweep",
        "entry": "2650.00",
        "status": "Active",
        "engine": "Axum Sniper v1.0"
    }