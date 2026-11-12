import time
import datetime
import csv
import os
import requests
import MetaTrader5 as mt5

RISK_REWARD_RATIO = 2.0

# Updated with your new BotFather API Token
TELEGRAM_BOT_TOKEN = "9106860212:AAF2eR2ML1It8pIhYnU4jtcki86jR4-_k8U"
TELEGRAM_CHAT_ID = "7480888438"
TARGET_TELEGRAM_ID = 7480888438

JOURNAL_FILE = "trade_journal.csv"

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

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

def get_user_selected_market() -> str:
    try:
        res = requests.get(f"http://127.0.0.1:8000/get-user-market/{TARGET_TELEGRAM_ID}", timeout=3)
        data = res.json()
        market_ui = data.get("market", "GBP/USD")
        if market_ui == "GBP/USD": return "GBPUSD.e"
        if market_ui == "XAU/USD": return "XAUUSD"
        if market_ui == "EUR/USD": return "EURUSD.e"
        if market_ui == "NASDAQ": return "NASDAQ"
        if market_ui == "AUD/USD": return "AUDUSD.e"
        return "GBPUSD.e"
    except:
        return "GBPUSD.e"

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

    c_prev = rates_5m[-2]
    c_curr = rates_5m[-1]
    
    is_bullish = macro_bullish and (c_curr['close'] > c_curr['open'])
    is_bearish = (not macro_bullish) and (c_curr['close'] < c_curr['open'])

    action = "BUY" if is_bullish else ("SELL" if is_bearish else "WAIT")
    
    sl_distance = 0.0020 if "USD" in symbol and "XAU" not in symbol else (2.0 if "XAU" in symbol else 50.0)
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
    print(" AXUM SNIPER: NEW BOT TOKEN SYNCED      ")
    print("========================================")
    
    init_journal()
    if not initialize_mt5():
        return
    
    send_telegram_alert("🤖 *Axum Trade Sniper Initialized with New Bot!* Scanning your selected market in real-time.")

    last_signal_action = None

    while True:
        active_symbol = get_user_selected_market()
        analysis = analyze_market_live(active_symbol)
        
        if analysis:
            timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp_str}] Market: {active_symbol} | Action: {analysis['action']}")
            
            if analysis["action"] in ["BUY", "SELL"] and analysis["action"] != last_signal_action:
                last_signal_action = analysis["action"]
                log_trade_to_csv(active_symbol, analysis["action"], float(analysis["entry"]), float(analysis["sl"]), float(analysis["tp"]))
                
                alert_msg = (
                    f"🔥 *HIGH-PROBABILITY {analysis['action']} SIGNAL* 🔥\n\n"
                    f"📅 Date/Time: `{timestamp_str}`\n"
                    f"Symbol: `{active_symbol}`\n"
                    f"Action: *{analysis['action']}*\n"
                    f"Entry Price: `{analysis['entry']}`\n"
                    f"Stop Loss: `{analysis['sl']}`\n"
                    f"Take Profit: `{analysis['tp']}` (1:2 RR)\n\n"
                    f"⚠️ *Risk Warning:* Manage your lot size and risk according to your personal account balance or prop firm rules.\n\n"
                    f"⚡ _Execute immediately on V Prop!_"
                )
                send_telegram_alert(alert_msg)
                
        time.sleep(20)

if __name__ == "__main__":
    main_loop()