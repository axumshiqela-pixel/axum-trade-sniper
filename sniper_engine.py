import time
import datetime
import csv
import os
import requests
import MetaTrader5 as mt5

RISK_REWARD_RATIO = 2.0

TELEGRAM_BOT_TOKEN = "9106860212:AAF2eR2ML1It8pIhYnU4jtcki86jR4-_k8U"
TELEGRAM_CHAT_ID = "7480888438"
TARGET_TELEGRAM_ID = 7480888438

JOURNAL_FILE = "trade_journal.csv"

# Tier Market Definitions
CORE_VIP_MARKETS = ["GBPUSD.e", "XAUUSD", "EURUSD.e", "NASDAQ", "AUDUSD.e"]
PRO_EXPANDED_MARKETS = [
    "GBPUSD.e", "XAUUSD", "EURUSD.e", "NASDAQ", "AUDUSD.e",
    "USDJPY.e", "US30", "GBPJPY.e", "EURJPY.e", "USDCAD.e",
    "NZDUSD.e", "USDCHF.e", "GER40", "UK100", "BRENT",
    "BTCUSD", "ETHUSD", "ADAUSD", "SOLUSD", "XRPUSD"
]

def init_journal():
    if not os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Symbol", "Action", "Entry Price", "Stop Loss", "Take Profit", "Status"])

def log_trade_to_csv(symbol, action, entry, sl, tp):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(JOURNAL_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, symbol, action, f"{entry:.5f}", f"{sl:.5f}", f"{tp:.5f}", "EXECUTED"])

def send_telegram_alert(message, chat_id=TELEGRAM_CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

def get_user_session_info():
    try:
        res = requests.get(f"http://127.0.0.1:8000/check-access/{TARGET_TELEGRAM_ID}", timeout=3)
        data = res.json()
        tier = data.get("tier", "VIP")
        
        res_market = requests.get(f"http://127.0.0.1:8000/get-user-market/{TARGET_TELEGRAM_ID}", timeout=3)
        market_data = res_market.json()
        market_ui = market_data.get("market", "GBP/USD")
        
        # Map UI name to MT5 symbol
        mapping = {
            "GBP/USD": "GBPUSD.e",
            "XAU/USD": "XAUUSD",
            "EUR/USD": "EURUSD.e",
            "NASDAQ": "NASDAQ",
            "AUD/USD": "AUDUSD.e"
        }
        symbol = mapping.get(market_ui, "GBPUSD.e")
        return tier, symbol
    except:
        return "VIP", "GBPUSD.e"

def initialize_mt5():
    if not mt5.initialize():
        print(f"[MT5 ERROR] Initialize failed: {mt5.last_error()}")
        return False
    print("[MT5 SUCCESS] Connected to MetaTrader 5 terminal.")
    return True

def analyze_market_live(symbol):
    rates_5m = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 20)
    rates_1h = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10)
    current_tick = mt5.symbol_info_tick(symbol)
    
    if rates_5m is None or len(rates_5m) < 20 or not current_tick:
        return None

    h1_closes = [bar['close'] for bar in rates_1h]
    macro_bullish = h1_closes[-1] > h1_closes[-4]

    c_curr = rates_5m[-1]
    
    is_bullish = macro_bullish and (c_curr['close'] > c_curr['open'])
    is_bearish = (not macro_bullish) and (c_curr['close'] < c_curr['open'])

    action = "BUY" if is_bullish else ("SELL" if is_bearish else "WAIT")
    
    sl_distance = 0.0020 if "USD" in symbol and "XAU" not in symbol and "US30" not in symbol and "NASDAQ" not in symbol else (2.0 if "XAU" in symbol else 50.0)
    tp_distance = sl_distance * RISK_REWARD_RATIO

    if action == "BUY":
        entry = current_tick.ask
        sl = entry - sl_distance
        tp = entry + tp_distance
    elif action == "SELL":
        entry = current_tick.bid
        sl = entry + sl_distance
        tp = entry - tp_distance
    else:
        entry = current_tick.bid
        sl = 0.0
        tp = 0.0

    return {
        "symbol": symbol,
        "price": f"{current_tick.bid:.5f}",
        "action": action,
        "entry": f"{entry:.5f}",
        "sl": f"{sl:.5f}",
        "tp": f"{tp:.5f}"
    }

def main_loop():
    print("========================================")
    print(" AXUM SNIPER: LIVE TIER & API SYNCED    ")
    print("========================================")
    
    init_journal()
    if not initialize_mt5():
        return
    
    send_telegram_alert("🤖 *Axum Trade Sniper Engine Activated!* Monitoring institutional liquidity and market structure in real-time.")

    last_signal_action = None

    while True:
        tier, active_symbol = get_user_session_info()
        
        # Enforce tier restrictions
        if tier == "VIP" and active_symbol not in CORE_VIP_MARKETS:
            active_symbol = "GBPUSD.e" # Default fallback for VIP if out of bounds
            
        analysis = analyze_market_live(active_symbol)
        
        if analysis:
            timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp_str}] Tier: {tier} | Market: {active_symbol} | Action: {analysis['action']}")
            
            if analysis["action"] in ["BUY", "SELL"] and analysis["action"] != last_signal_action:
                last_signal_action = analysis["action"]
                log_trade_to_csv(active_symbol, analysis["action"], float(analysis["entry"]), float(analysis["sl"]), float(analysis["tp"]))
                
                alert_msg = (
                    f"🔥 *AXUM INSTITUTIONAL SNIPER SIGNAL* 🔥\n\n"
                    f"🏷️ Tier Pass: *{tier} Tier*\n"
                    f"📅 Date/Time: `{timestamp_str}`\n"
                    f"📊 Asset: `{active_symbol}`\n"
                    f"⚡ Signal Action: *{analysis['action']}*\n\n"
                    f"📌 *Exact Price Levels:*\n"
                    f"• Entry Price: `{analysis['entry']}`\n"
                    f"• Stop Loss (SL): `{analysis['sl']}`\n"
                    f"• Take Profit (TP): `{analysis['tp']}` (1:2 RR)\n\n"
                    f"⚠️ _Execute with proper risk management according to V-Prop rules._"
                )
                send_telegram_alert(alert_msg, TARGET_TELEGRAM_ID)
                
        time.sleep(20)

if __name__ == "__main__":
    main_loop()
