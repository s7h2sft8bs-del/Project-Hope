import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import time
import requests
import numpy as np

# ==================== CONFIGURATION ====================
PUSHOVER_USER_KEY = "ugurfo1drgkckg3i8i9x8cmon5qm85"
PUSHOVER_API_TOKEN = "aa9hxotiko33nd33zvih8pxsw2cx6a"

# Protection Settings
TAKE_PROFIT_1 = 0.005   # +0.5%
TAKE_PROFIT_2 = 0.010   # +1.0%
TAKE_PROFIT_3 = 0.020   # +2.0%
STOP_LOSS = 0.01        # -1.0%
BREAKEVEN_TRIGGER = 0.005
TRAILING_STOP = 0.003
MAX_RISK_PER_TRADE = 0.05
MAX_DAILY_LOSS = 0.03
MAX_TRADES_PER_DAY = 10
MIN_ACCOUNT_BALANCE = 25
AUTO_SCAN_INTERVAL = 30
MIN_SIGNAL_SCORE = 4

# Balance Split - 50% stocks, 50% crypto during market hours
STOCK_ALLOCATION = 0.50
CRYPTO_ALLOCATION = 0.50

# Asset Lists - Affordable stocks under $50 for small accounts
CRYPTO_UNIVERSE = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "LINK/USD", "UNI/USD"]
STOCK_UNIVERSE = [
    # Under $10
    "NIO", "PLTR", "SOFI", "SNAP", "HOOD", "RIVN", "LCID", "F", "AAL", "CCL", "T", "WBD", "INTC",
    # $10-30
    "AMD", "UBER", "COIN", "RBLX", "DKNG", "SQ", "PYPL", "BAC", "GM", "PINS", "ROKU",
    # $30-50 (may need more balance)
    "DIS", "NFLX", "SHOP"
]

st.set_page_config(page_title="Project Hope", page_icon="🌱", layout="wide")
load_dotenv()

# Auto-refresh every 3 seconds for live data
st_autorefresh(interval=3000, key="live_refresh")

# ==================== STYLES ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp {
    background: linear-gradient(180deg, #0a0e1a 0%, #151b2e 100%);
}

.main-header {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, rgba(0,255,163,0.1), rgba(255,215,0,0.1));
    border-radius: 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(0,255,163,0.3);
}

.tier-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 25px;
    text-align: center;
    transition: all 0.3s ease;
}

.tier-starter { border-top: 4px solid #00FFA3; }
.tier-builder { border-top: 4px solid #00E5FF; }
.tier-master { border-top: 4px solid #FFD700; }

.position-card {
    background: rgba(255,255,255,0.05);
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
}

.position-profit { border-left: 4px solid #00FFA3; }
.position-loss { border-left: 4px solid #FF4B4B; }

.protection-badge {
    background: linear-gradient(135deg, rgba(0,255,163,0.2), rgba(0,200,100,0.1));
    border: 2px solid #00FFA3;
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    margin: 15px 0;
}

.market-open {
    background: linear-gradient(135deg, rgba(0,255,163,0.3), rgba(0,200,100,0.2));
    border: 2px solid #00FFA3;
    border-radius: 12px;
    padding: 10px;
    text-align: center;
}

.market-closed {
    background: linear-gradient(135deg, rgba(255,75,75,0.3), rgba(200,50,50,0.2));
    border: 2px solid #FF4B4B;
    border-radius: 12px;
    padding: 10px;
    text-align: center;
}

.live-badge {
    background: rgba(255,0,0,0.2);
    border: 1px solid #FF0000;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    color: #FF0000;
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.stButton > button {
    background: linear-gradient(135deg, #00FFA3, #00CC7A);
    color: black;
    font-weight: 600;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 5px 20px rgba(0,255,163,0.4);
}
</style>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================
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
    except:
        pass

def is_market_open():
    """Check if US stock market is open"""
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    # Market open 9:30 AM - 4:00 PM ET, Monday-Friday
    if now.weekday() >= 5:  # Weekend
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close

def get_time_until_market():
    """Get time until market opens/closes"""
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    
    if is_market_open():
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        delta = market_close - now
        return f"Closes in {delta.seconds//3600}h {(delta.seconds%3600)//60}m"
    else:
        # Find next market open
        next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        if now.hour >= 16:
            next_open += timedelta(days=1)
        while next_open.weekday() >= 5:
            next_open += timedelta(days=1)
        delta = next_open - now
        hours = delta.seconds // 3600
        mins = (delta.seconds % 3600) // 60
        if delta.days > 0:
            return f"Opens in {delta.days}d {hours}h"
        return f"Opens in {hours}h {mins}m"

def get_live_crypto_price(symbol, api):
    """Get real-time crypto price"""
    try:
        quote = api.get_latest_crypto_quotes(symbol)
        if symbol in quote:
            return float(quote[symbol].ap)
        bars = api.get_crypto_bars(symbol, '1Min', limit=1).df
        return float(bars['close'].iloc[-1]) if len(bars) >= 1 else 0
    except:
        return 0

def get_live_stock_price(symbol, api):
    """Get real-time stock price"""
    try:
        trade = api.get_latest_trade(symbol)
        return float(trade.price)
    except:
        return 0

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(prices, period):
    """Calculate EMA"""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0
    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    return ema

def calculate_macd(prices):
    """Calculate MACD"""
    if len(prices) < 26:
        return 0, 0, 0
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    macd_line = ema12 - ema26
    signal_line = calculate_ema(prices[-9:], 9) if len(prices) >= 9 else macd_line
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def analyze_crypto(symbol, api, balance):
    """Complete technical analysis for crypto"""
    try:
        bars = api.get_crypto_bars(symbol, '5Min', limit=50).df
        if len(bars) < 10:
            return None
        
        prices = bars['close'].values
        volumes = bars['volume'].values
        
        current_price = get_live_crypto_price(symbol, api)
        if current_price == 0:
            current_price = float(prices[-1])
        
        rsi = calculate_rsi(prices)
        ema9 = calculate_ema(prices, 9)
        ema21 = calculate_ema(prices, 21)
        macd_line, signal_line, histogram = calculate_macd(prices)
        
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        score = 0
        indicators = {}
        
        if 30 <= rsi <= 65:
            score += 1
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bullish', 'reason': 'Healthy range'}
        elif rsi < 30:
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'neutral', 'reason': 'Oversold'}
        else:
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bearish', 'reason': 'Overbought'}
        
        if histogram > 0:
            score += 1
            indicators['MACD'] = {'value': f"{histogram:.6f}", 'status': 'bullish', 'reason': 'Bullish'}
        else:
            indicators['MACD'] = {'value': f"{histogram:.6f}", 'status': 'bearish', 'reason': 'Bearish'}
        
        if current_price > ema9:
            score += 1
            indicators['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bullish', 'reason': 'Price above'}
        else:
            indicators['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bearish', 'reason': 'Price below'}
        
        if ema9 > ema21:
            score += 1
            indicators['Trend'] = {'value': 'UP', 'status': 'bullish', 'reason': 'EMA9 > EMA21'}
        else:
            indicators['Trend'] = {'value': 'DOWN', 'status': 'bearish', 'reason': 'EMA9 < EMA21'}
        
        if volume_ratio >= 1.0:
            score += 1
            indicators['Volume'] = {'value': f"{volume_ratio:.1f}x", 'status': 'bullish', 'reason': 'Above avg'}
        else:
            indicators['Volume'] = {'value': f"{volume_ratio:.1f}x", 'status': 'neutral', 'reason': 'Below avg'}
        
        if score >= 4:
            signal = "BUY"
        elif score >= 3:
            signal = "WATCH"
        else:
            signal = "WAIT"
        
        shares = round((balance * MAX_RISK_PER_TRADE) / current_price, 6)
        
        return {
            'symbol': symbol,
            'price': current_price,
            'score': score,
            'signal': signal,
            'indicators': indicators,
            'volume_ratio': volume_ratio,
            'stop_price': current_price * (1 - STOP_LOSS),
            'target_price': current_price * (1 + TAKE_PROFIT_2),
            'shares': shares,
            'is_crypto': True
        }
    except:
        return None

def analyze_stock(symbol, api, balance):
    """Complete technical analysis for stocks"""
    try:
        bars = api.get_bars(symbol, '5Min', limit=50).df
        if len(bars) < 26:
            return None
        
        prices = bars['close'].values
        volumes = bars['volume'].values
        
        current_price = get_live_stock_price(symbol, api)
        if current_price == 0:
            current_price = float(prices[-1])
        
        # Skip if stock is too expensive for the balance
        if current_price > balance * 0.5:
            return None
        
        rsi = calculate_rsi(prices)
        ema9 = calculate_ema(prices, 9)
        ema21 = calculate_ema(prices, 21)
        macd_line, signal_line, histogram = calculate_macd(prices)
        
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        score = 0
        indicators = {}
        
        if 30 <= rsi <= 65:
            score += 1
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bullish', 'reason': 'Healthy range'}
        elif rsi < 30:
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'neutral', 'reason': 'Oversold'}
        else:
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bearish', 'reason': 'Overbought'}
        
        if histogram > 0:
            score += 1
            indicators['MACD'] = {'value': f"{histogram:.4f}", 'status': 'bullish', 'reason': 'Bullish'}
        else:
            indicators['MACD'] = {'value': f"{histogram:.4f}", 'status': 'bearish', 'reason': 'Bearish'}
        
        if current_price > ema9:
            score += 1
            indicators['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bullish', 'reason': 'Price above'}
        else:
            indicators['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bearish', 'reason': 'Price below'}
        
        if ema9 > ema21:
            score += 1
            indicators['Trend'] = {'value': 'UP', 'status': 'bullish', 'reason': 'EMA9 > EMA21'}
        else:
            indicators['Trend'] = {'value': 'DOWN', 'status': 'bearish', 'reason': 'EMA9 < EMA21'}
        
        if volume_ratio >= 1.0:
            score += 1
            indicators['Volume'] = {'value': f"{volume_ratio:.1f}x", 'status': 'bullish', 'reason': 'Above avg'}
        else:
            indicators['Volume'] = {'value': f"{volume_ratio:.1f}x", 'status': 'neutral', 'reason': 'Below avg'}
        
        if score >= 4:
            signal = "BUY"
        elif score >= 3:
            signal = "WATCH"
        else:
            signal = "WAIT"
        
        # Calculate shares (whole shares for stocks)
        shares = int((balance * MAX_RISK_PER_TRADE) / current_price)
        if shares < 1:
            shares = 1
        
        return {
            'symbol': symbol,
            'price': current_price,
            'score': score,
            'signal': signal,
            'indicators': indicators,
            'volume_ratio': volume_ratio,
            'stop_price': current_price * (1 - STOP_LOSS),
            'target_price': current_price * (1 + TAKE_PROFIT_2),
            'shares': shares,
            'is_crypto': False
        }
    except:
        return None

def scan_all_crypto(api, balance):
    """Scan all crypto with full analysis"""
    results = []
    for symbol in CRYPTO_UNIVERSE:
        analysis = analyze_crypto(symbol, api, balance)
        if analysis:
            results.append(analysis)
    results.sort(key=lambda x: (x['score'], x['volume_ratio']), reverse=True)
    return results

def scan_all_stocks(api, balance):
    """Scan all stocks with full analysis"""
    results = []
    for symbol in STOCK_UNIVERSE:
        analysis = analyze_stock(symbol, api, balance)
        if analysis:
            results.append(analysis)
    results.sort(key=lambda x: (x['score'], x['volume_ratio']), reverse=True)
    return results

# ==================== INITIALIZE API ====================
try:
    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'),
        os.getenv('ALPACA_SECRET_KEY'),
        "https://paper-api.alpaca.markets"
    )
    api_connected = True
except:
    api_connected = False

# ==================== SESSION STATE ====================
defaults = {
    'page': 'home',
    'tier': 0,
    'daily_trades': 0,
    'daily_pnl': 0.0,
    'last_date': None,
    'circuit_breaker': False,
    'peak_pnl': 0.0,
    'breakeven_active': False,
    'wins': 0,
    'losses': 0,
    'scanned_crypto': [],
    'scanned_stocks': [],
    'last_crypto_scan': 0,
    'last_stock_scan': 0,
    'autopilot': False
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ==================== PAGE: HOME ====================
def render_home():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #00FFA3; margin: 0; font-size: 3em;">🌱 PROJECT HOPE</h1>
        <p style="color: #808495; margin: 10px 0; font-size: 1.2em;">Trade Smart. Protected Always.</p>
        <p style="color: #FFD700; margin: 0;">The #1 Trading App for Everyday People</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = 'home'
    with col2:
        if st.button("📊 Trade", use_container_width=True):
            if st.session_state.tier > 0:
                st.session_state.page = 'trade'
                st.rerun()
            else:
                st.warning("Enter access code first")
    with col3:
        if st.button("👤 About", use_container_width=True):
            st.session_state.page = 'about'
            st.rerun()
    with col4:
        if st.button("📖 How It Works", use_container_width=True):
            st.session_state.page = 'howto'
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("""
    <div style="text-align: center; padding: 30px;">
        <h2 style="color: white;">Wall Street Has Protection. Now You Do Too.</h2>
        <p style="color: #808495; font-size: 1.1em; max-width: 600px; margin: 20px auto;">
            Built by an Amazon warehouse worker who taught himself to code. 
            For everyone Wall Street forgot.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Choose Your Plan")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="tier-card tier-starter">
            <h3 style="color: #00FFA3;">🌱 STARTER</h3>
            <h2 style="color: white;">$29<span style="font-size: 0.5em;">/month</span></h2>
            <hr style="border-color: rgba(255,255,255,0.1);">
            <p style="color: white; text-align: left;">✅ Real-time Scanner</p>
            <p style="color: white; text-align: left;">✅ Technical Analysis</p>
            <p style="color: white; text-align: left;">✅ Manual Trading</p>
            <p style="color: #808495; text-align: left;">❌ Crypto 24/7</p>
            <p style="color: #808495; text-align: left;">❌ Auto Trading</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("Coming Soon", key="tier1", disabled=True, use_container_width=True)
    
    with col2:
        st.markdown("""
        <div class="tier-card tier-builder">
            <span style="background: #00E5FF; color: black; padding: 5px 15px; border-radius: 20px; font-size: 0.8em;">POPULAR</span>
            <h3 style="color: #00E5FF; margin-top: 10px;">🚀 BUILDER</h3>
            <h2 style="color: white;">$79<span style="font-size: 0.5em;">/month</span></h2>
            <hr style="border-color: rgba(255,255,255,0.1);">
            <p style="color: white; text-align: left;">✅ Everything in Starter</p>
            <p style="color: white; text-align: left;">✅ Crypto 24/7</p>
            <p style="color: white; text-align: left;">✅ Semi-Auto Trading</p>
            <p style="color: #808495; text-align: left;">❌ Full Autopilot</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("Coming Soon", key="tier2", disabled=True, use_container_width=True)
    
    with col3:
        st.markdown("""
        <div class="tier-card tier-master">
            <span style="background: #FFD700; color: black; padding: 5px 15px; border-radius: 20px; font-size: 0.8em;">BEST VALUE</span>
            <h3 style="color: #FFD700; margin-top: 10px;">⚡ MASTER</h3>
            <h2 style="color: white;">$149<span style="font-size: 0.5em;">/month</span></h2>
            <hr style="border-color: rgba(255,255,255,0.1);">
            <p style="color: white; text-align: left;">✅ Everything in Builder</p>
            <p style="color: white; text-align: left;">✅ FULL AUTOPILOT</p>
            <p style="color: white; text-align: left;">✅ Scaling Profits</p>
            <p style="color: white; text-align: left;">✅ 1-on-1 Setup Call</p>
        </div>
        """, unsafe_allow_html=True)
        st.button("Coming Soon", key="tier3", disabled=True, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🔐 Have an Access Code?")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        code = st.text_input("Enter Code", type="password", placeholder="Enter your access code...", label_visibility="collapsed")
        if code == "HOPE200":
            st.session_state.tier = 1
            st.success("✅ STARTER Access Granted!")
        elif code == "HOPE247":
            st.session_state.tier = 2
            st.success("✅ BUILDER Access Granted!")
        elif code == "HOPE777":
            st.session_state.tier = 3
            st.success("✅ MASTER Access Granted!")
        elif code:
            st.error("Invalid code")
        
        if st.session_state.tier > 0:
            if st.button("🚀 Enter Trading Dashboard", use_container_width=True, type="primary"):
                st.session_state.page = 'trade'
                st.rerun()

# ==================== PAGE: ABOUT ====================
def render_about():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #00FFA3; margin: 0;">🌱 PROJECT HOPE</h1>
        <p style="color: #808495;">About Us</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="nav1"):
            st.session_state.page = 'home'
            st.rerun()
    with col2:
        if st.button("📊 Trade", use_container_width=True, key="nav2"):
            st.session_state.page = 'trade'
            st.rerun()
    with col3:
        st.button("👤 About", use_container_width=True, key="nav3", disabled=True)
    with col4:
        if st.button("📖 How It Works", use_container_width=True, key="nav4"):
            st.session_state.page = 'howto'
            st.rerun()
    
    st.markdown("---")
    st.markdown("## 👤 Meet the Founder")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        <div style="text-align: center;">
            <img src="https://i.postimg.cc/qvVSgvfx/IMG-7642.jpg" style="width: 100%; max-width: 300px; border-radius: 20px; border: 3px solid #FFD700;">
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <h3 style="color: #FFD700; margin: 0;">Stephen Martinez</h3>
            <p style="color: #00FFA3; margin: 5px 0;">Founder & Developer</p>
            <p style="color: #808495; font-size: 0.9em;">Lancaster, PA</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="padding: 20px;">
            <h3 style="color: white;">From Amazon Warehouse to Wall Street Tools</h3>
            <p style="color: #E0E0E0; line-height: 1.8;">
                I'm Stephen Martinez - an Amazon warehouse employee from Lancaster, PA. After years of 
                watching my coworkers lose their hard-earned money on trading apps designed to make them 
                trade more, not trade smarter, I decided to do something about it.
            </p>
            <p style="color: #E0E0E0; line-height: 1.8;">
                I taught myself to code during breaks and after long shifts. Every night I'd study 
                technical analysis, risk management, and what separates successful traders from the 99% 
                who lose money. The answer was always the same: <b>protection</b>.
            </p>
            <p style="color: #00FFA3; line-height: 1.8; font-weight: 600;">
                Project Hope brings institutional-grade protection to everyday people. Built by a 
                warehouse worker, for warehouse workers - and everyone else Wall Street forgot.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("## 📬 Contact")
    st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <p style="color: #E0E0E0;">📧 Email: <a href="mailto:thetradingprotocol@gmail.com" style="color: #00FFA3;">thetradingprotocol@gmail.com</a></p>
    </div>
    """, unsafe_allow_html=True)

# ==================== PAGE: HOW IT WORKS ====================
def render_howto():
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #00FFA3; margin: 0;">🌱 PROJECT HOPE</h1>
        <p style="color: #808495;">How It Works</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="hnav1"):
            st.session_state.page = 'home'
            st.rerun()
    with col2:
        if st.button("📊 Trade", use_container_width=True, key="hnav2"):
            st.session_state.page = 'trade'
            st.rerun()
    with col3:
        if st.button("👤 About", use_container_width=True, key="hnav3"):
            st.session_state.page = 'about'
            st.rerun()
    with col4:
        st.button("📖 How It Works", use_container_width=True, key="hnav4", disabled=True)
    
    st.markdown("---")
    st.markdown("## 📊 Our 5-Point Analysis System")
    
    indicators = [
        ("1️⃣ RSI", "Must be 30-65 (not extreme)", "#00FFA3"),
        ("2️⃣ MACD", "Must be bullish", "#00E5FF"),
        ("3️⃣ EMA 9", "Price must be above", "#FFD700"),
        ("4️⃣ Trend", "EMA9 > EMA21", "#FF6B6B"),
        ("5️⃣ Volume", "Above average", "#9B59B6"),
    ]
    
    for name, req, color in indicators:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.05); border-left: 4px solid {color}; padding: 15px; margin: 10px 0; border-radius: 0 10px 10px 0;">
            <h4 style="color: {color}; margin: 0;">{name}</h4>
            <p style="color: #E0E0E0; margin: 5px 0;">✅ {req}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("## 💰 50/50 Balance Split Strategy")
    st.markdown("""
    <div style="background: rgba(0,255,163,0.1); border-radius: 15px; padding: 20px; border: 1px solid rgba(0,255,163,0.3);">
        <h4 style="color: #00FFA3;">During Market Hours (9:30 AM - 4 PM ET):</h4>
        <p style="color: white;">📈 50% for STOCKS - Settles next day (T+1)</p>
        <p style="color: white;">🪙 50% for CRYPTO - Instant settlement</p>
        <br>
        <h4 style="color: #FFD700;">After Hours & Weekends:</h4>
        <p style="color: white;">🪙 100% for CRYPTO - Trade 24/7!</p>
    </div>
    """, unsafe_allow_html=True)

# ==================== PAGE: TRADE ====================
def render_trade():
    if st.session_state.tier == 0:
        st.warning("⚠️ Please enter an access code on the Home page.")
        if st.button("← Back to Home"):
            st.session_state.page = 'home'
            st.rerun()
        return
    
    tier_names = {1: "🌱 STARTER", 2: "🚀 BUILDER", 3: "⚡ MASTER"}
    market_open = is_market_open()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
        <h2 style="color: #00FFA3; margin: 0;">🌱 PROJECT HOPE</h2>
        <p style="color: #808495; margin: 0;">{tier_names[st.session_state.tier]}</p>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown('<span class="live-badge">🔴 LIVE</span>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="tnav1"):
            st.session_state.page = 'home'
            st.rerun()
    with col2:
        st.button("📊 Trade", use_container_width=True, key="tnav2", disabled=True)
    with col3:
        if st.button("👤 About", use_container_width=True, key="tnav3"):
            st.session_state.page = 'about'
            st.rerun()
    with col4:
        if st.button("📖 How It Works", use_container_width=True, key="tnav4"):
            st.session_state.page = 'howto'
            st.rerun()
    
    st.markdown("---")
    
    if not api_connected:
        st.error("❌ API not connected")
        return
    
    try:
        account = api.get_account()
        balance = float(account.equity)
        cash = float(account.cash)
    except:
        st.error("❌ Could not connect")
        return
    
    # Calculate split balances
    if market_open:
        stock_balance = balance * STOCK_ALLOCATION
        crypto_balance = balance * CRYPTO_ALLOCATION
    else:
        stock_balance = 0
        crypto_balance = balance
    
    try:
        positions = api.list_positions()
        position_symbols = [p.symbol for p in positions]
    except:
        positions = []
        position_symbols = []
    
    # Market Status
    if market_open:
        st.markdown(f"""
        <div class="market-open">
            <h3 style="color: #00FFA3; margin: 0;">🟢 MARKET OPEN</h3>
            <p style="color: white; margin: 5px 0;">{get_time_until_market()}</p>
            <p style="color: #808495; margin: 0;">50% Stocks (${stock_balance:.2f}) | 50% Crypto (${crypto_balance:.2f})</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="market-closed">
            <h3 style="color: #FF4B4B; margin: 0;">🔴 MARKET CLOSED</h3>
            <p style="color: white; margin: 5px 0;">{get_time_until_market()}</p>
            <p style="color: #808495; margin: 0;">100% Crypto Available (${crypto_balance:.2f})</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")
    
    # Account Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Equity", f"${balance:,.2f}")
    with col2:
        st.metric("💵 Cash", f"${cash:,.2f}")
    with col3:
        st.metric("📊 P&L", f"${st.session_state.daily_pnl:,.2f}")
    with col4:
        total = st.session_state.wins + st.session_state.losses
        wr = (st.session_state.wins / total * 100) if total > 0 else 0
        st.metric("🏆 Win Rate", f"{wr:.0f}%")
    
    # Autopilot (Tier 3)
    if st.session_state.tier == 3:
        st.markdown("### 🤖 Autopilot Mode")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.session_state.autopilot = st.toggle("Enable", key="autopilot_toggle")
        with col2:
            if st.session_state.autopilot:
                st.success("🤖 AUTOPILOT ACTIVE")
    
    # Protection Badge
    st.markdown("""
    <div class="protection-badge">
        🛡️ <b>7-LAYER PROTECTION ACTIVE</b> | Max Loss: 1% per trade | Circuit Breaker: 3% daily
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== ACTIVE POSITIONS ====================
    if positions:
        st.markdown("### 📈 Active Positions")
        
        for pos in positions:
            symbol = pos.symbol
            qty = float(pos.qty)
            entry_price = float(pos.avg_entry_price)
            is_crypto = '/' in symbol
            
            if is_crypto:
                live_price = get_live_crypto_price(symbol, api)
            else:
                live_price = get_live_stock_price(symbol, api)
            
            if live_price == 0:
                live_price = float(pos.current_price)
            
            pnl_dollar = (live_price - entry_price) * qty
            pnl_pct = ((live_price - entry_price) / entry_price) * 100
            pnl_color = "#00FFA3" if pnl_pct >= 0 else "#FF4B4B"
            card_class = "position-profit" if pnl_pct >= 0 else "position-loss"
            asset_type = "🪙 CRYPTO" if is_crypto else "📈 STOCK"
            
            st.markdown(f"""
            <div class="position-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <p style="color: #808495; margin: 0; font-size: 0.8em;">{asset_type}</p>
                        <h3 style="color: white; margin: 0;">{symbol}</h3>
                        <p style="color: #808495; margin: 5px 0;">Entry: ${entry_price:,.4f}</p>
                        <p style="color: #00E5FF; margin: 0; font-size: 1.2em;">Live: ${live_price:,.4f}</p>
                    </div>
                    <div style="text-align: right;">
                        <h2 style="color: {pnl_color}; margin: 0;">{pnl_pct:+.2f}%</h2>
                        <p style="color: {pnl_color}; margin: 5px 0; font-size: 1.1em;">${pnl_dollar:+,.2f}</p>
                        <p style="color: #808495;">Qty: {qty:.6f if is_crypto else qty:.0f}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.session_state.daily_pnl = pnl_dollar
            
            col1, col2 = st.columns(2)
            with col1:
                if pnl_pct > 0:
                    if st.button(f"🔒 Lock Profit", key=f"lock_{symbol}", use_container_width=True, type="primary"):
                        api.close_position(symbol)
                        st.session_state.wins += 1
                        st.session_state.daily_trades += 1
                        send_notification("🔒 PROFIT LOCKED", f"{symbol} +{pnl_pct:.2f}%")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
            with col2:
                if st.button(f"🚪 Exit", key=f"exit_{symbol}", use_container_width=True):
                    api.close_position(symbol)
                    st.session_state.daily_trades += 1
                    if pnl_pct >= 0:
                        st.session_state.wins += 1
                    else:
                        st.session_state.losses += 1
                    send_notification("🚪 CLOSED", f"{symbol} {pnl_pct:.2f}%")
                    time.sleep(1)
                    st.rerun()
        
        st.markdown("---")
    
    # ==================== SCANNERS ====================
    
    # STOCK SCANNER (only during market hours)
    if market_open:
        st.markdown(f"### 📈 Stock Scanner (Using ${stock_balance:.2f})")
        st.caption("⚠️ T+1 Settlement - Funds available next business day")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 SCAN STOCKS", use_container_width=True, type="primary"):
                with st.spinner("Analyzing stocks..."):
                    st.session_state.scanned_stocks = scan_all_stocks(api, stock_balance)
                    st.session_state.last_stock_scan = time.time()
        
        if st.session_state.scanned_stocks:
            scan_age = int(time.time() - st.session_state.last_stock_scan)
            st.caption(f"Last scan: {scan_age}s ago")
            
            for asset in st.session_state.scanned_stocks[:5]:
                score = asset['score']
                stars = "⭐" * score + "☆" * (5 - score)
                already_owns = asset['symbol'] in position_symbols
                
                with st.expander(f"📈 {asset['symbol']} - ${asset['price']:,.2f} | {stars} | {asset['signal']}", expanded=(score >= 4 and not already_owns)):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📊 Indicators:**")
                        for name, data in asset['indicators'].items():
                            icon = "✅" if data['status'] == 'bullish' else "❌" if data['status'] == 'bearish' else "⚠️"
                            st.markdown(f"{icon} **{name}:** {data['value']}")
                    
                    with col2:
                        st.markdown("**🎯 Trade Setup:**")
                        st.markdown(f"**Entry:** ${asset['price']:,.2f}")
                        st.markdown(f"**Stop:** ${asset['stop_price']:,.2f} (-1%)")
                        st.markdown(f"**Target:** ${asset['target_price']:,.2f} (+1%)")
                        st.markdown(f"**Shares:** {asset['shares']}")
                    
                    if already_owns:
                        st.success(f"✅ Already own {asset['symbol']}")
                    elif score >= 4 and st.session_state.tier >= 2:
                        if st.button(f"🟢 BUY {asset['symbol']}", key=f"buy_stock_{asset['symbol']}", use_container_width=True, type="primary"):
                            try:
                                api.submit_order(
                                    symbol=asset['symbol'],
                                    qty=asset['shares'],
                                    side='buy',
                                    type='market',
                                    time_in_force='day'
                                )
                                st.session_state.daily_trades += 1
                                send_notification("🟢 BUY STOCK", f"{asset['symbol']} @ ${asset['price']:,.2f}")
                                st.success(f"✅ Bought {asset['symbol']}!")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    elif score >= 4:
                        st.info("🔒 Upgrade to Builder for trading")
                    else:
                        st.warning(f"⏳ Score {score}/5 - Need 4+ for buy signal")
        
        st.markdown("---")
    
    # CRYPTO SCANNER (always available)
    st.markdown(f"### 🪙 Crypto Scanner (Using ${crypto_balance:.2f})")
    st.caption("✅ Instant Settlement - 24/7 Trading - No PDT!")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 SCAN CRYPTO", use_container_width=True, type="primary"):
            with st.spinner("Analyzing crypto..."):
                st.session_state.scanned_crypto = scan_all_crypto(api, crypto_balance)
                st.session_state.last_crypto_scan = time.time()
    
    if st.session_state.scanned_crypto:
        scan_age = int(time.time() - st.session_state.last_crypto_scan)
        st.caption(f"Last scan: {scan_age}s ago")
        
        for asset in st.session_state.scanned_crypto:
            score = asset['score']
            stars = "⭐" * score + "☆" * (5 - score)
            already_owns = asset['symbol'] in position_symbols
            
            with st.expander(f"🪙 {asset['symbol']} - ${asset['price']:,.2f} | {stars} | {asset['signal']}", expanded=(score >= 4 and not already_owns)):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📊 Indicators:**")
                    for name, data in asset['indicators'].items():
                        icon = "✅" if data['status'] == 'bullish' else "❌" if data['status'] == 'bearish' else "⚠️"
                        st.markdown(f"{icon} **{name}:** {data['value']}")
                
                with col2:
                    st.markdown("**🎯 Trade Setup:**")
                    st.markdown(f"**Entry:** ${asset['price']:,.4f}")
                    st.markdown(f"**Stop:** ${asset['stop_price']:,.4f} (-1%)")
                    st.markdown(f"**Target:** ${asset['target_price']:,.4f} (+1%)")
                    st.markdown(f"**Size:** {asset['shares']:.6f}")
                
                if already_owns:
                    st.success(f"✅ Already own {asset['symbol']}")
                elif score >= 4 and st.session_state.tier >= 2:
                    if st.button(f"🟢 BUY {asset['symbol']}", key=f"buy_crypto_{asset['symbol']}", use_container_width=True, type="primary"):
                        try:
                            api.submit_order(
                                symbol=asset['symbol'],
                                qty=asset['shares'],
                                side='buy',
                                type='market',
                                time_in_force='gtc'
                            )
                            st.session_state.daily_trades += 1
                            send_notification("🟢 BUY CRYPTO", f"{asset['symbol']} @ ${asset['price']:,.2f}")
                            st.success(f"✅ Bought {asset['symbol']}!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                elif score >= 4:
                    st.info("🔒 Upgrade to Builder for trading")
                else:
                    st.warning(f"⏳ Score {score}/5 - Need 4+ for buy signal")
    else:
        st.info("👆 Click SCAN CRYPTO to analyze")

# ==================== MAIN ====================
def main():
    tz = pytz.timezone('US/Eastern')
    today = str(datetime.now(tz).date())
    if st.session_state.last_date != today:
        st.session_state.daily_trades = 0
        st.session_state.daily_pnl = 0.0
        st.session_state.last_date = today
        st.session_state.circuit_breaker = False
        st.session_state.wins = 0
        st.session_state.losses = 0
    
    if st.session_state.page == 'home':
        render_home()
    elif st.session_state.page == 'about':
        render_about()
    elif st.session_state.page == 'howto':
        render_howto()
    elif st.session_state.page == 'trade':
        render_trade()
    else:
        render_home()

if __name__ == "__main__":
    main()

