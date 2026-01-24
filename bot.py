import os
import time
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

PUSHOVER_USER_KEY = "ugurfo1drgkckg3i8i9x8cmon5qm85"
PUSHOVER_API_TOKEN = "aa9hxotiko33nd33zvih8pxsw2cx6a"

TAKE_PROFIT = 0.003
STOP_LOSS = 0.005
TRAILING_STOP = 0.002
BREAKEVEN_TRIGGER = 0.0015
MAX_RISK_PER_TRADE = 0.05
MAX_DAILY_LOSS = 0.02
MAX_TRADES_PER_DAY = 10
SCAN_INTERVAL = 30
MIN_SIGNAL_STRENGTH = 10

CRYPTO_UNIVERSE = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "LINK/USD", "UNI/USD"]

import alpaca_trade_api as tradeapi
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

state = {
    'daily_trades': 0,
    'daily_pnl': 0.0,
    'last_date': None,
    'peak_pnl': 0.0,
    'breakeven_active': False,
    'wins': 0,
    'losses': 0,
    'circuit_breaker': False
}

def send_notification(title, message, priority=0):
    try:
        requests.post("https://api.pushover.net/1/messages.json", data={
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "title": title,
            "message": message,
            "priority": priority,
            "sound": "cashregister"
        })
        print(f"📱 Notification: {title}")
    except:
        pass

def get_balance():
    try:
        return float(api.get_account().equity)
    except:
        return 0

def get_positions():
    try:
        return api.list_positions()
    except:
        return []

def get_crypto_movers(balance):
    movers = []
    for symbol in CRYPTO_UNIVERSE:
        try:
            bars = api.get_crypto_bars(symbol, '5Min', limit=3).df
            if len(bars) >= 2:
                price = float(bars['close'].iloc[-1])
                prev = float(bars['close'].iloc[-2])
                change = ((price - prev) / prev) * 100
                shares = round((balance * MAX_RISK_PER_TRADE) / price, 6)
                movers.append({'symbol': symbol, 'price': price, 'change': change, 'shares': shares})
        except:
            continue
    movers.sort(key=lambda x: x['change'], reverse=True)
    return movers

def get_crypto_signal(symbol):
    try:
        bars = api.get_crypto_bars(symbol, '5Min', limit=6).df
        if len(bars) < 2:
            return "WAIT", 0, "No data"
        prices = bars['close'].values
        m5 = ((prices[-1] - prices[-2]) / prices[-2]) * 100
        m15 = ((prices[-1] - prices[-4]) / prices[-4]) * 100 if len(prices) >= 4 else m5
        if m5 > 0.01:
            strength = min(abs(m5) * 100, 100)
            if m15 > 0:
                strength = min(strength + 20, 100)
            return "BUY", strength, f"+{m5:.3f}%"
        elif m5 < -0.02:
            return "WAIT", 0, f"{m5:.3f}%"
        return "WAIT", 0, "Flat"
    except:
        return "WAIT", 0, "Error"

def buy(symbol, shares, price):
    try:
        api.submit_order(symbol=symbol, qty=shares, side='buy', type='market', time_in_force='gtc')
        state['daily_trades'] += 1
        state['peak_pnl'] = 0.0
        state['breakeven_active'] = False
        send_notification("🤖 AUTO BUY", f"{symbol} @ ${price:,.2f}")
        print(f"✅ BOUGHT {symbol}")
        return True
    except Exception as e:
        print(f"❌ Buy failed: {e}")
        return False

def sell(position, reason):
    try:
        pnl = float(position.unrealized_plpc) * 100
        api.close_position(position.symbol)
        state['daily_trades'] += 1
        if pnl >= 0:
            state['wins'] += 1
            send_notification(f"💰 {reason}", f"{position.symbol} +{pnl:.2f}%")
        else:
            state['losses'] += 1
            send_notification(f"🛡️ {reason}", f"{position.symbol} {pnl:.2f}%")
        state['peak_pnl'] = 0.0
        state['breakeven_active'] = False
        print(f"✅ SOLD - {reason}")
        return True
    except Exception as e:
        print(f"❌ Sell failed: {e}")
        return False

def run():
    print("=" * 40)
    print("🌱 PROJECT HOPE BOT")
    print("🔥 AGGRESSIVE: 10% signal, 30s scans")
    print("=" * 40)
    send_notification("🚀 BOT STARTED", "Aggressive mode active")
    
    while True:
        try:
            tz = pytz.timezone('US/Eastern')
            today = str(datetime.now(tz).date())
            
            if state['last_date'] != today:
                state.update({'daily_trades': 0, 'daily_pnl': 0.0, 'last_date': today, 'circuit_breaker': False, 'wins': 0, 'losses': 0})
                print(f"📅 New day: {today}")
            
            if state['circuit_breaker']:
                time.sleep(SCAN_INTERVAL)
                continue
            
            balance = get_balance()
            if balance < 25:
                time.sleep(SCAN_INTERVAL)
                continue
            
            if state['daily_pnl'] <= -(balance * MAX_DAILY_LOSS):
                state['circuit_breaker'] = True
                send_notification("🚨 CIRCUIT BREAKER", "Daily limit hit")
                continue
            
            positions = get_positions()
            
            if positions:
                p = positions[0]
                pnl = float(p.unrealized_plpc)
                state['daily_pnl'] = float(p.unrealized_pl)
                
                print(f"📊 {p.symbol}: {pnl*100:.2f}%")
                
                if pnl > state['peak_pnl']:
                    state['peak_pnl'] = pnl
                
                if pnl >= BREAKEVEN_TRIGGER and not state['breakeven_active']:
                    state['breakeven_active'] = True
                    send_notification("🛡️ BREAKEVEN", f"{p.symbol} protected")
                
                if state['peak_pnl'] >= BREAKEVEN_TRIGGER and pnl <= (state['peak_pnl'] - TRAILING_STOP) and pnl > 0:
                    sell(p, "TRAILING STOP")
                    continue
                
                if pnl >= TAKE_PROFIT:
                    sell(p, "TAKE PROFIT")
                    continue
                
                stop = 0 if state['breakeven_active'] else -STOP_LOSS
                if pnl <= stop and pnl < 0:
                    sell(p, "STOP LOSS")
                    continue
            else:
                if state['daily_trades'] >= MAX_TRADES_PER_DAY:
                    time.sleep(SCAN_INTERVAL)
                    continue
                
                print(f"🔍 Scanning...")
                movers = get_crypto_movers(balance)
                
                bought = False
                for m in movers:
                    if m['change'] > 0:
                        sig, str_, reason = get_crypto_signal(m['symbol'])
                        print(f"   {m['symbol']}: {sig} ({str_:.0f}%)")
                        if sig == "BUY" and str_ >= MIN_SIGNAL_STRENGTH:
                            buy(m['symbol'], m['shares'], m['price'])
                            bought = True
                            break
                
                if not bought:
                    print("   ⏳ Waiting...")
            
            print(f"💰 ${balance:.2f} | P&L: ${state['daily_pnl']:.2f} | {state['daily_trades']}/{MAX_TRADES_PER_DAY} | W{state['wins']}/L{state['losses']}")
            print("-" * 40)
            time.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            print(f"❌ {e}")
            time.sleep(10)

if __name__ == "__main__":
    run()
