import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import time
import requests
import numpy as np

PUSHOVER_USER_KEY = "ugurfo1drgkckg3i8i9x8cmon5qm85"
PUSHOVER_API_TOKEN = "aa9hxotiko33nd33zvih8pxsw2cx6a"
TAKE_PROFIT = 0.01
STOP_LOSS = 0.01
MAX_RISK_PER_TRADE = 0.05
AUTO_SCAN_INTERVAL = 30
STOCK_ALLOCATION = 0.50
CRYPTO_ALLOCATION = 0.50
CRYPTO_UNIVERSE = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "LINK/USD", "UNI/USD"]
STOCK_UNIVERSE = ["SQQQ", "NIO", "PLTR", "SOFI", "SNAP", "HOOD", "RIVN", "LCID", "F", "AAL", "CCL", "T", "WBD", "INTC", "AMD", "UBER", "COIN", "RBLX", "DKNG", "SQ", "PYPL", "BAC", "GM", "PINS", "ROKU", "DIS", "NFLX", "SHOP"]

st.set_page_config(page_title="Project Hope", page_icon="🌱", layout="wide")
load_dotenv()
st_autorefresh(interval=2000, key="refresh")

st.markdown("""<style>
.stApp{background:linear-gradient(180deg,#0a0e1a,#151b2e)}
.main-header{text-align:center;padding:20px;background:linear-gradient(135deg,rgba(0,255,163,0.1),rgba(255,215,0,0.1));border-radius:20px;margin-bottom:20px;border:1px solid rgba(0,255,163,0.3)}
.tier-card{background:linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02));border:1px solid rgba(255,255,255,0.1);border-radius:20px;padding:25px;text-align:center}
.tier-starter{border-top:4px solid #00FFA3}.tier-builder{border-top:4px solid #00E5FF}.tier-master{border-top:4px solid #FFD700}
.position-card{background:rgba(255,255,255,0.05);border-radius:15px;padding:20px;margin:10px 0}
.position-profit{border-left:4px solid #00FFA3}.position-loss{border-left:4px solid #FF4B4B}
.protection-badge{background:linear-gradient(135deg,rgba(0,255,163,0.2),rgba(0,200,100,0.1));border:2px solid #00FFA3;border-radius:12px;padding:15px;text-align:center;margin:15px 0}
.market-open{background:linear-gradient(135deg,rgba(0,255,163,0.3),rgba(0,200,100,0.2));border:2px solid #00FFA3;border-radius:12px;padding:10px;text-align:center}
.market-closed{background:linear-gradient(135deg,rgba(255,75,75,0.3),rgba(200,50,50,0.2));border:2px solid #FF4B4B;border-radius:12px;padding:10px;text-align:center}
.stat-card{background:rgba(255,255,255,0.05);border-radius:15px;padding:20px;text-align:center}
.live-badge{background:rgba(255,0,0,0.2);border:1px solid red;border-radius:4px;padding:2px 8px;font-size:10px;color:red;animation:blink 1s infinite}
.ticker-up{color:#00FFA3;font-weight:bold}.ticker-down{color:#FF4B4B;font-weight:bold}.ticker-neutral{color:#808495}
.ticker-card{background:rgba(255,255,255,0.03);border-radius:10px;padding:10px;text-align:center;margin:5px}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.5}}
.stButton>button{background:linear-gradient(135deg,#00FFA3,#00CC7A);color:black;font-weight:600;border:none;border-radius:10px}
</style>""", unsafe_allow_html=True)

def send_notification(title, msg):
    try: requests.post("https://api.pushover.net/1/messages.json", data={"token": PUSHOVER_API_TOKEN, "user": PUSHOVER_USER_KEY, "title": f"🌱 {title}", "message": msg, "sound": "cashregister"}, timeout=5)
    except: pass

def log_trade(symbol, action, price, qty, pnl_pct, pnl_dollar):
    tz = pytz.timezone('US/Eastern')
    st.session_state.trade_history.insert(0, {'time': datetime.now(tz).strftime("%m/%d %I:%M %p"), 'symbol': symbol, 'action': action, 'price': price, 'qty': qty, 'pnl_pct': pnl_pct, 'pnl_dollar': pnl_dollar})
    st.session_state.total_profit += pnl_dollar
    if len(st.session_state.trade_history) > 50: st.session_state.trade_history = st.session_state.trade_history[:50]

def is_market_open():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    if now.weekday() >= 5: return False
    return now.replace(hour=9, minute=30, second=0, microsecond=0) <= now <= now.replace(hour=16, minute=0, second=0, microsecond=0)

def get_time_until_market():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    if is_market_open():
        delta = now.replace(hour=16, minute=0) - now
        return f"Closes in {delta.seconds//3600}h {(delta.seconds%3600)//60}m"
    next_open = now.replace(hour=9, minute=30)
    if now.hour >= 16: next_open += timedelta(days=1)
    while next_open.weekday() >= 5: next_open += timedelta(days=1)
    delta = next_open - now
    return f"Opens in {delta.days}d {delta.seconds//3600}h" if delta.days > 0 else f"Opens in {delta.seconds//3600}h {(delta.seconds%3600)//60}m"

def get_crypto_price(symbol, api):
    try:
        q = api.get_latest_crypto_quotes(symbol)
        return float(q[symbol].ap) if symbol in q else float(api.get_crypto_bars(symbol, '1Min', limit=1).df['close'].iloc[-1])
    except: return 0

def get_stock_price(symbol, api):
    try: return float(api.get_latest_trade(symbol).price)
    except: return 0

def calc_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    d = np.diff(prices)
    g, l = np.where(d > 0, d, 0), np.where(d < 0, -d, 0)
    ag, al = np.mean(g[-period:]), np.mean(l[-period:])
    return 100 if al == 0 else 100 - (100 / (1 + ag / al))

def calc_ema(prices, period):
    if len(prices) < period: return prices[-1] if len(prices) > 0 else 0
    m = 2 / (period + 1)
    e = prices[0]
    for p in prices[1:]: e = (p * m) + (e * (1 - m))
    return e

def analyze_crypto(symbol, api, balance):
    try:
        bars = api.get_crypto_bars(symbol, '5Min', limit=50).df
        if len(bars) < 10: return None
        prices, volumes = bars['close'].values, bars['volume'].values
        price = get_crypto_price(symbol, api) or float(prices[-1])
        rsi = calc_rsi(prices)
        ema9, ema21 = calc_ema(prices, 9), calc_ema(prices, 21)
        ema12, ema26 = calc_ema(prices, 12), calc_ema(prices, 26)
        hist = (ema12 - ema26) - calc_ema(prices[-9:], 9) if len(prices) >= 9 else 0
        vol_ratio = volumes[-1] / np.mean(volumes[:-1]) if len(volumes) > 1 and np.mean(volumes[:-1]) > 0 else 1
        score, ind = 0, {}
        if 30 <= rsi <= 65: score += 1; ind['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bullish'}
        else: ind['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bearish' if rsi > 65 else 'neutral'}
        if hist > 0: score += 1; ind['MACD'] = {'value': f"{hist:.6f}", 'status': 'bullish'}
        else: ind['MACD'] = {'value': f"{hist:.6f}", 'status': 'bearish'}
        if price > ema9: score += 1; ind['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bullish'}
        else: ind['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bearish'}
        if ema9 > ema21: score += 1; ind['Trend'] = {'value': 'UP', 'status': 'bullish'}
        else: ind['Trend'] = {'value': 'DOWN', 'status': 'bearish'}
        if vol_ratio >= 1: score += 1; ind['Volume'] = {'value': f"{vol_ratio:.1f}x", 'status': 'bullish'}
        else: ind['Volume'] = {'value': f"{vol_ratio:.1f}x", 'status': 'neutral'}
        return {'symbol': symbol, 'price': price, 'score': score, 'signal': 'BUY' if score >= 4 else 'WATCH' if score >= 3 else 'WAIT', 'indicators': ind, 'volume_ratio': vol_ratio, 'stop_price': price * 0.99, 'target_price': price * 1.01, 'shares': round((balance * MAX_RISK_PER_TRADE) / price, 6)}
    except: return None

def analyze_stock(symbol, api, balance):
    try:
        bars = api.get_bars(symbol, '5Min', limit=50).df
        if len(bars) < 10: return None
        prices, volumes = bars['close'].values, bars['volume'].values
        price = get_stock_price(symbol, api) or float(prices[-1])
        if price > balance * 0.5: return None
        rsi = calc_rsi(prices)
        ema9, ema21 = calc_ema(prices, 9), calc_ema(prices, 21)
        ema12, ema26 = calc_ema(prices, 12), calc_ema(prices, 26)
        hist = (ema12 - ema26) - calc_ema(prices[-9:], 9) if len(prices) >= 9 else 0
        vol_ratio = volumes[-1] / np.mean(volumes[:-1]) if len(volumes) > 1 and np.mean(volumes[:-1]) > 0 else 1
        score, ind = 0, {}
        if 30 <= rsi <= 65: score += 1; ind['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bullish'}
        else: ind['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bearish' if rsi > 65 else 'neutral'}
        if hist > 0: score += 1; ind['MACD'] = {'value': f"{hist:.4f}", 'status': 'bullish'}
        else: ind['MACD'] = {'value': f"{hist:.4f}", 'status': 'bearish'}
        if price > ema9: score += 1; ind['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bullish'}
        else: ind['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bearish'}
        if ema9 > ema21: score += 1; ind['Trend'] = {'value': 'UP', 'status': 'bullish'}
        else: ind['Trend'] = {'value': 'DOWN', 'status': 'bearish'}
        if vol_ratio >= 1: score += 1; ind['Volume'] = {'value': f"{vol_ratio:.1f}x", 'status': 'bullish'}
        else: ind['Volume'] = {'value': f"{vol_ratio:.1f}x", 'status': 'neutral'}
        return {'symbol': symbol, 'price': price, 'score': score, 'signal': 'BUY' if score >= 4 else 'WATCH' if score >= 3 else 'WAIT', 'indicators': ind, 'volume_ratio': vol_ratio, 'stop_price': price * 0.99, 'target_price': price * 1.01, 'shares': max(1, int((balance * MAX_RISK_PER_TRADE) / price))}
    except: return None

def scan_crypto(api, bal): return sorted([r for r in [analyze_crypto(s, api, bal) for s in CRYPTO_UNIVERSE] if r], key=lambda x: (x['score'], x['volume_ratio']), reverse=True)
def scan_stocks(api, bal): return sorted([r for r in [analyze_stock(s, api, bal) for s in STOCK_UNIVERSE] if r], key=lambda x: (x['score'], x['volume_ratio']), reverse=True)

try:
    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'), "https://paper-api.alpaca.markets")
    api_connected = True
except: api_connected, api = False, None

for k, v in {'page': 'home', 'tier': 0, 'daily_trades': 0, 'daily_pnl': 0.0, 'last_date': None, 'wins': 0, 'losses': 0, 'scanned_crypto': [], 'scanned_stocks': [], 'last_crypto_scan': 0, 'last_stock_scan': 0, 'autopilot': False, 'trade_history': [], 'total_profit': 0.0, 'prev_prices': {}}.items():
    if k not in st.session_state: st.session_state[k] = v

def render_home():
    st.markdown('<div class="main-header"><h1 style="color:#00FFA3;font-size:3em;">🌱 PROJECT HOPE</h1><p style="color:#808495;">Trade Smart. Protected Always.</p><p style="color:#FFD700;">The #1 Trading App</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.button("🏠 Home", disabled=True, use_container_width=True)
    with c2:
        if st.button("📊 Trade", use_container_width=True):
            if st.session_state.tier > 0: st.session_state.page = 'trade'; st.rerun()
            else: st.warning("Enter code first")
    with c3:
        if st.button("📜 History", use_container_width=True): st.session_state.page = 'history'; st.rerun()
    with c4:
        if st.button("👤 About", use_container_width=True): st.session_state.page = 'about'; st.rerun()
    with c5:
        if st.button("📖 How To", use_container_width=True): st.session_state.page = 'howto'; st.rerun()
    st.markdown("---")
    st.markdown('<div style="text-align:center;padding:30px;"><h2 style="color:white;">Wall Street Has Protection. Now You Do Too.</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown('<div class="stat-card"><h2 style="color:#00FFA3;">🛡️</h2><h4 style="color:white;">Auto Stop-Loss</h4><p style="color:#808495;">-1% on ALL tiers</p></div>', unsafe_allow_html=True)
    with c2: st.markdown('<div class="stat-card"><h2 style="color:#00E5FF;">🤖</h2><h4 style="color:white;">Full Autopilot</h4><p style="color:#808495;">Auto-scan, buy, sell</p></div>', unsafe_allow_html=True)
    with c3: st.markdown('<div class="stat-card"><h2 style="color:#FFD700;">📊</h2><h4 style="color:white;">5-Point Analysis</h4><p style="color:#808495;">RSI, MACD, EMA, Trend, Vol</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Choose Your Plan")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown('<div class="tier-card tier-starter"><h3 style="color:#00FFA3;">🌱 STARTER</h3><h2 style="color:white;">$29/mo</h2><p style="color:white;">✅ Scanner & Stop-Loss</p><p style="color:#808495;">❌ Auto-Buy</p></div>', unsafe_allow_html=True); st.button("Soon", key="t1", disabled=True, use_container_width=True)
    with c2: st.markdown('<div class="tier-card tier-builder"><h3 style="color:#00E5FF;">🚀 BUILDER</h3><h2 style="color:white;">$79/mo</h2><p style="color:white;">✅ One-Click Trade</p><p style="color:#808495;">❌ Autopilot</p></div>', unsafe_allow_html=True); st.button("Soon", key="t2", disabled=True, use_container_width=True)
    with c3: st.markdown('<div class="tier-card tier-master"><h3 style="color:#FFD700;">⚡ MASTER</h3><h2 style="color:white;">$149/mo</h2><p style="color:white;">✅ FULL AUTOPILOT</p><p style="color:white;">✅ Auto-Sell +1%</p></div>', unsafe_allow_html=True); st.button("Soon", key="t3", disabled=True, use_container_width=True)
    st.markdown("---")
    st.markdown("### 🔐 Access Code")
    _, c2, _ = st.columns([1,2,1])
    with c2:
        code = st.text_input("Code", type="password", label_visibility="collapsed")
        if code == "HOPE200": st.session_state.tier = 1; st.success("✅ STARTER!")
        elif code == "HOPE247": st.session_state.tier = 2; st.success("✅ BUILDER!")
        elif code == "HOPE777": st.session_state.tier = 3; st.success("✅ MASTER!")
        elif code: st.error("Invalid")
        if st.session_state.tier > 0 and st.button("🚀 Enter Dashboard", type="primary", use_container_width=True): st.session_state.page = 'trade'; st.rerun()

def render_about():
    st.markdown('<div class="main-header"><h1 style="color:#00FFA3;">🌱 PROJECT HOPE</h1><p style="color:#808495;">About</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("🏠", use_container_width=True, key="a1"): st.session_state.page = 'home'; st.rerun()
    with c2:
        if st.button("📊", use_container_width=True, key="a2"): st.session_state.page = 'trade'; st.rerun()
    with c3:
        if st.button("📜", use_container_width=True, key="a3"): st.session_state.page = 'history'; st.rerun()
    with c4: st.button("👤", disabled=True, use_container_width=True, key="a4")
    with c5:
        if st.button("📖", use_container_width=True, key="a5"): st.session_state.page = 'howto'; st.rerun()
    st.markdown("---")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div style="text-align:center;"><img src="https://i.postimg.cc/qvVSgvfx/IMG-7642.jpg" style="width:100%;max-width:300px;border-radius:20px;border:3px solid #FFD700;"><h2 style="color:#FFD700;margin-top:20px;">Stephen Martinez</h2><p style="color:#00FFA3;">Founder & Developer</p><p style="color:#808495;">Lancaster, PA</p></div>', unsafe_allow_html=True)
    
    with c2:
        st.markdown("## My Story")
        st.markdown("""
I'm **Stephen** — an Amazon warehouse worker from Lancaster, Pennsylvania. Every day I watch my coworkers, friends, and family try to build a better future through trading, only to lose their hard-earned money on apps designed to make them trade more, not trade *smarter*.

I got tired of seeing everyday people get burned while Wall Street has all the protection. So I taught myself to code — during lunch breaks, after 10-hour shifts, late nights when everyone else was sleeping. I studied what separates winning traders from the 95% who lose.
        """)
        st.markdown("### :green[The answer was always the same:] :orange[PROTECTION]")
        st.markdown("""
Wall Street has circuit breakers, stop losses, and risk management systems. Regular people? They get confetti animations when they blow their accounts.
        """)
        st.success("""
**💡 What is Project Hope?**

Project Hope is my mission to level the playing field. It's a trading app with **built-in protection** — automatic stop losses, smart entry signals, and risk management that works FOR you, not against you. No more watching helplessly as a bad trade wipes out your gains.
        """)
        st.warning("""
**🎯 My Mission**

To give everyday people — warehouse workers, teachers, nurses, parents working two jobs — the same protection that hedge funds have. Because everyone deserves a fair shot at building wealth, not just the 1%.
        """)
        st.caption("*This isn't just an app. It's hope for people like me — people who weren't born with a silver spoon but refuse to stop fighting for a better life.*")
    
    st.markdown("---")
    st.markdown("### 📬 Let's Connect")
    st.markdown("📧 **thetradingprotocol@gmail.com**")
    st.caption("Built with 💚 for the 99%")

def render_howto():
    st.markdown('<div class="main-header"><h1 style="color:#00FFA3;">🌱 PROJECT HOPE</h1><p style="color:#808495;">How It Works</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("🏠", use_container_width=True, key="h1"): st.session_state.page = 'home'; st.rerun()
    with c2:
        if st.button("📊", use_container_width=True, key="h2"): st.session_state.page = 'trade'; st.rerun()
    with c3:
        if st.button("📜", use_container_width=True, key="h3"): st.session_state.page = 'history'; st.rerun()
    with c4:
        if st.button("👤", use_container_width=True, key="h4"): st.session_state.page = 'about'; st.rerun()
    with c5: st.button("📖", disabled=True, use_container_width=True, key="h5")
    st.markdown("---")
    st.markdown("## 📊 5-Point Analysis")
    for n, d, c in [("1️⃣ RSI", "30-65 range", "#00FFA3"), ("2️⃣ MACD", "Positive histogram", "#00E5FF"), ("3️⃣ EMA9", "Price above", "#FFD700"), ("4️⃣ Trend", "EMA9 > EMA21", "#FF6B6B"), ("5️⃣ Volume", "Above average", "#9B59B6")]:
        st.markdown(f'<div style="background:rgba(255,255,255,0.05);border-left:4px solid {c};padding:15px;margin:10px 0;border-radius:0 10px 10px 0;"><h4 style="color:{c};margin:0;">{n}</h4><p style="color:#E0E0E0;margin:5px 0;">{d}</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("## 🔴 SQQQ = Inverse ETF")
    st.markdown('<div style="background:rgba(255,75,75,0.1);border-radius:15px;padding:20px;border:1px solid rgba(255,75,75,0.3);"><p style="color:white;">When market DROPS, SQQQ goes UP!</p><p style="color:#808495;">The <b>S</b> in SQQQ = Short (profits from drops)</p></div>', unsafe_allow_html=True)

def render_history():
    st.markdown('<div class="main-header"><h1 style="color:#00FFA3;">🌱 PROJECT HOPE</h1><p style="color:#808495;">History</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("🏠", use_container_width=True, key="hi1"): st.session_state.page = 'home'; st.rerun()
    with c2:
        if st.button("📊", use_container_width=True, key="hi2"): st.session_state.page = 'trade'; st.rerun()
    with c3: st.button("📜", disabled=True, use_container_width=True, key="hi3")
    with c4:
        if st.button("👤", use_container_width=True, key="hi4"): st.session_state.page = 'about'; st.rerun()
    with c5:
        if st.button("📖", use_container_width=True, key="hi5"): st.session_state.page = 'howto'; st.rerun()
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    pc = "#00FFA3" if st.session_state.total_profit >= 0 else "#FF4B4B"
    with c1: st.markdown(f'<div class="stat-card"><p style="color:#808495;">Profit</p><h2 style="color:{pc};">${st.session_state.total_profit:,.2f}</h2></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card"><p style="color:#808495;">Wins</p><h2 style="color:#00FFA3;">{st.session_state.wins}</h2></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card"><p style="color:#808495;">Losses</p><h2 style="color:#FF4B4B;">{st.session_state.losses}</h2></div>', unsafe_allow_html=True)
    t = st.session_state.wins + st.session_state.losses
    wr = (st.session_state.wins / t * 100) if t > 0 else 0
    with c4: st.markdown(f'<div class="stat-card"><p style="color:#808495;">Win Rate</p><h2 style="color:#FFD700;">{wr:.0f}%</h2></div>', unsafe_allow_html=True)
    st.markdown("---")
    if st.session_state.trade_history:
        for tr in st.session_state.trade_history:
            c = "#00FFA3" if tr['pnl_dollar'] >= 0 else "#FF4B4B"
            st.markdown(f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:15px;margin:10px 0;border-left:4px solid {c};"><div style="display:flex;justify-content:space-between;"><div><p style="color:#808495;margin:0;">{tr["time"]}</p><h4 style="color:white;margin:5px 0;">{"✅" if tr["pnl_dollar"] >= 0 else "❌"} {tr["action"]} {tr["symbol"]}</h4></div><div style="text-align:right;"><h3 style="color:{c};margin:0;">{tr["pnl_pct"]:+.2f}%</h3><p style="color:{c};">${tr["pnl_dollar"]:+,.2f}</p></div></div></div>', unsafe_allow_html=True)
    else: st.info("No trades yet!")
    if st.button("🗑️ Clear"): st.session_state.trade_history, st.session_state.total_profit, st.session_state.wins, st.session_state.losses = [], 0.0, 0, 0; st.rerun()

def render_trade():
    if st.session_state.tier == 0: st.warning("Enter code on Home"); return
    tn = {1: "🌱 STARTER", 2: "🚀 BUILDER", 3: "⚡ MASTER"}
    mo = is_market_open()
    c1, c2 = st.columns([3, 1])
    with c1: st.markdown(f'<h2 style="color:#00FFA3;margin:0;">🌱 PROJECT HOPE</h2><p style="color:#808495;">{tn[st.session_state.tier]}</p>', unsafe_allow_html=True)
    with c2: st.markdown('<span class="live-badge">🔴 LIVE</span>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("🏠", use_container_width=True, key="tr1"): st.session_state.page = 'home'; st.rerun()
    with c2: st.button("📊", disabled=True, use_container_width=True, key="tr2")
    with c3:
        if st.button("📜", use_container_width=True, key="tr3"): st.session_state.page = 'history'; st.rerun()
    with c4:
        if st.button("👤", use_container_width=True, key="tr4"): st.session_state.page = 'about'; st.rerun()
    with c5:
        if st.button("📖", use_container_width=True, key="tr5"): st.session_state.page = 'howto'; st.rerun()
    st.markdown("---")
    if not api_connected: st.error("❌ API not connected"); return
    try:
        account = api.get_account()
        balance, cash = float(account.equity), float(account.cash)
    except: st.error("❌ Connection error"); return
    stock_bal = balance * STOCK_ALLOCATION if mo else 0
    crypto_bal = balance * CRYPTO_ALLOCATION if mo else balance
    try: positions = api.list_positions(); pos_symbols = [p.symbol for p in positions]
    except: positions, pos_symbols = [], []
    if mo: st.markdown(f'<div class="market-open"><h3 style="color:#00FFA3;margin:0;">🟢 MARKET OPEN</h3><p style="color:white;">{get_time_until_market()}</p><p style="color:#808495;">📈 ${stock_bal:.2f} | 🪙 ${crypto_bal:.2f}</p></div>', unsafe_allow_html=True)
    else: st.markdown(f'<div class="market-closed"><h3 style="color:#FF4B4B;margin:0;">🔴 MARKET CLOSED</h3><p style="color:white;">{get_time_until_market()}</p><p style="color:#808495;">🪙 100% Crypto: ${crypto_bal:.2f}</p></div>', unsafe_allow_html=True)
    st.markdown("")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("💰 Equity", f"${balance:,.2f}")
    with c2: st.metric("💵 Cash", f"${cash:,.2f}")
    with c3: st.metric("📊 P&L", f"${st.session_state.daily_pnl:,.2f}")
    t = st.session_state.wins + st.session_state.losses
    wr = (st.session_state.wins / t * 100) if t > 0 else 0
    with c4: st.metric("🏆 Win Rate", f"{wr:.0f}%")
    if st.session_state.tier == 3:
        st.markdown("### 🤖 Autopilot")
        c1, c2 = st.columns([1, 3])
        with c1: st.session_state.autopilot = st.toggle("Enable", key="auto")
        with c2:
            if st.session_state.autopilot: st.success("🤖 AUTOPILOT ACTIVE")
    st.markdown('<div class="protection-badge">🛡️ <b>PROTECTION ACTIVE</b> | Stop: -1% | Profit: +1%</div>', unsafe_allow_html=True)
    
    # ==================== LIVE TICKER ====================
    st.markdown("### 📊 Live Prices")
    st.caption("🔴 Updates every 2 seconds")
    
    # Crypto Ticker
    st.markdown("**🪙 Crypto**")
    crypto_html = '<div style="display:flex;flex-wrap:wrap;gap:10px;">'
    for sym in CRYPTO_UNIVERSE:
        price = get_crypto_price(sym, api)
        name = sym.replace("/USD", "")
        prev_key = f"prev_{sym}"
        prev = st.session_state.prev_prices.get(sym, price)
        change = ((price - prev) / prev * 100) if prev > 0 else 0
        st.session_state.prev_prices[sym] = price
        if change > 0: arrow, color = "▲", "#00FFA3"
        elif change < 0: arrow, color = "▼", "#FF4B4B"
        else: arrow, color = "●", "#808495"
        crypto_html += f'<div class="ticker-card"><span style="color:white;font-weight:bold;">{name}</span><br><span style="color:#00E5FF;font-size:1.1em;">${price:,.2f}</span><br><span style="color:{color};">{arrow} {change:+.2f}%</span></div>'
    crypto_html += '</div>'
    st.markdown(crypto_html, unsafe_allow_html=True)
    
    # Stock Ticker (only if market open)
    if mo:
        st.markdown("**📈 Stocks**")
        stock_html = '<div style="display:flex;flex-wrap:wrap;gap:10px;">'
        for sym in STOCK_UNIVERSE[:12]:  # Show first 12 stocks
            price = get_stock_price(sym, api)
            if price == 0: continue
            prev = st.session_state.prev_prices.get(sym, price)
            change = ((price - prev) / prev * 100) if prev > 0 else 0
            st.session_state.prev_prices[sym] = price
            if change > 0: arrow, color = "▲", "#00FFA3"
            elif change < 0: arrow, color = "▼", "#FF4B4B"
            else: arrow, color = "●", "#808495"
            is_inverse = sym == "SQQQ"
            stock_html += f'<div class="ticker-card" style="{"border:1px solid #FF4B4B;" if is_inverse else ""}"><span style="color:{"#FF4B4B" if is_inverse else "white"};font-weight:bold;">{"🔴 " if is_inverse else ""}{sym}</span><br><span style="color:#00E5FF;font-size:1.1em;">${price:,.2f}</span><br><span style="color:{color};">{arrow} {change:+.2f}%</span></div>'
        stock_html += '</div>'
        st.markdown(stock_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if positions:
        st.markdown("### 📈 Positions")
        for pos in positions:
            sym, qty, entry = pos.symbol, float(pos.qty), float(pos.avg_entry_price)
            is_crypto = '/' in sym
            price = get_crypto_price(sym, api) if is_crypto else get_stock_price(sym, api)
            if price == 0: price = float(pos.current_price)
            pnl_d = (price - entry) * qty
            pnl_p = ((price - entry) / entry) * 100
            color = "#00FFA3" if pnl_p >= 0 else "#FF4B4B"
            target, stop = entry * 1.01, entry * 0.99
            if pnl_p <= -1.0:
                try:
                    api.close_position(sym); st.session_state.losses += 1
                    log_trade(sym, "🛡️ STOP", price, qty, pnl_p, pnl_d)
                    send_notification("🛡️ STOP", f"{sym} {pnl_p:.2f}%"); st.rerun()
                except: pass
            if st.session_state.autopilot and st.session_state.tier == 3 and pnl_p >= 1.0:
                try:
                    api.close_position(sym); st.session_state.wins += 1
                    log_trade(sym, "🤖 PROFIT", price, qty, pnl_p, pnl_d)
                    send_notification("🤖 PROFIT", f"{sym} +{pnl_p:.2f}%"); st.balloons(); st.rerun()
                except: pass
            qd = f"{qty:.6f}" if is_crypto else f"{qty:.0f}"
            st.markdown(f'<div class="position-card {"position-profit" if pnl_p >= 0 else "position-loss"}"><div style="display:flex;justify-content:space-between;"><div><h3 style="color:white;margin:0;">{sym}</h3><p style="color:#808495;">Entry: ${entry:,.4f}</p><p style="color:#00E5FF;font-size:1.2em;">Live: ${price:,.4f}</p></div><div style="text-align:right;"><h2 style="color:{color};margin:0;">{pnl_p:+.2f}%</h2><p style="color:{color};">${pnl_d:+,.2f}</p><p style="color:#808495;">Qty: {qd}</p></div></div><div style="margin-top:15px;padding-top:15px;border-top:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;"><p style="color:#00FFA3;margin:0;">🎯 Target: ${target:,.4f}</p><p style="color:#FF4B4B;margin:0;">🛡️ Stop: ${stop:,.4f}</p></div></div>', unsafe_allow_html=True)
            st.session_state.daily_pnl = pnl_d
            c1, c2 = st.columns(2)
            with c1:
                if pnl_p > 0 and st.button(f"🔒 Lock", key=f"l_{sym}", type="primary", use_container_width=True):
                    api.close_position(sym); st.session_state.wins += 1
                    log_trade(sym, "🔒 LOCKED", price, qty, pnl_p, pnl_d)
                    send_notification("🔒 LOCKED", f"{sym} +{pnl_p:.2f}%"); st.balloons(); st.rerun()
            with c2:
                if st.button(f"🚪 Exit", key=f"e_{sym}", use_container_width=True):
                    api.close_position(sym)
                    log_trade(sym, "🚪 EXIT", price, qty, pnl_p, pnl_d)
                    if pnl_p >= 0: st.session_state.wins += 1
                    else: st.session_state.losses += 1
                    send_notification("🚪 EXIT", f"{sym} {pnl_p:.2f}%"); st.rerun()
        st.markdown("---")
    if mo:
        st.markdown(f"### 📈 Stocks (${stock_bal:.2f})")
        if st.session_state.autopilot and st.session_state.tier == 3:
            if time.time() - st.session_state.last_stock_scan >= AUTO_SCAN_INTERVAL:
                st.session_state.scanned_stocks = scan_stocks(api, stock_bal)
                st.session_state.last_stock_scan = time.time()
            st.info(f"🤖 Scan in {max(0, int(AUTO_SCAN_INTERVAL - (time.time() - st.session_state.last_stock_scan)))}s")
        if st.button("🔄 SCAN STOCKS", type="primary"):
            st.session_state.scanned_stocks = scan_stocks(api, stock_bal)
            st.session_state.last_stock_scan = time.time()
        for a in st.session_state.scanned_stocks[:5]:
            stars = "⭐" * a['score'] + "☆" * (5 - a['score'])
            owns = a['symbol'] in pos_symbols
            with st.expander(f"{'🔴 ' if a['symbol']=='SQQQ' else ''}📈 {a['symbol']} ${a['price']:.2f} | {stars}", expanded=(a['score'] >= 4 and not owns)):
                c1, c2 = st.columns(2)
                with c1:
                    for n, d in a['indicators'].items(): st.markdown(f"{'✅' if d['status']=='bullish' else '❌' if d['status']=='bearish' else '⚠️'} **{n}:** {d['value']}")
                with c2: st.markdown(f"Entry: ${a['price']:.2f}\nStop: ${a['stop_price']:.2f}\nTarget: ${a['target_price']:.2f}\nShares: {a['shares']}")
                if owns: st.success(f"✅ Own {a['symbol']}")
                elif a['score'] >= 4 and st.session_state.tier >= 2:
                    if st.session_state.autopilot and st.session_state.tier == 3:
                        try: api.submit_order(symbol=a['symbol'], qty=a['shares'], side='buy', type='market', time_in_force='day'); send_notification("🤖 BUY", a['symbol']); st.balloons(); st.rerun()
                        except: pass
                    elif st.button(f"🟢 BUY {a['symbol']}", key=f"bs_{a['symbol']}", type="primary"):
                        try: api.submit_order(symbol=a['symbol'], qty=a['shares'], side='buy', type='market', time_in_force='day'); send_notification("🟢 BUY", a['symbol']); st.balloons(); st.rerun()
                        except Exception as e: st.error(str(e))
        st.markdown("---")
    st.markdown(f"### 🪙 Crypto (${crypto_bal:.2f})")
    if st.session_state.autopilot and st.session_state.tier == 3:
        if time.time() - st.session_state.last_crypto_scan >= AUTO_SCAN_INTERVAL:
            st.session_state.scanned_crypto = scan_crypto(api, crypto_bal)
            st.session_state.last_crypto_scan = time.time()
        st.info(f"🤖 Scan in {max(0, int(AUTO_SCAN_INTERVAL - (time.time() - st.session_state.last_crypto_scan)))}s")
    if st.button("🔄 SCAN CRYPTO", type="primary"):
        st.session_state.scanned_crypto = scan_crypto(api, crypto_bal)
        st.session_state.last_crypto_scan = time.time()
    for a in st.session_state.scanned_crypto:
        stars = "⭐" * a['score'] + "☆" * (5 - a['score'])
        owns = a['symbol'] in pos_symbols
        with st.expander(f"🪙 {a['symbol']} ${a['price']:.2f} | {stars}", expanded=(a['score'] >= 4 and not owns)):
            c1, c2 = st.columns(2)
            with c1:
                for n, d in a['indicators'].items(): st.markdown(f"{'✅' if d['status']=='bullish' else '❌' if d['status']=='bearish' else '⚠️'} **{n}:** {d['value']}")
            with c2: st.markdown(f"Entry: ${a['price']:.4f}\nStop: ${a['stop_price']:.4f}\nTarget: ${a['target_price']:.4f}\nSize: {a['shares']:.6f}")
            if owns: st.success(f"✅ Own {a['symbol']}")
            elif a['score'] >= 4 and st.session_state.tier >= 2:
                if st.session_state.autopilot and st.session_state.tier == 3:
                    try: api.submit_order(symbol=a['symbol'], qty=a['shares'], side='buy', type='market', time_in_force='gtc'); send_notification("🤖 BUY", a['symbol']); st.balloons(); st.rerun()
                    except: pass
                elif st.button(f"🟢 BUY {a['symbol']}", key=f"bc_{a['symbol']}", type="primary"):
                    try: api.submit_order(symbol=a['symbol'], qty=a['shares'], side='buy', type='market', time_in_force='gtc'); send_notification("🟢 BUY", a['symbol']); st.balloons(); st.rerun()
                    except Exception as e: st.error(str(e))

def main():
    tz = pytz.timezone('US/Eastern')
    today = str(datetime.now(tz).date())
    if st.session_state.last_date != today:
        st.session_state.daily_trades, st.session_state.daily_pnl, st.session_state.last_date = 0, 0.0, today
    page = st.session_state.page
    if page == 'home': render_home()
    elif page == 'about': render_about()
    elif page == 'howto': render_howto()
    elif page == 'history': render_history()
    elif page == 'trade': render_trade()
    else: render_home()

if __name__ == "__main__": main()

