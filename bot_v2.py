import ccxt
import pandas as pd
import numpy as np
import time
import smtplib
import os  # Secrets ke liye zaroori 🏛️
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. CONFIGURATION (Vault Integration) ---
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
APP_PASSWORD = os.getenv('APP_PASSWORD')

def format_price(price):
    if price < 1.0: return f"{price:.6f}"
    elif price < 10.0: return f"{price:.4f}"
    else: return f"{price:.2f}"

def send_ranked_report(signals):
    if not signals: return
    signals.sort(key=lambda x: x['score'], reverse=True)
    elite_4 = signals[:4]

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg['Subject'] = "🔱 ARATA SHIUNJI ELITE REPORT"

    body = " 🔱 ARATA SHIUNJI BATCH REPORT 🔱\n"
    body += "====================================\n\n"
    for rank, s in enumerate(elite_4, 1):
        dir_label = "🟢 LONG" if s['side'] == 'buy' else "🔴 SHORT"
        p_str, sl_str, tp_str = format_price(s['price']), format_price(s['sl']), format_price(s['tp'])
        body += f"🔱 RANK {rank}: {s['symbol']} ({dir_label})\n"
        body += f" 🔥 Score: {s['score']:.2f}% | 💰 Price: ${p_str}\n"
        body += f" 📉 SL: ${sl_str} | 📈 TP: ${tp_str}\n"
        body += "------------------------------------\n"
    body += "\n 📺 Monitor these on your TV screen dashboard. 📺"
    
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
        server.quit()
        print(f"✅ Report Sent! Top: {elite_4[0]['symbol']}")
    except Exception as e:
        print(f"❌ Error: {e}")

def get_market_analysis(exchange, symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['returns'] = np.log(df['c'] / df['c'].shift(1))
        vol = df['returns'].rolling(window=20).std().iloc[-1] * np.sqrt(24 * 365)
        current_price = df['c'].iloc[-1]
        ma_24 = df['c'].rolling(window=24).mean().iloc[-1]
        side = 'buy' if current_price > ma_24 else 'sell'
        return (vol if not np.isnan(vol) else 0.40), side
    except: return 0.40, 'buy'

# GitHub Actions ke liye loop ki zaroorat nahi hoti, ye ek baar run hoga
if __name__ == "__main__":
    exchange = ccxt.binance({'options': {'defaultType': 'delivery'}})
    tickers = exchange.fetch_tickers()
    valid = [t for t in tickers.values() if '/USD' in t['symbol'] and t['quoteVolume'] is not None]
    top_20 = sorted(valid, key=lambda x: x['quoteVolume'], reverse=True)[:20]
    
    all_signals = []
    for ticker in top_20:
        try:
            symbol, price = ticker['symbol'], ticker['last']
            vol, side = get_market_analysis(exchange, symbol)
            sl_dist, tp_dist = 0.015, 0.030
            if side == 'buy':
                sl, tp = price * (1 - sl_dist), price * (1 + tp_dist)
            else:
                sl, tp = price * (1 + sl_dist), price * (1 - sl_dist)
            all_signals.append({'symbol': symbol, 'price': price, 'score': vol*100, 'side': side, 'sl': sl, 'tp': tp})
        except: continue
    send_ranked_report(all_signals)
