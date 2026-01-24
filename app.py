
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import time
import requests

# Pushover Notifications

nano app.py
```

**Step 6:** Find the same lines near the top and change them the same way:
```
PUSHOVER_USER_KEY = "ugurfo1drgkckg3i8i9x8cmon5qm85"
PUSHOVER_API_TOKEN = "aa9hxotiko33nd33zvih8pxsw2cx6a"
def send_notification(title, message, priority=0):
    """Send push notification to iPhone/Apple Watch"""
    try:
        requests.post("https://api.pushover.net/1/messages.json", data={
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "title": title,
            "message": message,
            "priority": priority,
            "sound": "cashregister"
        })
    except:
        pass

st.set_page_config(page_title="Project Hope", page_icon="🌱", layout="centered")
st_autorefresh(interval=1000, key="clock")
load_dotenv()

try:
    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'), 
        os.getenv('ALPACA_SECRET_KEY'), 
        "https://paper-api.alpaca.markets"
    )
except:
    st.error("Check API setup")
    st.stop()

TAKE_PROFIT = 0.003
STOP_LOSS = 0.005
TRAILING_STOP = 0.002
BREAKEVEN_TRIGGER = 0.0015
MAX_RISK_PER_TRADE = 0.05
MAX_DAILY_LOSS = 0.02
MAX_TRADES_PER_DAY = 10
MIN_ACCOUNT_BALANCE = 25
AUTO_SCAN_INTERVAL = 60

STOCK_UNIVERSE = [
    "NIO", "PLTR", "SOFI", "SNAP", "HOOD", "RIVN", "LCID", "F", "AAL", "CCL",
    "AMD", "UBER", "COIN", "RBLX", "DKNG", "SQ", "PYPL", "BAC", "T", "WBD",
    "INTC", "GM", "SHOP", "ROKU", "NET", "CRWD", "SNOW", "PATH", "U", "PINS",
    "DIS", "AMZN", "GOOG", "META", "NFLX", "CRM", "ORCL", "IBM", "GE", "CAT",
    "NVDA", "AAPL", "MSFT", "TSLA", "V", "MA", "JPM", "HD", "UNH", "PG",
    "SPY", "QQQ", "AVGO", "COST", "LLY", "ISRG", "REGN", "ADBE", "NOW", "PANW"
]

CRYPTO_UNIVERSE = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "LINK/USD", "UNI/USD"]
FRACTIONAL_ASSETS = ["SPY", "QQQ", "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "LINK/USD", "UNI/USD"]

defaults = {
    'daily_trades': 0, 'daily_pnl': 0.0, 'last_date': None, 'show_share': False,
    'autopilot_active': False, 'circuit_breaker': False, 'last_alert': None,
    'entry_price': 0.0, 'hot_stocks': [], 'peak_pnl': 0.0, 'breakeven_active': False,
    'wins': 0, 'losses': 0, 'crypto_mode': False, 'last_scan_time': 0
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

def get_affordable_movers(balance, api):
    max_price = balance * 0.9
    movers = []
    try:
        snapshots = api.get_snapshots(STOCK_UNIVERSE)
        for symbol, snapshot in snapshots.items():
            if snapshot and snapshot.daily_bar:
                price = snapshot.latest_trade.price if snapshot.latest_trade else snapshot.daily_bar.close
                if price > max_price or price < 1:
                    continue
                prev_close = snapshot.prev_daily_bar.close if snapshot.prev_daily_bar else snapshot.daily_bar.open
                if prev_close > 0:
                    change_pct = ((price - prev_close) / prev_close) * 100
                else:
                    continue
                volume = snapshot.daily_bar.volume if snapshot.daily_bar else 0
                if volume >= 500000:
                    movers.append({'symbol': symbol, 'price': price, 'change': change_pct, 'volume': volume,
                                   'shares': max(1, int(balance * MAX_RISK_PER_TRADE / price)), 'is_crypto': False})
        movers.sort(key=lambda x: abs(x['change']), reverse=True)
        return movers[:10]
    except:
        return []

def get_crypto_movers(balance, api):
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
                        'volume': 0, 
                        'shares': shares, 
                        'is_crypto': True
                    })
            except:
                continue
        movers.sort(key=lambda x: x['change'], reverse=True)
        return movers
    except:
        return []

def get_crypto_signal(symbol, api):
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
        return "WAIT", 0, "Scanning..."

st.markdown("""<style>
.stApp {background: linear-gradient(180deg, #0a0e1a 0%, #151b2e 100%);}
.block-container {max-width: 500px; margin: 0 auto; padding: 1rem 1rem 150px 1rem;}
h1, h2, h3, p, div {text-align: center;}
.stMetric {text-align: center;}
.stMetric > div {justify-content: center;}
.stMetric label {justify-content: center;}
.stButton > button {width: 100%;}
.safe-badge {background: rgba(0,255,163,0.1); border: 1px solid #00FFA3; border-radius: 8px; padding: 10px; margin: 10px auto; text-align: center;}
.tier-box {background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin: 15px auto; text-align: center;}
.hot-stock {background: linear-gradient(135deg, rgba(255,215,0,0.2), rgba(255,69,0,0.2)); border: 1px solid #FFD700; border-radius: 8px; padding: 8px; margin: 5px 0; text-align: center;}
.profit-zone {background: linear-gradient(135deg, rgba(0,255,163,0.3), rgba(0,200,100,0.2)); border: 2px solid #00FFA3; border-radius: 12px; padding: 15px; margin: 10px auto; text-align: center; animation: glow 1.5s infinite;}
@keyframes glow {0%, 100% {box-shadow: 0 0 10px rgba(0,255,163,0.5);} 50% {box-shadow: 0 0 25px rgba(0,255,163,0.8);}}
.danger-zone {background: linear-gradient(135deg, rgba(255,75,75,0.3), rgba(200,50,50,0.2)); border: 2px solid #FF4B4B; border-radius: 12px; padding: 15px; margin: 10px auto; text-align: center;}
.gainer {color: #00FFA3;}
.loser {color: #FF4B4B;}
</style>""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180" width="120" height="120" style="filter: drop-shadow(0 4px 8px rgba(0,255,163,0.3));">
        <defs>
            <linearGradient id="premiumGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#FFD700;stop-opacity:1" />
                <stop offset="50%" style="stop-color:#00FFA3;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#00E5B8;stop-opacity:1" />
            </linearGradient>
            <linearGradient id="textGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#FFFFFF;stop-opacity:1" />
                <stop offset="50%" style="stop-color:#00FFA3;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#FFFFFF;stop-opacity:1" />
            </linearGradient>
        </defs>
        <circle cx="90" cy="90" r="85" fill="none" stroke="url(#premiumGrad)" stroke-width="2" opacity="0.3"/>
        <g transform="translate(90, 70)">
            <path d="M 0,-25 L 18,-8 L 18,8 L 0,25 L -18,8 L -18,-8 Z" fill="url(#premiumGrad)" opacity="0.9"/>
            <circle cx="0" cy="0" r="5" fill="#FFFFFF" opacity="0.9"/>
        </g>
        <g transform="translate(90, 55)">
            <polygon points="0,-15 -8,-5 -3,-5 -3,5 3,5 3,-5 8,-5" fill="url(#premiumGrad)"/>
        </g>
        <text x="90" y="115" font-family="Arial" font-size="16" font-weight="900" fill="url(#textGrad)" text-anchor="middle" letter-spacing="2">PROJECT</text>
        <text x="90" y="138" font-family="Arial" font-size="26" font-weight="900" fill="url(#premiumGrad)" text-anchor="middle" letter-spacing="3">HOPE</text>
        <line x1="50" y1="143" x2="130" y2="143" stroke="url(#premiumGrad)" stroke-width="2" opacity="0.6"/>
    </svg>
</div>
<p style="text-align: center; color: #808495; font-size: 13px; letter-spacing: 2px; margin-bottom: 20px;">SCALP SMART • TRADE FAST • WIN BIG</p>
""", unsafe_allow_html=True)

st.markdown("### 🔐 Enter Access Code")
col1, col2, col3 = st.columns([1,2,1])
with col2:
    code = st.text_input("", type="password", placeholder="Enter code...", label_visibility="collapsed")

tier = 1 if code == "HOPE200" else 2 if code == "HOPE247" else 3 if code == "HOPE777" else 0

if tier:
    tier_names = {1: "🌱 STARTER", 2: "🚀 BUILDER", 3: "⚡ MASTER"}
    st.success(f"✅ TIER {tier} - {tier_names[tier]}")
else:
    st.markdown("""
    <div class="tier-box">
        <p style="color: #00FFA3; margin: 5px 0;">🌱 TIER 1 - STARTER</p>
        <p style="color: #808495; font-size: 12px; margin: 0 0 15px 0;">Smart Scanner + Alerts</p>
        <p style="color: #00E5FF; margin: 5px 0;">🚀 TIER 2 - BUILDER</p>
        <p style="color: #808495; font-size: 12px; margin: 0 0 15px 0;">Scanner + Crypto 24/7</p>
        <p style="color: #FFD700; margin: 5px 0;">⚡ TIER 3 - MASTER</p>
        <p style="color: #808495; font-size: 12px; margin: 0;">Full Access + Autopilot + Trailing Stop</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown('<div class="safe-badge">🛡️ <b>BOSS MODE</b> • Trailing Stop • Auto Breakeven • Profit Lock</div>', unsafe_allow_html=True)
st.divider()

tz = pytz.timezone('US/Eastern')
now = datetime.now(tz)
today = str(now.date())

if st.session_state.last_date != today:
    st.session_state.daily_trades = 0
    st.session_state.daily_pnl = 0.0
    st.session_state.last_date = today
    st.session_state.circuit_breaker = False
    st.session_state.hot_stocks = []
    st.session_state.peak_pnl = 0.0
    st.session_state.breakeven_active = False
    st.session_state.wins = 0
    st.session_state.losses = 0

market_open = (9 <= now.hour < 16) and (now.weekday() < 5)
target = now.replace(hour=9, minute=30, second=0, microsecond=0)
if now >= target.replace(hour=16): target += timedelta(days=1)
while target.weekday() > 4: target += timedelta(days=1)
delta = target - now

st.markdown(f"<h2 style='text-align:center;'>⏰ {delta.seconds//3600:02d}:{(delta.seconds%3600)//60:02d}:{delta.seconds%60:02d}</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;'><b>{'MARKET OPEN' if market_open else 'NEXT BELL'}</b></p>", unsafe_allow_html=True)
st.divider()

try:
    account = api.get_account()
    balance = float(account.equity)
except:
    st.error("❌ Could not connect to account")
    st.stop()

ticker = None
crypto = False
autopilot = False
selected_stock = None

with st.sidebar:
    st.markdown("### 🔥 SMART SCANNER")
    st.caption(f"Finding trades for ${balance:.0f} account")
    scan_mode = st.radio("Mode:", ["🪙 CRYPTO (No PDT!)", "📈 STOCKS"], horizontal=True)
    
    if scan_mode == "🪙 CRYPTO (No PDT!)":
        st.markdown('<p style="color:#00FFA3; font-size:12px;">✅ Unlimited day trades • 24/7 trading</p>', unsafe_allow_html=True)
        if st.button("🔄 SCAN CRYPTO", use_container_width=True):
            with st.spinner("Scanning crypto..."):
                st.session_state.hot_stocks = get_crypto_movers(balance, api)
                st.session_state.crypto_mode = True
                st.session_state.last_scan_time = time.time()
    else:
        st.markdown('<p style="color:#FFA500; font-size:12px;">⚠️ 3 day trades per 5 days (PDT Rule)</p>', unsafe_allow_html=True)
        if st.button("🔄 SCAN STOCKS", use_container_width=True):
            with st.spinner("Scanning 60 stocks..."):
                st.session_state.hot_stocks = get_affordable_movers(balance, api)
                st.session_state.crypto_mode = False
                st.session_state.last_scan_time = time.time()
    
    if st.session_state.hot_stocks:
        st.markdown("---")
        is_crypto = st.session_state.get('crypto_mode', False)
        st.markdown(f"**{'🔥 5-MIN MOMENTUM:' if is_crypto else 'TOP STOCK MOVERS:'}**")
        for stock in st.session_state.hot_stocks[:5]:
            change_class = "gainer" if stock['change'] > 0 else "loser"
            arrow = "🟢" if stock['change'] > 0 else "🔴"
            display_symbol = stock['symbol']
            shares_display = f"{stock['shares']:.4f}" if is_crypto else f"{stock['shares']}"
            st.markdown(f'<div class="hot-stock">{arrow} <b>{display_symbol}</b> ${stock["price"]:,.2f} <span class="{change_class}">({stock["change"]:+.2f}%)</span><br><small style="color:#808495;">{shares_display} units</small></div>', unsafe_allow_html=True)
    else:
        st.info("👆 Tap SCAN to find trades")

if st.session_state.hot_stocks:
    is_crypto = st.session_state.get('crypto_mode', False)
    stock_options = [f"{s['symbol']} (${s['price']:,.2f})" for s in st.session_state.hot_stocks[:5]]
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"### 🎯 SELECT {'CRYPTO' if is_crypto else 'STOCK'}")
        selected = st.selectbox("Choose:", ["-- Select --"] + stock_options, label_visibility="collapsed")
        if selected != "-- Select --":
            ticker = selected.split(" (")[0]
            for s in st.session_state.hot_stocks:
                if s['symbol'] == ticker:
                    selected_stock = s
                    crypto = is_crypto
                    break

if tier == 3:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🤖 AUTOPILOT")
        autopilot = st.checkbox("Full Auto Trading")
        if autopilot:
            st.markdown('<div style="background: linear-gradient(135deg, rgba(255,215,0,0.3), rgba(255,165,0,0.2)); border: 2px solid #FFD700; border-radius: 12px; padding: 10px; margin: 10px 0; text-align: center;"><b>🤖 BOT IS LIVE</b><br><small>Auto-scan • Auto-trade • Auto-protect</small></div>', unsafe_allow_html=True)
            
            current_time = time.time()
            time_since_scan = current_time - st.session_state.last_scan_time
            next_scan_in = max(0, AUTO_SCAN_INTERVAL - time_since_scan)
            st.caption(f"⏱️ Next scan in: {int(next_scan_in)}s")
            
            if time_since_scan >= AUTO_SCAN_INTERVAL or st.session_state.last_scan_time == 0:
                st.session_state.hot_stocks = get_crypto_movers(balance, api)
                st.session_state.crypto_mode = True
                st.session_state.last_scan_time = current_time
            
            if st.session_state.hot_stocks:
                for stock in st.session_state.hot_stocks:
                    if stock['change'] > 0:
                        ticker = stock['symbol']
                        selected_stock = stock
                        crypto = True
                        break
                if not ticker and st.session_state.hot_stocks:
                    ticker = st.session_state.hot_stocks[0]['symbol']
                    selected_stock = st.session_state.hot_stocks[0]
                    crypto = True

with st.sidebar:
    st.markdown("---")
    st.markdown("### 🛡️ PROTECTION")
    st.metric("Trades", f"{st.session_state.daily_trades}/{MAX_TRADES_PER_DAY}")
    st.metric("Daily P&L", f"${st.session_state.daily_pnl:.2f}")
    total_trades = st.session_state.wins + st.session_state.losses
    win_rate = (st.session_state.wins / total_trades * 100) if total_trades > 0 else 0
    st.metric("Win Rate", f"{win_rate:.0f}% ({st.session_state.wins}W/{st.session_state.losses}L)")

try:
    start_balance = balance - st.session_state.daily_pnl
    if balance < MIN_ACCOUNT_BALANCE:
        st.error(f"🚨 Balance below ${MIN_ACCOUNT_BALANCE}")
        st.stop()
    if st.session_state.daily_pnl <= -(start_balance * MAX_DAILY_LOSS):
        st.session_state.circuit_breaker = True
    if st.session_state.circuit_breaker:
        send_notification("🚨 CIRCUIT BREAKER", "Daily loss limit hit. Trading stopped.", 2)
        st.error("🚨 CIRCUIT BREAKER ACTIVE")
        st.stop()

    positions = api.list_positions()
    current_position = None
    has_position = False
    for p in positions:
        current_position = p
        has_position = True
        ticker = p.symbol
        crypto = ticker in CRYPTO_UNIVERSE
        break

    if ticker:
        try:
            if crypto or ticker in CRYPTO_UNIVERSE:
                quote = api.get_latest_crypto_quotes(ticker)
                if ticker in quote:
                    price = float(quote[ticker].ap)
                else:
                    bars = api.get_crypto_bars(ticker, '1Min', limit=1).df
                    price = float(bars['close'].iloc[-1]) if len(bars) >= 1 else 0
                crypto = True
            else:
                price = float(api.get_latest_trade(ticker).price)
        except:
            price = selected_stock['price'] if selected_stock else 0
        if crypto or ticker in FRACTIONAL_ASSETS:
            shares = round((balance * MAX_RISK_PER_TRADE) / price, 6) if crypto else round((balance * MAX_RISK_PER_TRADE) / price, 3)
        else:
            shares = max(1, int(balance * MAX_RISK_PER_TRADE / price)) if balance >= price else 0
    else:
        price, shares = 0, 0

    if has_position and current_position:
        current_pnl = float(current_position.unrealized_pl)
        current_pnl_pct = float(current_position.unrealized_plpc)
        st.session_state.daily_pnl = current_pnl
        if current_pnl_pct > st.session_state.peak_pnl:
            st.session_state.peak_pnl = current_pnl_pct
        if current_pnl_pct >= BREAKEVEN_TRIGGER and not st.session_state.breakeven_active:
            st.session_state.breakeven_active = True
            st.toast("🛡️ Stop moved to BREAKEVEN!", icon="✅")
        if st.session_state.peak_pnl >= BREAKEVEN_TRIGGER:
            if current_pnl_pct <= (st.session_state.peak_pnl - TRAILING_STOP) and current_pnl_pct > 0:
                api.close_position(current_position.symbol)
                st.session_state.daily_trades += 1
                st.session_state.wins += 1
                send_notification("🔒 TRAILING STOP", f"{current_position.symbol} +{current_pnl_pct*100:.2f}% locked!", 1)
                st.success(f"🔒 TRAILING STOP: +{current_pnl_pct*100:.2f}%")
                st.balloons()
                st.session_state.peak_pnl = 0.0
                st.session_state.breakeven_active = False
                time.sleep(2)
                st.rerun()
        if current_pnl_pct >= TAKE_PROFIT:
            api.close_position(current_position.symbol)
            st.session_state.daily_trades += 1
            st.session_state.wins += 1
            send_notification("💰 TAKE PROFIT", f"{current_position.symbol} +{current_pnl_pct*100:.2f}% WIN!", 1)
            st.success(f"✅ TAKE PROFIT: +{current_pnl_pct*100:.2f}%")
            st.balloons()
            st.session_state.peak_pnl = 0.0
            st.session_state.breakeven_active = False
            time.sleep(2)
            st.rerun()
        effective_stop = 0 if st.session_state.breakeven_active else -STOP_LOSS
        if current_pnl_pct <= effective_stop and current_pnl_pct < 0:
            api.close_position(current_position.symbol)
            st.session_state.daily_trades += 1
            st.session_state.losses += 1
            send_notification("🛡️ STOP LOSS", f"{current_position.symbol} {current_pnl_pct*100:.2f}% - Protected!", 0)
            st.error(f"🛡️ STOP LOSS: {current_pnl_pct*100:.2f}%")
            st.session_state.peak_pnl = 0.0
            st.session_state.breakeven_active = False
            time.sleep(2)
            st.rerun()

    col1, col2 = st.columns(2)
    with col1: st.metric("Balance", f"${balance:.2f}")
    with col2: st.metric("P&L", f"${st.session_state.daily_pnl:.2f}")

    if ticker:
        display_ticker = ticker if '/' in ticker else ticker
        st.markdown(f"<p style='text-align:center; color:#00FFA3; font-size:12px;'>{'🪙 CRYPTO • NO PDT • 24/7' if crypto else '📈 STOCK'}</p>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;'>🎯 {display_ticker}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align:center;'>${price:,.2f}</h1>", unsafe_allow_html=True)
        shares_display = f"{shares:.6f}" if crypto else f"{shares}"
        st.markdown(f"<p style='text-align:center; color:#808495;'>Size: {shares_display} {'units' if crypto else 'shares'}</p>", unsafe_allow_html=True)
        
        signal = "WAIT"
        signal_strength = 0
        signal_reason = ""
        if crypto and not has_position:
            signal, signal_strength, signal_reason = get_crypto_signal(ticker, api)
            if signal == "BUY":
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(0,255,163,0.3), rgba(0,200,100,0.2)); border: 2px solid #00FFA3; border-radius: 12px; padding: 15px; margin: 10px auto; text-align: center;">
                    <h2 style="color: #00FFA3; margin: 0;">🟢 BUY SIGNAL</h2>
                    <p style="color: white; margin: 5px 0;">{signal_reason}</p>
                    <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 5px; margin-top: 10px;">
                        <div style="background: linear-gradient(90deg, #00FFA3, #00CC7A); width: {signal_strength}%; height: 8px; border-radius: 4px;"></div>
                    </div>
                    <p style="color: #808495; font-size: 11px; margin-top: 5px;">Signal Strength: {signal_strength:.0f}%</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: rgba(255,165,0,0.2); border: 2px solid #FFA500; border-radius: 12px; padding: 15px; margin: 10px auto; text-align: center;">
                    <h2 style="color: #FFA500; margin: 0;">⏳ WAIT</h2>
                    <p style="color: #808495; margin: 5px 0;">{signal_reason}</p>
                    <p style="color: #808495; font-size: 11px;">Don't buy into falling momentum</p>
                </div>
                """, unsafe_allow_html=True)

        if has_position and current_position:
            pnl_pct = float(current_position.unrealized_plpc) * 100
            if pnl_pct > 0:
                st.markdown(f'<div class="profit-zone"><h2 style="color: #00FFA3; margin: 0;">💰 WINNING: +{pnl_pct:.2f}%</h2><p style="color: white; margin: 5px 0;">Peak: +{st.session_state.peak_pnl*100:.2f}%</p><p style="color: #808495; font-size: 12px;">{"🛡️ BREAKEVEN ACTIVE" if st.session_state.breakeven_active else "⏳ Breakeven at +0.15%"}</p></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="danger-zone"><h2 style="color: #FF4B4B; margin: 0;">📉 DOWN: {pnl_pct:.2f}%</h2><p style="color: #808495; font-size: 12px;">Stop: {"BREAKEVEN" if st.session_state.breakeven_active else "-0.5%"}</p></div>', unsafe_allow_html=True)
            st.progress(min(max((pnl_pct + 0.5) / 0.8, 0), 1))
            st.markdown("---")
            if pnl_pct > 0:
                if st.button(f"🔒 LOCK PROFIT (+{pnl_pct:.2f}%)", use_container_width=True, type="primary"):
                    api.close_position(current_position.symbol)
                    st.session_state.daily_trades += 1
                    st.session_state.wins += 1
                    st.balloons()
                    st.session_state.peak_pnl = 0.0
                    st.session_state.breakeven_active = False
                    time.sleep(1)
                    st.rerun()
            if st.button("🚪 EXIT NOW", use_container_width=True):
                api.close_position(current_position.symbol)
                st.session_state.daily_trades += 1
                if pnl_pct >= 0: st.session_state.wins += 1
                else: st.session_state.losses += 1
                st.session_state.peak_pnl = 0.0
                st.session_state.breakeven_active = False
                time.sleep(1)
                st.rerun()
        else:
            good_signal = signal == "BUY" if crypto else True
            can_trade = (crypto or market_open) and st.session_state.daily_trades < MAX_TRADES_PER_DAY and not st.session_state.circuit_breaker and shares > 0
            
            if not can_trade:
                if not (crypto or market_open): st.info("⏰ Markets closed - Switch to CRYPTO for 24/7!")
                elif shares == 0: st.warning(f"⚠️ Need ${price:.2f} minimum")
            
            if can_trade and good_signal:
                if st.button("🟢 BUY NOW", use_container_width=True, type="primary"):
                    api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force='gtc' if crypto else 'day')
                    st.session_state.daily_trades += 1
                    st.session_state.peak_pnl = 0.0
                    st.session_state.breakeven_active = False
                    send_notification("🟢 BOUGHT", f"{ticker} @ ${price:,.2f}", 1)
                    st.success("✅ BUY - Boss Mode Active!")
                    time.sleep(1)
                    st.rerun()
            elif can_trade and not good_signal:
                st.button("⏳ WAIT FOR SIGNAL", disabled=True, use_container_width=True)
                st.caption("Button activates when momentum turns up")
            else:
                st.button("🟢 BUY", disabled=True, use_container_width=True)
            
            if tier == 3 and autopilot and can_trade and good_signal and signal_strength >= 50:
                api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force='gtc' if crypto else 'day')
                st.session_state.daily_trades += 1
                st.session_state.peak_pnl = 0.0
                st.session_state.breakeven_active = False
                send_notification("🤖 AUTO BUY", f"{ticker} @ ${price:,.2f}\n{signal_reason}", 1)
                st.success(f"🤖 AUTO BUY - {signal_reason}")
                time.sleep(1)
                st.rerun()
    else:
        st.markdown("<h3 style='text-align:center; color:#808495;'>👈 Scan & Select a Trade</h3>", unsafe_allow_html=True)

    st.divider()
    with st.expander("🛡️ BOSS MODE RULES"):
        st.markdown("""
        **5-Layer Protection:**
        1. Auto Breakeven at +0.15%
        2. Trailing Stop -0.2% from peak
        3. Take Profit at +0.3%
        4. Stop Loss at -0.5%
        5. Circuit Breaker at -2% daily
        
        **AUTOPILOT (Tier 3):**
        - Auto-scans every 60 seconds
        - Auto-picks best mover
        - Auto-buys on 50%+ signal
        - Auto-protects with Boss Mode
        
        **CRYPTO = NO PDT + 24/7 Trading!**
        """)
    
    if st.button("📱 SHARE", use_container_width=True):
        st.session_state.show_share = not st.session_state.show_share
    if st.session_state.show_share:
        st.code(f"🌱 PROJECT HOPE\n💰 ${balance:.2f}\n📊 P&L: ${st.session_state.daily_pnl:+.2f}\n🏆 {win_rate:.0f}% Win Rate\n#ProjectHope")

except Exception as e:
    st.error(f"Error: {e}")
