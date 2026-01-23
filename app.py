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

MAX_RISK_PER_TRADE = 0.005
MAX_DAILY_LOSS = 0.02
MIN_ACCOUNT_BALANCE = 25
MAX_POSITION_SIZE = 0.01

for key in ['daily_trades', 'daily_pnl', 'last_date', 'show_share', 'autopilot_active', 'circuit_breaker', 'last_alert']:
    if key not in st.session_state:
        st.session_state[key] = 0 if 'trades' in key or 'pnl' in key else None if 'date' in key or 'alert' in key else False

st.markdown("""<style>
.stApp {background: linear-gradient(180deg, #0a0e1a 0%, #151b2e 100%);}
.block-container {max-width: 480px; margin: auto;}
.alert-box {background: rgba(255,165,0,0.2); border: 2px solid #FFA500; border-radius: 12px; padding: 15px; margin: 10px 0; animation: pulse 2s infinite;}
@keyframes pulse {0%, 100% {opacity: 1;} 50% {opacity: 0.7;}}
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
<div style="text-align: center; color: #808495; font-size: 13px; letter-spacing: 2px; margin-bottom: 30px;">SCALP SMART • TRADE FAST</div>
""", unsafe_allow_html=True)

st.divider()
with st.sidebar:
    st.markdown("### 🔐 ACCESS")
    code = st.text_input("Code", type="password")
    tier = 1 if code == "HOPE200" else 2 if code == "HOPE247" else 3 if code == "HOPE777" else 0
    if tier: st.success(f"✅ TIER {tier}")

if not tier:
    st.info("Enter code: HOPE200, HOPE247, or HOPE777")
    st.stop()

tz = pytz.timezone('US/Eastern')
now = datetime.now(tz)
market_open = (9 <= now.hour < 16) and (now.weekday() < 5)

target = now.replace(hour=9, minute=30, second=0, microsecond=0)
if now >= target.replace(hour=16): target += timedelta(days=1)
while target.weekday() > 4: target += timedelta(days=1)
delta = target - now
st.markdown(f"### ⏰ {delta.seconds//3600:02d}:{(delta.seconds%3600)//60:02d}:{delta.seconds%60:02d}")
st.markdown("**MARKET OPEN**" if market_open else "**NEXT BELL**")
st.divider()

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

with st.sidebar:
    st.divider()
    st.metric("Daily Trades", f"{st.session_state.daily_trades}/15")
    st.metric("Risk/Trade", "0.5%")

try:
    account = api.get_account()
    balance = float(account.equity)
    
    if balance < MIN_ACCOUNT_BALANCE:
        st.error(f"🚨 Balance below ${MIN_ACCOUNT_BALANCE}")
        st.stop()
    
    if crypto:
        price = float(api.get_latest_crypto_trade(ticker, exchange='CBSE').price)
    else:
        price = float(api.get_latest_trade(ticker).price)
    
    shares = round(balance * MAX_RISK_PER_TRADE / price, 3)
    
    positions = api.list_positions()
    has_position = any(p.symbol == ticker for p in positions)
    
    for p in positions:
        if p.symbol == ticker:
            st.session_state.daily_pnl = float(p.unrealized_pl)
    
    scalp_signal = None
    signal_strength = 0
    
    try:
        if crypto:
            bars = api.get_crypto_bars(ticker, '1Min', limit=20, exchanges=['CBSE']).df
        else:
            bars = api.get_bars(ticker, '1Min', limit=20).df
        
        if len(bars) >= 20:
            ema_5 = bars['close'].tail(5).mean()
            ema_10 = bars['close'].tail(10).mean()
            current_candle_change = (price - bars['close'].iloc[-2]) / bars['close'].iloc[-2] * 100
            avg_volume = bars['volume'].tail(10).mean()
            current_volume = bars['volume'].iloc[-1]
            volume_spike = current_volume > (avg_volume * 1.2)
            
            if price > ema_5 and ema_5 > ema_10 and current_candle_change > 0.05 and volume_spike:
                scalp_signal = "BUY"
                signal_strength = abs(current_candle_change)
            elif price < ema_5 and ema_5 < ema_10 and current_candle_change < -0.05 and volume_spike:
                scalp_signal = "SELL"
                signal_strength = abs(current_candle_change)
            
            if tier in [1, 2] and scalp_signal and not has_position:
                current_minute = now.strftime("%H:%M")
                if st.session_state.last_alert != current_minute:
                    st.session_state.last_alert = current_minute
                    alert_color = "#00FFA3" if scalp_signal == "BUY" else "#FF4B4B"
                    st.markdown(f"""
                    <div class="alert-box" style="border-color: {alert_color};">
                        <h2 style="color: {alert_color}; margin: 0;">⚡ SCALP ALERT: {scalp_signal}</h2>
                        <p style="color: white; margin: 5px 0;">Momentum: {signal_strength:.2f}%</p>
                        <p style="color: #808495; font-size: 12px; margin: 0;">Click {scalp_signal} now!</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            if tier == 3 and autopilot and st.session_state.daily_trades < 15 and (market_open or crypto):
                if has_position and st.session_state.daily_pnl < -(balance * 0.005):
                    api.close_position(ticker)
                    st.session_state.daily_trades += 1
                    st.session_state.autopilot_active = False
                    st.error("🛡️ STOP LOSS")
                elif has_position and st.session_state.daily_pnl > (balance * 0.005):
                    api.close_position(ticker)
                    st.session_state.daily_trades += 1
                    st.session_state.autopilot_active = False
                    st.success("✅ PROFIT TAKEN")
                elif scalp_signal == "BUY" and not has_position:
                    tif = 'gtc' if crypto else 'day'
                    api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force=tif)
                    st.session_state.daily_trades += 1
                    st.session_state.autopilot_active = True
                    st.success(f"🤖 AUTO BUY: {signal_strength:.2f}%")
                elif scalp_signal == "SELL" and has_position:
                    api.close_position(ticker)
                    st.session_state.daily_trades += 1
                    st.session_state.autopilot_active = False
                    st.success(f"🤖 AUTO SELL: {signal_strength:.2f}%")
            
            with st.sidebar:
                st.divider()
                st.markdown("### ⚡ SCALP SCAN")
                st.metric("1-Min Move", f"{current_candle_change:+.2f}%")
                st.metric("Volume", "🔥 HIGH" if volume_spike else "Normal")
                if scalp_signal:
                    st.success(f"🎯 {scalp_signal} SIGNAL")
                else:
                    st.info("⏳ Scanning...")
    except:
        pass
    
    col1, col2 = st.columns(2)
    col1.metric("Balance", f"${balance:.2f}")
    col2.metric("P&L", f"${st.session_state.daily_pnl:.2f}")
    
    st.markdown(f"### 🎯 {ticker}")
    st.markdown(f"## ${price:.2f}")
    st.caption(f"Size: {shares} shares")
    
    can_trade = (market_open or crypto) and st.session_state.daily_trades < 15
    
    col1, col2 = st.columns(2)
    
    if col1.button("🟢 BUY", disabled=not can_trade or has_position):
        tif = 'gtc' if crypto else 'day'
        api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force=tif)
        st.session_state.daily_trades += 1
        st.success("✅ BUY")
        time.sleep(1)
        st.rerun()
        
    if col2.button("🔴 SELL", disabled=not can_trade or not has_position):
        api.close_position(ticker)
        st.session_state.daily_trades += 1
        st.success("✅ SELL")
        time.sleep(1)
        st.rerun()
    
    st.divider()
    if st.button("📱 SHARE MY WINS"):
        st.session_state.show_share = not st.session_state.show_share
    
    if st.session_state.show_share:
        display_ticker = "BTC/USD" if ticker == "BTCUSD" else "ETH/USD" if ticker == "ETHUSD" else ticker
        st.code(f"""🌱 PROJECT HOPE 🌱
💰 ${balance:.2f}
📊 P&L: ${st.session_state.daily_pnl:+.2f}
🎯 {display_ticker}
⚡ {st.session_state.daily_trades}/15
#ProjectHope""")

except Exception as e:
    st.error(f"Error: {e}")
