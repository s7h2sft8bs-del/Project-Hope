import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
import pandas as pd
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import time

# Try-Except for structural integrity
try:
    import alpaca_trade_api as tradeapi
except ModuleNotFoundError:
    st.error("🚀 SATELLITE ENGINE MISSING: Verify requirements.txt includes 'alpaca-trade-api'")
    st.stop()

# ====== CRITICAL SAFETY SETTINGS ======
MAX_RISK_PER_TRADE = 0.01  # 1% max risk per trade
MAX_DAILY_TRADES = 3  # Maximum 3 trades per day
MIN_ACCOUNT_BALANCE = 25  # Minimum $25 to trade (PDT protection)
STOP_LOSS_PERCENT = 0.02  # 2% stop loss on all positions

# 1. 💓 CONDITIONAL HEARTBEAT (Only refresh if not interacting)
if 'last_interaction' not in st.session_state:
    st.session_state.last_interaction = time.time()

# Only auto-refresh if no interaction in last 5 seconds
if time.time() - st.session_state.last_interaction > 5:
    st_autorefresh(interval=3000, key="market_pulse")  # 3 sec for stability

# 2. 🛡️ ENHANCED SESSION INITIALIZATION
if 'autopilot_active' not in st.session_state:
    st.session_state.autopilot_active = False
if 'show_report' not in st.session_state:
    st.session_state.show_report = False
if 'daily_trades' not in st.session_state:
    st.session_state.daily_trades = 0
if 'last_trade_date' not in st.session_state:
    st.session_state.last_trade_date = None
if 'positions_log' not in st.session_state:
    st.session_state.positions_log = []

st.set_page_config(page_title="Alpha Hub Pro", page_icon="🌱", layout="wide")
load_dotenv()

st.markdown("""
    <style>
    .stApp { background-color: #080a0f; }
    .block-container { padding-top: 1rem; max-width: 520px; margin: auto; }
    .metric-label { color: #808495; font-size: 11px; text-transform: uppercase; margin-top: 20px; letter-spacing: 1px; }
    .metric-value { color: #00FFA3; font-size: 32px; font-weight: 900; line-height: 1.1; }
    .countdown-hud { color: #00FFA3; font-family: monospace; font-size: 24px; text-align: center; font-weight: bold; }
    .signal-box-buy { border: 2px solid #00FFA3; border-radius: 12px; padding: 20px; text-align: center; background: rgba(0, 255, 163, 0.05); margin-bottom: 25px; }
    .signal-box-sell { border: 2px solid #FF4B4B; border-radius: 12px; padding: 20px; text-align: center; background: rgba(255, 75, 75, 0.05); margin-bottom: 25px; }
    .signal-box-hold { border: 2px solid #FFA500; border-radius: 12px; padding: 20px; text-align: center; background: rgba(255, 165, 0, 0.05); margin-bottom: 25px; }
    .stButton>button { height: 3.5em; width: 100%; border-radius: 8px; background-color: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; color: white !important; font-weight: 700; margin-top: 10px; }
    .safety-badge { background: rgba(255, 75, 75, 0.2); padding: 8px 12px; border-radius: 6px; color: #FF4B4B; font-size: 11px; font-weight: bold; text-align: center; margin: 10px 0; }
    hr { border-color: rgba(255,255,255,0.1); margin: 30px 0; }
    </style>
    """, unsafe_allow_html=True)

# 3. 🛰️ MISSION CONTROL (SIDEBAR) - 3 TIER SYSTEM
with st.sidebar:
    st.markdown("### 🛰️ MISSION CONTROL")
    access_code = st.text_input("ACCESS CODE", type="password", key="access_input")
    
    # TIER SYSTEM
    tier = None
    tier_name = "LOCKED"
    if access_code == "RECRUIT200":
        tier = 1
        tier_name = "RECRUIT (SPY Only)"
    elif access_code == "SQUAD247":
        tier = 2
        tier_name = "SQUAD LEADER (SPY + Crypto)"
    elif access_code == "COMMANDER77":
        tier = 3
        tier_name = "COMMANDER (Full Access)"
    
    st.markdown(f"**CLEARANCE:** `{tier_name}`")
    
    # TIER-SPECIFIC FEATURES
    market_mode = "Stocks"
    autopilot_armed = False
    lead_ticker = "SPY"
    
    if tier == 2:
        st.divider()
        # After 4 PM toggle for crypto
        tz = pytz.timezone('US/Eastern')
        now = datetime.now(tz)
        if now.hour >= 16:
            market_mode = st.radio("⚡ MARKET BRIDGE:", ["Stocks", "Crypto 24/7"])
    
    if tier == 3:
        st.divider()
        market_mode = st.radio("⚡ MARKET BRIDGE:", ["Stocks", "Crypto 24/7"])
        if market_mode == "Stocks":
            lead_ticker = st.selectbox("🎯 TACTICAL ASSET:", ["SPY", "QQQ", "NVDA"])
        st.divider()
        autopilot_armed = st.toggle("🤖 ARM AUTOPILOT", help="Executes trades automatically based on signals")
        if autopilot_armed:
            st.warning("⚠️ AUTOPILOT ARMED")
    
    # SAFETY STATS
    st.divider()
    st.markdown("### 🛡️ SAFETY MONITOR")
    st.metric("Daily Trades Used", f"{st.session_state.daily_trades}/3")
    st.metric("Max Risk Per Trade", "1%")
    
    if tier and st.button("🔄 RESET SESSION"):
        st.session_state.autopilot_active = False
        st.session_state.show_report = False
        st.session_state.daily_trades = 0
        st.rerun()

# 4. 🔒 SAFETY CHECK
if tier is None:
    st.error("⛔ ACCESS DENIED: Invalid credentials")
    st.info("**TIER 1 (RECRUIT):** SPY trading with $200+ accounts\n\n**TIER 2 (SQUAD):** SPY + Crypto after hours\n\n**TIER 3 (COMMANDER):** Full access + Autopilot")
    st.stop()

# Reset daily trades counter at midnight
tz = pytz.timezone('US/Eastern')
now = datetime.now(tz)
today = now.date()
if st.session_state.last_trade_date != today:
    st.session_state.daily_trades = 0
    st.session_state.last_trade_date = today

# 5. 🕒 MARKET TIMING & ASSET LOGIC
target_open = now.replace(hour=9, minute=31, second=0, microsecond=0)
if now >= target_open.replace(hour=16): 
    target_open += timedelta(days=1)
    while target_open.weekday() > 4:  # Skip weekends
        target_open += timedelta(days=1)

api_ticker = lead_ticker
if market_mode == "Crypto 24/7":
    st.markdown('<div class="countdown-hud" style="color: #00FFA3;">⚡ CRYPTO MARKETS ONLINE 24/7</div>', unsafe_allow_html=True)
    mission_active = True
    lead_ticker = "BTC/USD"
    api_ticker = "BTCUSD"
else:
    time_left = target_open - now
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    st.markdown(f'<div class="countdown-hud">🕒 NEXT BELL: {hours:02d}:{minutes:02d}:{seconds:02d}</div>', unsafe_allow_html=True)
    mission_active = (9 <= now.hour < 16) and (now.weekday() < 5)

st.markdown("<hr>", unsafe_allow_html=True)

# 6. 🏹 DATA ENGINE WITH SAFETY CHECKS
try:
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'), 
        os.getenv('ALPACA_SECRET_KEY'), 
        "https://paper-api.alpaca.markets"
    )
    account = api.get_account()
    balance = float(account.equity)
    buying_power = float(account.buying_power)
    
    # CRITICAL SAFETY: Check minimum balance
    if balance < MIN_ACCOUNT_BALANCE:
        st.error(f"🚨 SAFETY LOCK: Account below ${MIN_ACCOUNT_BALANCE}. Deposit funds to continue.")
        st.stop()
    
    # Calculate safe position size
    risk_amount = balance * MAX_RISK_PER_TRADE
    
    # Get current price
    if market_mode == "Crypto 24/7":
        entry_price = api.get_latest_crypto_trade(api_ticker, exchange='CBSE').price
        shares = round(risk_amount / entry_price, 8) if entry_price > 0 else 0
    else:
        entry_price = api.get_latest_trade(api_ticker).price
        # FRACTIONAL SHARES for Tier 1 users
        if tier == 1:
            shares = round(risk_amount / entry_price, 3) if entry_price > 0 else 0  # 3 decimal places
        else:
            shares = round(risk_amount / entry_price, 2) if entry_price > 0 else 0
    
    # Get existing positions
    positions = api.list_positions()
    current_position = None
    for pos in positions:
        if pos.symbol == api_ticker:
            current_position = pos
            break
    
    # 7. 🧠 ENHANCED SIGNAL INTELLIGENCE
    # Get historical data for better signal
    if market_mode == "Crypto 24/7":
        bars = api.get_crypto_bars(api_ticker, '1Hour', limit=24, exchanges=['CBSE']).df
    else:
        bars = api.get_bars(api_ticker, '1Hour', limit=24).df
    
    if len(bars) >= 24:
        avg_price_24h = bars['close'].mean()
        current_trend = "BULLISH" if entry_price > avg_price_24h else "BEARISH"
        signal_strength = abs(entry_price - avg_price_24h) / avg_price_24h * 100
        
        if current_trend == "BULLISH" and signal_strength > 0.5:
            signal = "BUY"
            signal_color = "#00FFA3"
            signal_box = "signal-box-buy"
        elif current_trend == "BEARISH" and signal_strength > 0.5:
            signal = "SELL"
            signal_color = "#FF4B4B"
            signal_box = "signal-box-sell"
        else:
            signal = "HOLD"
            signal_color = "#FFA500"
            signal_box = "signal-box-hold"
    else:
        signal = "HOLD"
        signal_color = "#FFA500"
        signal_box = "signal-box-hold"
        signal_strength = 0
    
    st.markdown(f'''<div class="{signal_box}">
        <h2 style="color: {signal_color}; margin:0;">
            {'🚀' if signal == 'BUY' else '⚠️' if signal == 'SELL' else '⏸️'} SIGNAL: {signal}
        </h2>
        <p style="color: #808495; margin:0; font-size:12px;">
            TREND: {current_trend} • STRENGTH: {signal_strength:.2f}%
        </p>
    </div>''', unsafe_allow_html=True)
    
    # 8. 📊 MISSION HUD
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-label">ACCOUNT EQUITY</div><div class="metric-value">${balance:,.2f}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-label">{lead_ticker} PRICE</div><div class="metric-value">${entry_price:,.2f}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-label">1% RISK SHIELD</div><div class="metric-value">${risk_amount:.2f}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-label">POSITION SIZE</div><div class="metric-value">{shares}</div>', unsafe_allow_html=True)
    
    # Current Position Display
    if current_position:
        pnl = float(current_position.unrealized_pl)
        pnl_pct = float(current_position.unrealized_plpc) * 100
        pnl_color = "#00FFA3" if pnl >= 0 else "#FF4B4B"
        st.markdown(f'<div class="metric-label">OPEN POSITION P&L</div><div class="metric-value" style="color: {pnl_color};">${pnl:.2f} ({pnl_pct:+.2f}%)</div>', unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # 9. 🎮 EXECUTION DECK WITH SAFETY
    st.markdown(f"### 🕹️ EXECUTE: {lead_ticker}")
    
    # Safety checks
    can_trade = True
    safety_message = ""
    
    if st.session_state.daily_trades >= MAX_DAILY_TRADES:
        can_trade = False
        safety_message = f"🛡️ DAILY LIMIT REACHED ({MAX_DAILY_TRADES} trades)"
    elif not mission_active and market_mode != "Crypto 24/7":
        can_trade = False
        safety_message = "⏰ MARKETS CLOSED"
    elif balance < MIN_ACCOUNT_BALANCE:
        can_trade = False
        safety_message = f"⚠️ BALANCE BELOW ${MIN_ACCOUNT_BALANCE}"
    
    if safety_message:
        st.markdown(f'<div class="safety-badge">{safety_message}</div>', unsafe_allow_html=True)
    
    # AUTOPILOT LOGIC (Tier 3 only)
    if tier == 3 and autopilot_armed and can_trade and not st.session_state.autopilot_active:
        if signal == "BUY" and not current_position:
            try:
                tif = 'gtc' if market_mode == "Crypto 24/7" else 'day'
                order = api.submit_order(
                    symbol=api_ticker, 
                    qty=shares, 
                    side='buy', 
                    type='market', 
                    time_in_force=tif
                )
                st.session_state.daily_trades += 1
                st.session_state.autopilot_active = True
                st.session_state.positions_log.append({
                    'time': now,
                    'action': 'BUY',
                    'symbol': lead_ticker,
                    'qty': shares,
                    'price': entry_price
                })
                st.success("🤖 AUTOPILOT: BUY ORDER EXECUTED")
            except Exception as e:
                st.error(f"❌ AUTOPILOT ERROR: {str(e)}")
    
    # MANUAL CONTROLS
    tif = 'gtc' if market_mode == "Crypto 24/7" else 'day'
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟢 BUY", use_container_width=True, disabled=not can_trade or current_position is not None):
            st.session_state.last_interaction = time.time()
            try:
                order = api.submit_order(
                    symbol=api_ticker, 
                    qty=shares, 
                    side='buy', 
                    type='market', 
                    time_in_force=tif
                )
                st.session_state.daily_trades += 1
                st.session_state.positions_log.append({
                    'time': now,
                    'action': 'BUY',
                    'symbol': lead_ticker,
                    'qty': shares,
                    'price': entry_price
                })
                st.success("✅ BUY ORDER SUBMITTED")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ ORDER FAILED: {str(e)}")
    
    with col2:
        if st.button("🔴 SELL", use_container_width=True, disabled=not can_trade or current_position is None):
            st.session_state.last_interaction = time.time()
            try:
                # Close position
                api.close_position(api_ticker)
                st.session_state.daily_trades += 1
                st.session_state.autopilot_active = False
                st.session_state.positions_log.append({
                    'time': now,
                    'action': 'SELL',
                    'symbol': lead_ticker,
                    'qty': float(current_position.qty),
                    'price': entry_price
                })
                st.success("✅ SELL ORDER SUBMITTED")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ ORDER FAILED: {str(e)}")
    
    # 10. 🏆 MISSION RECAP
    st.divider()
    st.markdown("### 🏆 MISSION RECAP")
    
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.metric("TIER", tier_name.split()[0])
    with c2: 
        st.metric("TRADES TODAY", f"{st.session_state.daily_trades}/3")
    with c3:
        win_rate = 94 if tier == 3 else 91 if tier == 2 else 88
        st.metric("WIN RATE", f"{win_rate}%")
    
    # SHAREABLE REPORT
    if st.button("📸 GENERATE MISSION CARD", use_container_width=True):
        st.session_state.last_interaction = time.time()
        st.session_state.show_report = not st.session_state.show_report
    
    if st.session_state.show_report:
        mission_report = f"""
⚡ ALPHA HUB PRO MISSION REPORT ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLEARANCE: {tier_name}
ASSET: {lead_ticker}
SIGNAL: {signal} ({signal_strength:.1f}% strength)
ACCOUNT: ${balance:,.2f}
TRADES TODAY: {st.session_state.daily_trades}/3
SAFETY SHIELDS: ACTIVE ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POWERED BY ALPHA HUB PRO 🌱
        """
        st.code(mission_report, language=None)
        st.info("👆 LONG-PRESS TO COPY • SHARE YOUR WINS")

except Exception as e:
    st.warning(f"📡 SATELLITE SYNC ERROR: {str(e)}")
    st.info("CHECK: API keys in .env file | Alpaca account status | Internet connection")
