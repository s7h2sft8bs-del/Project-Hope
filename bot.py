"""
PROJECT HOPE - 24/7 CRYPTO TRADING BOT
Runs in background, no browser needed
Sends notifications to iPhone/Apple Watch
"""

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

nano bot.py
```

**Step 3:** Find these lines near the top (around line 14-15):
```
PUSHOVER_USER_KEY = "a81i8ufm2sepdytc7o7riieagxyzag"
PUSHOVER_API_TOKEN = "ugurfo1drgkckg3i8i9x8cmon5qm85"
```

**Change them to:**
```
PUSHOVER_USER_KEY = "ugurfo1drgkckg3i8i9x8cmon5qm85"
PUSHOVER_API_TOKEN = "aa9hxotiko33nd33zvih8pxsw2cx6a"

TAKE_PROFIT = 0.003
STOP_LOSS = 0.005
TRAILING_STOP = 0.002
BREAKEVEN_TRIGGER = 0.0015
MAX_RISK_PER_TRADE = 0.05
MAX_DAILY_LOSS = 0.02
MAX_TRADES_PER_DAY = 10
SCAN_INTERVAL = 60
MIN_SIGNAL_STRENGTH = 50

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
            "title": f"🌱 {title}",
            "message": message,
            "priority": priority,
            "sound": "cashregister"
        })
        print(f"📱 Notification sent: {title}")
    except Exception as e:
        print(f"❌ Notification failed: {e}")

def get_balance():
    try:
        account = api.get_account()
        return float(account.equity)
    except Exception as e:
        print(f"❌ Error getting balance: {e}")
        return 0

def get_positions():
    try:
        return api.list_positions()
    except:
        return []

def get_crypto_movers(balance):
    movers = []
    try:
        for symbol in CRYPTO_UNIVERSE:
            try:
                bars = api.get_crypto_bars(symbol, '5Min', limit=3).df
                if len(bars) >= 2:
                    price = float(bars['close'].iloc[-1])
                    price_5min_ago = float(bars['close'].iloc[-2])
                    momentum_5m = ((price - price_5min_ago) / price_5min_ago) * 100
                    shares = round((balance * MAX_RISK_PER_TRADE) / price, 6)
                    movers.append({
                        'symbol': symbol,
                        'price': price,
                        'change': momentum_5m,
                        'shares': shares
                    })
            except:
                continue
        movers.sort(key=lambda x: x['change'], reverse=True)
        return movers
    except:
        return []

def get_crypto_signal(symbol):
    try:
        bars = api.get_crypto_bars(symbol, '5Min', limit=6).df
        if len(bars) < 3:
            return "WAIT", 0, "Not enough data"
        prices = bars['close'].values
        current_price = prices[-1]
        price_5min_ago = prices[-2] if len(prices) >= 2 else current_price
        price_15min_ago = prices[-4] if len(prices) >= 4 else current_price
        ema_2 = prices[-2:].mean()
        ema_4 = prices[-4:].mean() if len(prices) >= 4 else ema_2
        momentum_5m = ((current_price - price_5min_ago) / price_5min_ago) * 100
        momentum_15m = ((current_price - price_15min_ago) / price_15min_ago) * 100
        if current_price > ema_2 > ema_4 and momentum_5m > 0.03 and momentum_15m > 0:
            strength = min(abs(momentum_15m) * 25, 100)
            return "BUY", strength, f"+{momentum_5m:.2f}% (5m)"
        elif momentum_5m < -0.05:
            return "WAIT", 0, f"{momentum_5m:.2f}% dropping"
        else:
            return "WAIT", 0, "Waiting for momentum"
    except Exception as e:
        return "WAIT", 0, f"Error: {e}"

def buy_crypto(symbol, shares, price):
    try:
        api.submit_order(symbol=symbol, qty=shares, side='buy', type='market', time_in_force='gtc')
        state['daily_trades'] += 1
        state['peak_pnl'] = 0.0
        state['breakeven_active'] = False
        send_notification("🤖 AUTO BUY", f"{symbol} @ ${price:,.2f}\nShares: {shares}", 1)
        print(f"✅ BOUGHT {symbol} @ ${price:,.2f}")
        return True
    except Exception as e:
        print(f"❌ Buy failed: {e}")
        return False

def sell_position(position, reason):
    try:
        symbol = position.symbol
        pnl_pct = float(position.unrealized_plpc) * 100
        api.close_position(symbol)
        state['daily_trades'] += 1
        if pnl_pct >= 0:
            state['wins'] += 1
            send_notification(f"💰 {reason}", f"{symbol} +{pnl_pct:.2f}%", 1)
        else:
            state['losses'] += 1
            send_notification(f"🛡️ {reason}", f"{symbol} {pnl_pct:.2f}%", 0)
        state['peak_pnl'] = 0.0
        state['breakeven_active'] = False
        print(f"✅ SOLD {symbol} - {reason}: {pnl_pct:.2f}%")
        return True
    except Exception as e:
        print(f"❌ Sell failed: {e}")
        return False

def run_bot():
    print("=" * 50)
    print("🌱 PROJECT HOPE - 24/7 CRYPTO BOT")
    print("=" * 50)
    send_notification("🚀 BOT STARTED", "Project Hope is now trading 24/7", 0)
    
    while True:
        try:
            tz = pytz.timezone('US/Eastern')
            now = datetime.now(tz)
            today = str(now.date())
            
            if state['last_date'] != today:
                state['daily_trades'] = 0
                state['daily_pnl'] = 0.0
                state['last_date'] = today
                state['circuit_breaker'] = False
                state['wins'] = 0
                state['losses'] = 0
                print(f"📅 New day: {today}")
            
            if state['circuit_breaker']:
                print("🚨 Circuit breaker active - waiting for new day")
                time.sleep(SCAN_INTERVAL)
                continue
            
            balance = get_balance()
            if balance < 25:
                print("⚠️ Balance too low")
                time.sleep(SCAN_INTERVAL)
                continue
            
            if state['daily_pnl'] <= -(balance * MAX_DAILY_LOSS):
                state['circuit_breaker'] = True
                send_notification("🚨 CIRCUIT BREAKER", "Daily loss limit hit. Trading stopped.", 2)
                print("🚨 Circuit breaker triggered!")
                time.sleep(SCAN_INTERVAL)
                continue
            
            positions = get_positions()
            
            if positions:
                position = positions[0]
                symbol = position.symbol
                pnl_pct = float(position.unrealized_plpc)
                state['daily_pnl'] = float(position.unrealized_pl)
                
                print(f"📊 {symbol}: {pnl_pct*100:.2f}% (Peak: {state['peak_pnl']*100:.2f}%)")
                
                if pnl_pct > state['peak_pnl']:
                    state['peak_pnl'] = pnl_pct
                
                if pnl_pct >= BREAKEVEN_TRIGGER and not state['breakeven_active']:
                    state['breakeven_active'] = True
                    send_notification("🛡️ BREAKEVEN", f"{symbol} stop moved to $0", 0)
                    print("🛡️ Breakeven activated!")
                
                if state['peak_pnl'] >= BREAKEVEN_TRIGGER:
                    if pnl_pct <= (state['peak_pnl'] - TRAILING_STOP) and pnl_pct > 0:
                        sell_position(position, "TRAILING STOP")
                        time.sleep(5)
                        continue
                
                if pnl_pct >= TAKE_PROFIT:
                    sell_position(position, "TAKE PROFIT")
                    time.sleep(5)
                    continue
                
                effective_stop = 0 if state['breakeven_active'] else -STOP_LOSS
                if pnl_pct <= effective_stop and pnl_pct < 0:
                    sell_position(position, "STOP LOSS")
                    time.sleep(5)
                    continue
            
            else:
                if state['daily_trades'] >= MAX_TRADES_PER_DAY:
                    print("📊 Max trades reached for today")
                    time.sleep(SCAN_INTERVAL)
                    continue
                
                print(f"🔍 Scanning {len(CRYPTO_UNIVERSE)} cryptos...")
                movers = get_crypto_movers(balance)
                
                if movers:
                    for mover in movers:
                        if mover['change'] > 0:
                            signal, strength, reason = get_crypto_signal(mover['symbol'])
                            print(f"   {mover['symbol']}: {signal} ({strength:.0f}%) - {reason}")
                            
                            if signal == "BUY" and strength >= MIN_SIGNAL_STRENGTH:
                                buy_crypto(mover['symbol'], mover['shares'], mover['price'])
                                break
                    else:
                        print("   ⏳ No buy signals")
                else:
                    print("   ❌ No movers found")
            
            print(f"💰 Balance: ${balance:.2f} | P&L: ${state['daily_pnl']:.2f} | Trades: {state['daily_trades']}/{MAX_TRADES_PER_DAY} | W/L: {state['wins']}/{state['losses']}")
            print("-" * 50)
            
            time.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
