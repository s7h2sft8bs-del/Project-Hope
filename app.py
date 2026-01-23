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
    api = tradeapi.REST(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'), "https://paper-api.alpaca.markets")
except:
    st.error("Check API setup")
    st.stop()

TAKE_PROFIT = 0.003
STOP_LOSS = 0.005
MAX_RISK_PER_TRADE = 0.05  # Increased to 5% for small accounts
MAX_DAILY_LOSS = 0.02
MAX_TRADES_PER_DAY = 10
MIN_ACCOUNT_BALANCE = 25

# Smart Scanner Stock Universe - Quality stocks at various price points
STOCK_UNIVERSE = [
    # Under $10
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

# Assets that support fractional shares
FRACTIONAL_ASSETS = ["SPY", "QQQ", "BTCUSD", "ETHUSD"]

for key in ['daily_trades', 'daily_pnl', 'last_date', 'show_share', 'autopilot_active', 'circuit_breaker', 'last_alert', 'entry_price', 'hot_stocks']:
    if key not in st.session_state:
        st.session_state[key] = 0.0 if 'pnl' in key or 'price' in key else 0 if 'trades' in key else None if 'date' in key or 'alert' in key else [] if 'hot' in key else False

def get_affordable_movers(balance, api):
    """Scan for stocks that are affordable AND moving"""
    max_price = balance * 0.9  # Can afford with 90% of balance
    movers = []
    
    try:
        # Get snapshots for all stocks in universe
        snapshots = api.get_snapshots(STOCK_UNIVERSE)
        
        for symbol, snapshot in snapshots.items():
            if snapshot and snapshot.daily_bar:
                price = snapshot.latest_trade.price if snapshot.latest_trade else snapshot.daily_bar.close
                
                # Skip if can't afford at least 1 share
                if price > max_price or price < 1:
                    continue
                
                # Calculate daily change %
                prev_close = snapshot.prev_daily_bar.close if snapshot.prev_daily_bar else snapshot.daily_bar.open
                if prev_close > 0:
                    change_pct = ((price - prev_close) / prev_close) * 100
                else:
                    continue
                
                # Get volume info
                volume = snapshot.daily_bar.volume if snapshot.daily_bar else 0
                min_volume = 500000  # Minimum 500K volume for liquidity
                
                if volume >= min_volume:
                    movers.append({
                        'symbol': symbol,
                        'price': price,
                        'change': change_pct,
                        'volume': volume,
                        'shares': max(1, int(balance * MAX_RISK_PER_TRADE / price))
                    })
        
        # Sort by absolute change (most movement first)
        movers.sort(key=lambda x: abs(x['change']), reverse=True)
        return movers[:10]  # Return top 10 movers
        
    except Exception as e:
        return []

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
<p style="text-align: center; color: #808495; font-size: 13px; letter-spacing: 2px; margin-bottom: 20px;">SCALP SMART • TRADE FAST</p>
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
        <p style="color: #808495; font-size: 12px; margin: 0 0 15px 0;">Scanner + Crypto After Hours</p>
        <p style="color: #FFD700; margin: 5px 0;">⚡ TIER 3 - MASTER</p>
        <p style="color: #808495; font-size: 12px; margin: 0;">Full Access + Autopilot</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown('<div class="safe-badge">🛡️ <b>ULTRA-SAFE MODE</b> • TP: 0.3% • SL: 0.5% • Max Loss: 2%/day</div>', unsafe_allow_html=True)

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

market_open = (9 <= now.hour < 16) and (now.weekday() < 5)

target = now.replace(hour=9, minute=30, second=0, microsecond=0)
if now >= target.replace(hour=16): target += timedelta(days=1)
while target.weekday() > 4: target += timedelta(days=1)
delta = target - now

st.markdown(f"<h2 style='text-align:center;'>⏰ {delta.seconds//3600:02d}:{(delta.seconds%3600)//60:02d}:{delta.seconds%60:02d}</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;'><b>{'MARKET OPEN' if market_open else 'NEXT BELL'}</b></p>", unsafe_allow_html=True)

st.divider()

# Get account info first
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

# SMART SCANNER - Find affordable movers
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

# Crypto option for Tier 2+
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
                # Auto-select top mover
                ticker = st.session_state.hot_stocks[0]['symbol']
                selected_stock = st.session_state.hot_stocks[0]
                st.info(f"Auto: {ticker}")

# Protection Stats
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🛡️ PROTECTION")
    st.metric("Trades", f"{st.session_state.daily_trades}/{MAX_TRADES_PER_DAY}")
    st.metric("Daily P&L", f"${st.session_state.daily_pnl:.2f}")
    if st.session_state.circuit_breaker:
        st.error("🚨 CIRCUIT BREAKER")

# Main Trading Logic
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
        ticker = p.symbol  # Show current position
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
    
    # Auto TP/SL Management
    if has_position and current_position:
        current_pnl = float(current_position.unrealized_pl)
        current_pnl_pct = float(current_position.unrealized_plpc)
        st.session_state.daily_pnl = current_pnl
        
        if current_pnl_pct >= TAKE_PROFIT:
            api.close_position(current_position.symbol)
            st.session_state.daily_trades += 1
            st.success(f"✅ AUTO TAKE PROFIT: +{current_pnl_pct*100:.2f}%")
            st.balloons()
            time.sleep(2)
            st.rerun()
        
        elif current_pnl_pct <= -STOP_LOSS:
            api.close_position(current_position.symbol)
            st.session_state.daily_trades += 1
            st.error(f"🛡️ AUTO STOP LOSS: {current_pnl_pct*100:.2f}%")
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
                            <p style="color: #808495; font-size: 12px;">Auto TP: 0.3% • Auto SL: 0.5%</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Autopilot execution for Tier 3
                if tier == 3 and autopilot and st.session_state.daily_trades < MAX_TRADES_PER_DAY and market_open and not has_position:
                    if scalp_signal == "BUY" and shares > 0:
                        api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force='day')
                        st.session_state.daily_trades += 1
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
    
    # Display Section
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
        st.markdown(f"<p style='text-align:center; color:#808495;'>Size: {shares} {share_label} • TP: 0.3% • SL: 0.5%</p>", unsafe_allow_html=True)
        
        if has_position and current_position:
            pnl_pct = float(current_position.unrealized_plpc) * 100
            pnl_color = "#00FFA3" if pnl_pct >= 0 else "#FF4B4B"
            st.markdown(f"<h2 style='text-align:center; color:{pnl_color};'>OPEN: {pnl_pct:+.2f}%</h2>", unsafe_allow_html=True)
            st.progress(min(max((pnl_pct + 0.5) / 0.8, 0), 1))
            st.markdown("<p style='text-align:center; color:#808495;'>🔴 -0.5% SL | 🟢 +0.3% TP</p>", unsafe_allow_html=True)
        
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
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 BUY", disabled=not can_trade or has_position, use_container_width=True):
                tif = 'gtc' if crypto else 'day'
                api.submit_order(symbol=ticker, qty=shares, side='buy', type='market', time_in_force=tif)
                st.session_state.daily_trades += 1
                st.success("✅ BUY - TP/SL Active!")
                time.sleep(1)
                st.rerun()
        
        with col2:
            if st.button("🔴 SELL", disabled=not has_position, use_container_width=True):
                api.close_position(ticker)
                st.session_state.daily_trades += 1
                st.success("✅ CLOSED")
                time.sleep(1)
                st.rerun()
    else:
        st.markdown("<h3 style='text-align:center; color:#808495;'>👈 Scan & Select a Stock</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#808495;'>Use the Smart Scanner in the sidebar to find affordable, moving stocks.</p>", unsafe_allow_html=True)
    
    st.divider()
    
    if st.button("📱 SHARE MY WINS", use_container_width=True):
        st.session_state.show_share = not st.session_state.show_share
    
    if st.session_state.show_share:
        display_name = ticker if ticker else "SCANNING"
        st.code(f"""🌱 PROJECT HOPE 🌱
🛡️ ULTRA-SAFE MODE
💰 ${balance:.2f}
📊 P&L: ${st.session_state.daily_pnl:+.2f}
🎯 {display_name}
⚡ {st.session_state.daily_trades}/{MAX_TRADES_PER_DAY}
#ProjectHope #SafeTrading""")

except Exception as e:
    st.error(f"Error: {e}")
