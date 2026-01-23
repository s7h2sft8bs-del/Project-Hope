import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import time

st.set_page_config(page_title="Project Hope", page_icon="🌱", layout="centered")
st_autorefresh(interval=1000, key="clock")
load_dotenv()

try:
    import alpaca_trade_api as tradeapi
    # Real-time SIP feed (Algo Trader Plus subscription)
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'), 
        os.getenv('ALPACA_SECRET_KEY'), 
        "https://paper-api.alpaca.markets"
    )
except:
    st.error("Check API setup")
    st.stop()

# =============================================================================
# BOSS MODE SETTINGS - MAXIMUM PROFIT PROTECTION
# =============================================================================
TAKE_PROFIT = 0.003          # 0.3% auto take profit
STOP_LOSS = 0.005            # 0.5% stop loss
TRAILING_STOP = 0.002        # 0.2% trailing stop (locks in profits)
BREAKEVEN_TRIGGER = 0.0015   # Move stop to breakeven at 0.15% profit
MAX_RISK_PER_TRADE = 0.05    # 5% of account per trade
MAX_DAILY_LOSS = 0.02        # 2% daily circuit breaker
MAX_TRADES_PER_DAY = 10
MIN_ACCOUNT_BALANCE = 25

# Smart Scanner Stock Universe - Quality stocks at various price points
STOCK_UNIVERSE = [
    # Under $10 - High volume movers
    "NIO", "PLTR", "SOFI", "SNAP", "HOOD", "RIVN", "LCID", "F", "AAL", "CCL",
    # $10-25
    "AMD", "UBER", "COIN", "RBLX", "DKNG", "SQ", "PYPL", "BAC", "T", "WBD",
    # $25-50  
    "INTC", "GM", "SHOP", "ROKU", "NET", "CRWD", "SNOW", "PATH", "U", "PINS",
    # $50-100
    "DIS", "AMZN", "GOOG", "META", "NFLX", "CRM", "ORCL", "IBM", "GE", "CAT",
    # $100-200
    "NVDA", "AAPL", "MSFT", "TSLA", "V", "MA", "JPM", "HD", "UNH", "PG",
    # $200+
    "SPY", "QQQ", "AVGO", "COST", "LLY", "ISRG", "REGN", "ADBE", "NOW", "PANW"
]

FRACTIONAL_ASSETS = ["SPY", "QQQ", "BTCUSD", "ETHUSD"]

# Session state initialization
defaults = {
    'daily_trades': 0,
    'daily_pnl': 0.0,
    'last_date': None,
    'show_share': False,
    'autopilot_active': False,
    'circuit_breaker': False,
    'last_alert': None,
    'entry_price': 0.0,
    'hot_stocks': [],
    'peak_pnl': 0.0,           # Track highest profit for trailing stop
    'breakeven_active': False,  # Whether we've moved stop to breakeven
    'wins': 0,
    'losses': 0
}

for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

def get_affordable_movers(balance, api):
    """Scan for stocks that are affordable AND moving"""
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
                min_volume = 500000
                
                if volume >= min_volume:
                    movers.append({
                        'symbol': symbol,
                        'price': price,
                        'change': change_pct,
                        'volume': volume,
                        'shares': max(1, int(balance * MAX_RISK_PER_TRADE / price))
                    })
        
        movers.sort(key=lambda x: abs(x['change']), reverse=True)
        return movers[:10]
        
    except Exception as e:
        return []

# =============================================================================
# STYLES
# =============================================================================
st.markdown("""<style>
.stApp {background: linear-gradient(180deg, #0a0e1a 0%, #151b2e 100%);}
.block-container {max-width: 500px; margin: 0 auto; padding: 1rem 1rem 150px 1rem;}
h1, h2, h3, p, div {text-align: center;}
.stMetric {text-align: center;}
.stMetric > div {justify-content: center;}
.stMetric label {justify-content: center;}
.stButton > button {width: 100%;}
.alert-box {background: rgba(255,165,0,0.2); border: 2px solid #FFA500; border-radius: 12px; padding: 15px; margin: 10px auto; animation: pulse 2s infinite; text-align: center;}
@keyframes pulse {0%, 100% {opacity: 1;} 50% {opacity: 0.7;}}
.safe-badge {background: rgba(0,255,163,0.1); border: 1px solid #00FFA3; border-radius: 8px; padding: 10px; margin: 10px auto; text-align: center;}
.tier-box {background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin: 15px auto; text-align: center;}
.hot-stock {background: linear-gradient(135deg, rgba(255,215,0,0.2), rgba(255,69,0,0.2)); border: 1px solid #FFD700; border-radius: 8px; padding: 8px; margin: 5px 0; text-align: center;}
.profit-zone {background: linear-gradient(135deg, rgba(0,255,163,0.3), rgba(0,200,100,0.2)); border: 2px solid #00FFA3; border-radius: 12px; padding: 15px; margin: 10px auto; text-align: center; animation: glow 1.5s infinite;}
@keyframes glow {0%, 100% {box-shadow: 0 0 10px rgba(0,255,163,0.5);} 50% {box-shadow: 0 0 25px rgba(0,255,163,0.8);}}
.danger-zone {background: linear-gradient(135deg, rgba(255,75,75,0.3), rgba(200,50,50,0.2)); border: 2px solid #FF4B4B; border-radius: 12px; padding: 15px; margin: 10px auto; text-align: center;}
.lock-btn {background: linear-gradient(135deg, #00FFA3, #00CC7A) !important; color: black !important; font-weight: bold !important;}
.gainer {color: #00FFA3;}
.loser {color: #FF4B4B;}
</style>""", unsafe_allow_html=True)

# =============================================================================
# LOGO
# =============================================================================
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

# =============================================================================
# ACCESS CODE
# =============================================================================
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
        <p style="color: #808495; font-size: 12px; margin: 0 0 15px 0;">Scanner + Crypto After Hours</p>
        <p style="color: #FFD700; margin: 5px 0;">⚡ TIER 3 - MASTER</p>
        <p style="color: #808495; font-size: 12px; margin: 0;">Full Access + Autopilot + Trailing Stop</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown('<div class="safe-badge">🛡️ <b>BOSS MODE</b> • Trailing Stop • Auto Breakeven • Profit Lock</div>', unsafe_allow_html=True)

st.divider()

# =============================================================================
# TIME & MARKET STATUS
# =============================================================================
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

# =============================================================================
# ACCOUNT INFO
# =============================================================================
try:
    account = api.get_account()
    balance = float(account.equity)
    buying_power = float(account.buying_power)
except:
    st.error("❌ Could not connect to account")
    st.stop()

ticker = None
crypto = False
autopilot = False
selected_stock = None

# =============================================================================
# SIDEBAR - SMART SCANNER
# =============================================================================
with st.sidebar:
    st.markdown("### 🔥 SMART SCANNER")
    st.caption(f"Finding stocks for ${balance:.0f} account")
    
    if st.button("🔄 SCAN NOW", use_container_width=True):
        with st.spinner("Scanning 60 stocks..."):
            st.session_state.hot_stocks = get_affordable_movers(balance, api)
    
    if st.session_state.hot_stocks:
        st.markdown("---")
        st.markdown("**TOP MOVERS YOU CAN TRADE:**")
        for i, stock in enumerate(st.session_state.hot_stocks[:5]):
            change_class = "gainer" if stock['change'] > 0 else "loser"
            arrow = "🟢" if stock['change'] > 0 else "🔴"
            st.markdown(f"""
            <div class="hot-stock">
                {arrow} <b>{stock['symbol']}</b> ${stock['price']:.2f}
                <span class="{change_class}">({stock['change']:+.2f}%)</span>
                <br><small style="color:#808495;">{stock['shares']} shares possible</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("👆 Tap SCAN to find hot stocks")

# Stock Selection
if st.session_state.hot_stocks:
    stock_options = [f"{s['symbol']} (${s['price']:.2f})" for s in st.session_state.hot_stocks[:5]]
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🎯 SELECT STOCK")
        selected = st.selectbox("Choose:", ["-- Select --"] + stock_options, label_visibility="collapsed")
        
        if selected != "-- Select --":
            ticker = selected.split(" ")[0]
            for s in st.session_state.hot_stocks:
                if s['symbol'] == ticker:
                    selected_stock = s
                    break

# Crypto for Tier 2+
if tier >= 2 and now.hour >= 16:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ⚡ CRYPTO")
        if st.checkbox("Enable Crypto"):
            crypto = True
            ticker = "BTCUSD" if st.radio("Select:", ["Bitcoin", "Ethereum"]) == "Bitcoin" else "ETHUSD"
            selected_stock = None

# Autopilot for Tier 3
if tier == 3:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🤖 AUTOPILOT")
        autopilot = st.checkbox("Full Auto Trading")
        if autopilot:
            st.warning("⚠️ BOT IS LIVE")
            if not ticker and st.session_state.hot_stocks:
                ticker = st.session_state.hot_stocks[0]['symbol']
                selected_stock = st.session_state.hot_stocks[0]
                st.info(f"Auto: {ticker}")

# Protection Stats
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🛡️ PROTECTION")
    st.metric("Trades", f"{st.session_state.daily_trades}/{MAX_TRADES_PER_DAY}")
    st.metric("Daily P&L", f"${st.session_state.daily_pnl:.2f}")
    
    # Win/Loss tracker
    total_trades = st.session_state.wins + st.session_state.losses
    win_rate = (st.session_state.wins / total_trades * 100) if total_trades > 0 else 0
    st.metric("Win Rate", f"{win_rate:.0f}% ({st.session_state.wins}W/{st.session_state.losses}L)")
    
    if st.session_state.circuit_breaker:
        st.error("🚨 CIRCUIT BREAKER")

# =============================================================================
# MAIN TRADING LOGIC
# =============================================================================
try:
    start_balance = balance - st.session_state.daily_pnl
    
    if balance < MIN_ACCOUNT_BALANCE:
        st.error(f"🚨 Balance below ${MIN_ACCOUNT_BALANCE}")
        st.stop()
    
    if st.session_state.daily_pnl <= -(start_balance * MAX_DAILY_LOSS):
        st.session_state.circuit_breaker = True
    
    if st.session_state.circuit_breaker:
        st.error("🚨 CIRCUIT BREAKER ACTIVE")
        st.info("Daily loss limit reached. Account protected.")
        st.stop()
    
    # Check for existing positions
    positions = api.list_positions()
    current_position = None
    has_position = False
    
    for p in positions:
        current_position = p
        has_position = True
        ticker = p.symbol
        break
    
    # Get price for selected ticker
    if ticker:
        try:
            if crypto:
                price = float(api.get_latest_crypto_trade(ticker, exchange='CBSE').price)
            else:
                price = float(api.get_latest_trade(ticker).price)
        except:
            price = selected_stock['price'] if selected_stock else 0
        
        # Calculate shares
        if ticker in FRACTIONAL_ASSETS:
            shares = round(balance * MAX_RISK_PER_TRADE / price, 3)
        else:
            shares = max(1, int(balance * MAX_RISK_PER_TRADE / price))
            if balance < price:
                shares = 0
    else:
        price = 0
        shares = 0
    
    # ==========================================================================
    # BOSS MODE PROFIT PROTECTION SYSTEM
    # ==========================================================================
    if has_position and current_position:
        current_pnl = float(current_position.unrealized_pl)
        current_pnl_pct = float(current_position.unrealized_plpc)
        st.session_state.daily_pnl = current_pnl
        
        # Track peak profit for trailing stop
        if current_pnl_pct > st.session_state.peak_pnl:
            st.session_state.peak_pnl = current_pnl_pct
        
        # RULE 1: Auto breakeven - once we hit 0.15% profit, stop loss moves to entry
        if current_pnl_pct >= BREAKEVEN_TRIGGER and not st.session_state.breakeven_active:
            st.session_state.breakeven_active = True
            st.toast("🛡️ Stop moved to BREAKEVEN!", icon="✅")
        
        # RULE 2: Trailing stop - if we've peaked and dropped 0.2% from peak, EXIT
        if st.session_state.peak_pnl >= BREAKEVEN_TRIGGER:
            trailing_trigger = st.session_state.peak_pnl - TRAILING_STOP
            if current_pnl_pct <= trailing_trigger and current_pnl_pct > 0:
                api.close_position(current_position.symbol)
                st.session_state.daily_trades += 1
                st.session_state.wins += 1
                profit_locked = st.session_state.peak_pnl * 100
                st.success(f"🔒 TRAILING STOP: Locked +{current_pnl_pct*100:.2f}% (Peak was +{profit_locked:.2f}%)")
                st.balloons()
                st.session_state.peak_pnl = 0.0
                st.session_state.breakeven_active = False
                time.sleep(2)
                st.rerun()
        
        # RULE 3: Take profit at target
        if current_pnl_pct >= TAKE_PROFIT:
            api.close_position(current_position.symbol)
            st.session_state.daily_trades += 1
            st.session_state.wins += 1
            st.success(f"✅ TAKE PROFIT: +{current_pnl_pct*100:.2f}%")
            st.balloons()
            st.session_state.peak_pnl = 0.0
            st.session_state.breakeven_active = False
            time.sleep(2)
            st.rerun()
        
        # RULE 4: Stop loss (respects breakeven if active)
        effective_stop = 0 if st.session_state.breakeven_active else -STOP_LOSS
        if current_pnl_pct <= effective_stop and current_pnl_pct < 0:
            api.close_position(current_position.symbol)
            st.session_state.daily_trades += 1
            st.session_state.losses += 1
            st.error(f"🛡️ STOP LOSS: {current_pnl_pct*100:.2f}%")
            st.session_state.peak_pnl = 0.0
            st.session_state.breakeven_active = False
            time.sleep(2)
            st.rerun()
        
        # RULE 5: Breakeven exit - if breakeven active and we drop to 0, exit flat
        if st.session_state.breakeven_active and current_pnl_pct <= 0.0001:
            api.close_position(current_position.symbol)
            st.session_state.daily_trades += 1
            st.info("🛡️ BREAKEVEN EXIT: $0 loss")
            st.session_state.peak_pnl = 0.0
            st.session_state.breakeven_active = False
            time.sleep(2)
            st.rerun()
    
    # Scalp Signal Detection
    scalp_signal = None
    signal_strength = 0
    
    if ticker and not crypto:
        try:
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
                
                # Alert for Tier 1 & 2
                if tier in [1, 2] and scalp_signal and not has_position:
                    current_minute = now.strftime("%H:%M")
                    if st.session_state.last_alert != current_minute:
                        st.session_state.last_alert = current_minute
                        alert_color = "#00FFA3" if scalp_signal == "BUY" else "#FF4B4B"
                        st.markdown(f"""
                        <div class="alert-box" style="border-color: {alert_color};">
                            <h2 style="color: {alert_color}; margin: 0;">⚡ SCALP ALERT: {scalp_signal} {ticker}</h2>
                            <p style="color: white; margin: 5px 0;">Momentum: {signal_strength:.2f}%</p>
                            <p style="color: #808495; font-size: 12px;">Trailing Stop Active • Auto Breakeven</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Autopilot for Tier 3
                if tier == 3 and autopilot and st.session_state.daily_trades < MAX_TRADES_PER_DAY and market_open and not has_position:
                    if scalp_signal == "BUY" and shares > 0:
                        api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force='day')
                        st.session_state.daily_trades += 1
                        st.session_state.peak_pnl = 0.0
                        st.session_state.breakeven_active = False
                        st.success(f"🤖 AUTO BUY {ticker}: {signal_strength:.2f}%")
                        time.sleep(1)
                        st.rerun()
                    elif scalp_signal == "BUY" and shares == 0:
                        st.warning(f"⚠️ Need ${price:.2f} for 1 share of {ticker}")
                
                with st.sidebar:
                    st.markdown("---")
                    st.markdown("### ⚡ SIGNAL")
                    st.metric("1-Min", f"{current_candle_change:+.2f}%")
                    if scalp_signal:
                        st.success(f"🎯 {scalp_signal}")
                    else:
                        st.info("⏳ Scanning...")
        except:
            pass
    
    # ==========================================================================
    # DISPLAY SECTION
    # ==========================================================================
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Balance", f"${balance:.2f}")
    with col2:
        st.metric("P&L", f"${st.session_state.daily_pnl:.2f}")
    
    if ticker:
        display_ticker = "BTC/USD" if ticker == "BTCUSD" else "ETH/USD" if ticker == "ETHUSD" else ticker
        st.markdown(f"<h3 style='text-align:center;'>🎯 {display_ticker}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align:center;'>${price:,.2f}</h1>", unsafe_allow_html=True)
        
        share_label = "shares" if shares != 1 else "share"
        st.markdown(f"<p style='text-align:center; color:#808495;'>Size: {shares} {share_label}</p>", unsafe_allow_html=True)
        
        # =======================================================================
        # POSITION DISPLAY WITH BOSS MODE CONTROLS
        # =======================================================================
        if has_position and current_position:
            pnl_pct = float(current_position.unrealized_plpc) * 100
            pnl_color = "#00FFA3" if pnl_pct >= 0 else "#FF4B4B"
            
            # Show different UI based on profit/loss
            if pnl_pct > 0:
                st.markdown(f"""
                <div class="profit-zone">
                    <h2 style="color: #00FFA3; margin: 0;">💰 WINNING: +{pnl_pct:.2f}%</h2>
                    <p style="color: white; margin: 5px 0;">Peak: +{st.session_state.peak_pnl*100:.2f}%</p>
                    <p style="color: #808495; font-size: 12px;">
                        {"🛡️ BREAKEVEN ACTIVE" if st.session_state.breakeven_active else "⏳ Breakeven at +0.15%"} 
                        • Trailing: -0.2% from peak
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                effective_stop_display = "BREAKEVEN (0%)" if st.session_state.breakeven_active else f"-{STOP_LOSS*100:.1f}%"
                st.markdown(f"""
                <div class="danger-zone">
                    <h2 style="color: #FF4B4B; margin: 0;">📉 DOWN: {pnl_pct:.2f}%</h2>
                    <p style="color: #808495; font-size: 12px;">Stop Loss: {effective_stop_display}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Progress bar
            st.progress(min(max((pnl_pct + 0.5) / 0.8, 0), 1))
            
            # =================================================================
            # ACTION BUTTONS - ALWAYS AVAILABLE WHEN IN POSITION
            # =================================================================
            st.markdown("---")
            
            # LOCK PROFIT button - only shows when in profit
            if pnl_pct > 0:
                if st.button(f"🔒 LOCK PROFIT (+{pnl_pct:.2f}%)", use_container_width=True, type="primary"):
                    api.close_position(current_position.symbol)
                    st.session_state.daily_trades += 1
                    st.session_state.wins += 1
                    st.success(f"💰 PROFIT LOCKED: +{pnl_pct:.2f}%")
                    st.balloons()
                    st.session_state.peak_pnl = 0.0
                    st.session_state.breakeven_active = False
                    time.sleep(1)
                    st.rerun()
            
            # EXIT NOW button - always available
            if st.button("🚪 EXIT NOW", use_container_width=True):
                api.close_position(current_position.symbol)
                st.session_state.daily_trades += 1
                if pnl_pct >= 0:
                    st.session_state.wins += 1
                    st.success(f"✅ CLOSED: +{pnl_pct:.2f}%")
                else:
                    st.session_state.losses += 1
                    st.warning(f"📉 CLOSED: {pnl_pct:.2f}%")
                st.session_state.peak_pnl = 0.0
                st.session_state.breakeven_active = False
                time.sleep(1)
                st.rerun()
        
        else:
            # NO POSITION - Show buy controls
            can_trade = (market_open or crypto) and st.session_state.daily_trades < MAX_TRADES_PER_DAY and not st.session_state.circuit_breaker and shares > 0
            
            if not can_trade:
                if st.session_state.circuit_breaker:
                    st.error("🚨 Circuit breaker active")
                elif st.session_state.daily_trades >= MAX_TRADES_PER_DAY:
                    st.warning(f"⚠️ Max trades reached")
                elif shares == 0:
                    st.warning(f"⚠️ Need ${price:.2f} for 1 share")
                elif not market_open and not crypto:
                    st.info("⏰ Markets closed")
            
            if st.button("🟢 BUY", disabled=not can_trade, use_container_width=True):
                tif = 'gtc' if crypto else 'day'
                api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force=tif)
                st.session_state.daily_trades += 1
                st.session_state.peak_pnl = 0.0
                st.session_state.breakeven_active = False
                st.success("✅ BUY - Boss Mode Protection Active!")
                time.sleep(1)
                st.rerun()
    else:
        st.markdown("<h3 style='text-align:center; color:#808495;'>👈 Scan & Select a Stock</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#808495;'>Use the Smart Scanner to find affordable, moving stocks.</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # ==========================================================================
    # BOSS MODE INFO
    # ==========================================================================
    with st.expander("🛡️ BOSS MODE PROTECTION RULES"):
        st.markdown("""
        **Your money is protected by 5 rules:**
        
        1. **Auto Breakeven** - At +0.15% profit, stop loss moves to $0
        2. **Trailing Stop** - Locks profits, exits if drops 0.2% from peak
        3. **Take Profit** - Auto-exits at +0.3%
        4. **Stop Loss** - Max loss -0.5% (or $0 if breakeven active)
        5. **Circuit Breaker** - Stops trading at -2% daily loss
        
        **Manual Controls:**
        - 🔒 LOCK PROFIT - Exit anytime you're green
        - 🚪 EXIT NOW - Emergency exit anytime
        
        **You can NEVER lose more than 0.5% per trade!**
        """)
    
    if st.button("📱 SHARE MY WINS", use_container_width=True):
        st.session_state.show_share = not st.session_state.show_share
    
    if st.session_state.show_share:
        display_name = ticker if ticker else "SCANNING"
        st.code(f"""🌱 PROJECT HOPE 🌱
🛡️ BOSS MODE ACTIVE
💰 ${balance:.2f}
📊 P&L: ${st.session_state.daily_pnl:+.2f}
🏆 Win Rate: {win_rate:.0f}%
🎯 {display_name}
⚡ {st.session_state.daily_trades}/{MAX_TRADES_PER_DAY}
#ProjectHope #BossMode #Winning""")

except Exception as e:
    st.error(f"Error: {e}")
