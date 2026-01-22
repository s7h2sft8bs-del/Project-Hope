# Get data with MAXIMUM SAFETY
try:
    account = api.get_account()
    balance = float(account.equity)
    
    # SAFETY CHECK 1: Minimum balance
    if balance < MIN_ACCOUNT_BALANCE:
        st.error(f"🚨 ACCOUNT LOCKED: Balance below ${MIN_ACCOUNT_BALANCE}")
        st.info("Deposit funds to continue trading")
        st.stop()
    
    # SAFETY CHECK 2: Daily loss limit (CIRCUIT BREAKER)
    start_balance = balance + st.session_state.daily_pnl
    daily_loss_pct = abs(st.session_state.daily_pnl / start_balance) if start_balance > 0 else 0
    
    if st.session_state.daily_pnl < 0 and daily_loss_pct >= MAX_DAILY_LOSS:
        st.session_state.circuit_breaker = True
        st.error("🚨 CIRCUIT BREAKER ACTIVATED")
        st.error(f"Daily loss limit reached: {daily_loss_pct*100:.1f}% (Max: {MAX_DAILY_LOSS*100}%)")
        st.info("Trading locked until tomorrow. Your account is protected.")
        st.stop()
    
    # Get price
    if crypto:
        price = float(api.get_latest_crypto_trade(ticker, exchange='CBSE').price)
    else:
        price = float(api.get_latest_trade(ticker).price)
    
    # SAFETY CHECK 3: Position sizing with multiple limits
    risk_amount = balance * MAX_RISK_PER_TRADE
    max_position_value = balance * MAX_POSITION_SIZE
    shares = min(
        round(risk_amount / price, 3),  # 1% risk limit
        round(max_position_value / price, 3)  # 2% position limit
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import time

st.set_page_config(page_title="Project Hope", page_icon="🌱", layout="wide")
st_autorefresh(interval=1000, key="clock")
load_dotenv()

try:
    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'), "https://paper-api.alpaca.markets")
except:
    st.error("Check API setup")
    st.stop()

# SAFETY LIMITS
MAX_RISK_PER_TRADE = 0.005  # 0.5% risk for scalping
MAX_DAILY_LOSS = 0.02  # 2% max daily loss
MIN_ACCOUNT_BALANCE = 25
MAX_POSITION_SIZE = 0.01  # 1% position for quick scalps

# Session state
for key in ['daily_trades', 'daily_pnl', 'last_date', 'show_share', 'autopilot_active', 'circuit_breaker', 'last_alert']:
    if key not in st.session_state:
        st.session_state[key] = 0 if 'trades' in key or 'pnl' in key else None if 'date' in key or 'alert' in key else False

# Styling
st.markdown("""<style>
.stApp {background: linear-gradient(180deg, #0a0e1a 0%, #151b2e 100%);}
.block-container {max-width: 480px; margin: auto;}
.alert-box {background: rgba(255,165,0,0.2); border: 2px solid #FFA500; border-radius: 12px; 
             padding: 15px; margin: 10px 0; animation: pulse 2s infinite;}
@keyframes pulse {0%, 100% {opacity: 1;} 50% {opacity: 0.7;}}
</style>""", unsafe_allow_html=True)

# Logo
st.markdown("# 🌱 PROJECT HOPE")
st.markdown("**Scalp Smart • Trade Fast**")
st.divider()

# Sidebar
with st.sidebar:
    st.markdown("### 🔐 ACCESS")
    code = st.text_input("Code", type="password")
    tier = 1 if code == "HOPE200" else 2 if code == "HOPE247" else 3 if code == "HOPE777" else 0
    if tier: st.success(f"✅ TIER {tier}")

if not tier:
    st.info("Enter code: HOPE200, HOPE247, or HOPE777")
    st.stop()

# Time
tz = pytz.timezone('US/Eastern')
now = datetime.now(tz)
market_open = (9 <= now.hour < 16) and (now.weekday() < 5)

# Countdown
target = now.replace(hour=9, minute=30, second=0, microsecond=0)
if now >= target.replace(hour=16): target += timedelta(days=1)
while target.weekday() > 4: target += timedelta(days=1)
delta = target - now
st.markdown(f"### ⏰ {delta.seconds//3600:02d}:{(delta.seconds%3600)//60:02d}:{delta.seconds%60:02d}")
st.markdown("**MARKET OPEN**" if market_open else "**NEXT BELL**")
st.divider()

# Asset selection
ticker = "SPY"
crypto = False
autopilot = False

if tier >= 2 and now.hour >= 16:
    with st.sidebar:
        st.divider()
        st.markdown("### ⚡ CRYPTO")
        if st.checkbox("Enable Crypto"):
            crypto = True
            ticker = "BTCUSD" if st.radio("", ["Bitcoin", "Ethereum"]) == "Bitcoin" else "ETHUSD"

if tier == 3:
    with st.sidebar:
        st.divider()
        st.markdown("### 🎯 STOCK")
        ticker = st.selectbox("Select", ["SPY", "QQQ", "NVDA"])
        
        st.divider()
        st.markdown("### 🤖 AUTOPILOT")
        autopilot = st.checkbox("Full Auto Trading")
        if autopilot:
            st.warning("⚠️ BOT IS LIVE")
            st.info("Taking all scalp trades automatically")

# Sidebar stats
with st.sidebar:
    st.divider()
    st.metric("Daily Trades", f"{st.session_state.daily_trades}/15")
    st.metric("Risk/Trade", "0.5%")

# TRADING ENGINE
try:
    account = api.get_account()
    balance = float(account.equity)
    
    # Safety checks
    if balance < MIN_ACCOUNT_BALANCE:
        st.error(f"🚨 Balance below ${MIN_ACCOUNT_BALANCE}")
        st.stop()
    
    start_balance = balance + st.session_state.daily_pnl
    daily_loss_pct = abs(st.session_state.daily_pnl / start_balance) if start_balance > 0 else 0
    
    if st.session_state.daily_pnl < 0 and daily_loss_pct >= MAX_DAILY_LOSS:
        st.session_state.circuit_breaker = True
        st.error("🚨 CIRCUIT BREAKER ACTIVE")
        st.error(f"Daily loss: {daily_loss_pct*100:.1f}% (Max: {MAX_DAILY_LOSS*100}%)")
        st.info("Trading locked until tomorrow")
        st.stop()
    
    # Get price
    if crypto:
        price = float(api.get_latest_crypto_trade(ticker, exchange='CBSE').price)
    else:
        price = float(api.get_latest_trade(ticker).price)
    
    # Position sizing
    risk_amount = balance * MAX_RISK_PER_TRADE
    max_position_value = balance * MAX_POSITION_SIZE
    shares = min(round(risk_amount / price, 3), round(max_position_value / price, 3))
    
    # Check positions
    positions = api.list_positions()
    has_position = any(p.symbol == ticker for p in positions)
    
    # Calculate P&L
    for p in positions:
        if p.symbol == ticker:
            st.session_state.daily_pnl = float(p.unrealized_pl)
    
    # SCALPING ANALYSIS (1-min bars for speed)
    scalp_signal = None
    signal_strength = 0
    
    try:
        if crypto:
            bars = api.get_crypto_bars(ticker, '1Min', limit=20, exchanges=['CBSE']).df
        else:
            bars = api.get_bars(ticker, '1Min', limit=20).df
        
        if len(bars) >= 20:
            # Fast scalping indicators
            ema_5 = bars['close'].tail(5).mean()   # Very fast EMA
            ema_10 = bars['close'].tail(10).mean()  # Fast EMA
            current_candle_change = (price - bars['close'].iloc[-2]) / bars['close'].iloc[-2] * 100
            
            # Volume spike check
            avg_volume = bars['volume'].tail(10).mean()
            current_volume = bars['volume'].iloc[-1]
            volume_spike = current_volume > (avg_volume * 1.2)
            
            # SCALP BUY: Quick momentum + volume
            if (price > ema_5 and ema_5 > ema_10 and current_candle_change > 0.05 and volume_spike):
                scalp_signal = "BUY"
                signal_strength = abs(current_candle_change)
            
            # SCALP SELL: Quick reversal + volume
            elif (price < ema_5 and ema_5 < ema_10 and current_candle_change < -0.05 and volume_spike):
                scalp_signal = "SELL"
                signal_strength = abs(current_candle_change)
            
            # TIER 1 & 2: SCALP ALERTS ONLY
            if tier in [1, 2] and scalp_signal and not has_position:
                # Prevent alert spam (only alert once per minute)
                current_minute = now.strftime("%H:%M")
                if st.session_state.last_alert != current_minute:
                    st.session_state.last_alert = current_minute
                    
                    alert_color = "#00FFA3" if scalp_signal == "BUY" else "#FF4B4B"
                    st.markdown(f"""
                    <div class="alert-box" style="border-color: {alert_color};">
                        <h2 style="color: {alert_color}; margin: 0;">⚡ SCALP ALERT: {scalp_signal}</h2>
                        <p style="color: white; margin: 5px 0;">Momentum: {signal_strength:.2f}%</p>
                        <p style="color: #808495; font-size: 12px; margin: 0;">Click {scalp_signal} button now!</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # TIER 3: AUTOPILOT EXECUTION
            if tier == 3 and autopilot and st.session_state.daily_trades < 15 and (market_open or crypto) and not st.session_state.circuit_breaker:
                
                # Auto stop loss at 0.5%
                if has_position and st.session_state.daily_pnl < -(balance * 0.005):
                    api.close_position(ticker)
                    st.session_state.daily_trades += 1
                    st.session_state.autopilot_active = False
                    st.error("🛡️ STOP LOSS: -0.5%")
