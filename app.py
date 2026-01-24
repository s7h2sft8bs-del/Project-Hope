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
TAKE_PROFIT_1 = 0.005   # +0.5% - First scale out
TAKE_PROFIT_2 = 0.010   # +1.0% - Second scale out
TAKE_PROFIT_3 = 0.020   # +2.0% - Third scale out
STOP_LOSS = 0.01        # -1.0% max loss
BREAKEVEN_TRIGGER = 0.005
TRAILING_STOP = 0.002
MAX_RISK_PER_TRADE = 0.05
MAX_DAILY_LOSS = 0.03
MAX_TRADES_PER_DAY = 10
MIN_ACCOUNT_BALANCE = 25
AUTO_SCAN_INTERVAL = 30
MIN_SIGNAL_SCORE = 4  # Require 4/5 indicators

# Asset Lists
CRYPTO_UNIVERSE = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "LINK/USD", "UNI/USD"]
STOCK_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "CRM",
    "PLTR", "SOFI", "NIO", "RIVN", "LCID", "COIN", "HOOD", "SNAP", "RBLX", "DKNG",
    "SQ", "PYPL", "UBER", "ABNB", "SHOP", "ROKU", "NET", "CRWD", "SNOW", "PATH"
]

st.set_page_config(page_title="Project Hope", page_icon="🌱", layout="wide")
load_dotenv()

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

.nav-menu {
    display: flex;
    justify-content: center;
    gap: 10px;
    padding: 15px;
    background: rgba(255,255,255,0.05);
    border-radius: 15px;
    margin-bottom: 20px;
}

.tier-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 25px;
    text-align: center;
    transition: all 0.3s ease;
}

.tier-card:hover {
    border-color: #00FFA3;
    transform: translateY(-5px);
}

.tier-starter { border-top: 4px solid #00FFA3; }
.tier-builder { border-top: 4px solid #00E5FF; }
.tier-master { border-top: 4px solid #FFD700; }

.signal-card {
    background: rgba(255,255,255,0.05);
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
    border-left: 4px solid #00FFA3;
}

.signal-buy { border-left-color: #00FFA3; background: rgba(0,255,163,0.1); }
.signal-wait { border-left-color: #FFA500; background: rgba(255,165,0,0.1); }
.signal-sell { border-left-color: #FF4B4B; background: rgba(255,75,75,0.1); }

.protection-badge {
    background: linear-gradient(135deg, rgba(0,255,163,0.2), rgba(0,200,100,0.1));
    border: 2px solid #00FFA3;
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    margin: 15px 0;
}

.indicator-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 15px;
    background: rgba(255,255,255,0.03);
    border-radius: 8px;
    margin: 5px 0;
}

.indicator-bullish { color: #00FFA3; }
.indicator-bearish { color: #FF4B4B; }
.indicator-neutral { color: #808495; }

.score-stars {
    font-size: 24px;
    text-align: center;
    margin: 15px 0;
}

.author-card {
    background: linear-gradient(135deg, rgba(255,215,0,0.1), rgba(0,255,163,0.1));
    border-radius: 20px;
    padding: 30px;
    text-align: center;
    border: 1px solid rgba(255,215,0,0.3);
}

.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.feature-item {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 20px;
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

def analyze_asset(symbol, api, is_crypto=True):
    """Complete technical analysis for any asset"""
    try:
        # Get price data
        if is_crypto:
            bars = api.get_crypto_bars(symbol, '5Min', limit=50).df
        else:
            bars = api.get_bars(symbol, '5Min', limit=50).df
        
        if len(bars) < 26:
            return None
        
        prices = bars['close'].values
        volumes = bars['volume'].values
        current_price = float(prices[-1])
        
        # Calculate indicators
        rsi = calculate_rsi(prices)
        ema9 = calculate_ema(prices, 9)
        ema21 = calculate_ema(prices, 21)
        macd_line, signal_line, histogram = calculate_macd(prices)
        
        # Volume analysis
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Score each indicator (0 or 1)
        score = 0
        indicators = {}
        
        # 1. RSI Check (30-65 is healthy)
        if 30 <= rsi <= 65:
            score += 1
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bullish', 'reason': 'Healthy range'}
        elif rsi < 30:
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'neutral', 'reason': 'Oversold (risky)'}
        else:
            indicators['RSI'] = {'value': f"{rsi:.1f}", 'status': 'bearish', 'reason': 'Overbought'}
        
        # 2. MACD Check (bullish if histogram positive or crossing up)
        if histogram > 0:
            score += 1
            indicators['MACD'] = {'value': f"{histogram:.4f}", 'status': 'bullish', 'reason': 'Bullish momentum'}
        elif histogram > -0.0001 and macd_line > signal_line:
            score += 1
            indicators['MACD'] = {'value': f"{histogram:.4f}", 'status': 'bullish', 'reason': 'Crossing bullish'}
        else:
            indicators['MACD'] = {'value': f"{histogram:.4f}", 'status': 'bearish', 'reason': 'Bearish momentum'}
        
        # 3. Price above EMA9
        if current_price > ema9:
            score += 1
            indicators['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bullish', 'reason': 'Price above'}
        else:
            indicators['EMA9'] = {'value': f"${ema9:.2f}", 'status': 'bearish', 'reason': 'Price below'}
        
        # 4. EMA9 above EMA21 (trend confirmation)
        if ema9 > ema21:
            score += 1
            indicators['EMA21'] = {'value': f"${ema21:.2f}", 'status': 'bullish', 'reason': 'Uptrend confirmed'}
        else:
            indicators['EMA21'] = {'value': f"${ema21:.2f}", 'status': 'bearish', 'reason': 'Downtrend'}
        
        # 5. Volume above average
        if volume_ratio >= 1.0:
            score += 1
            indicators['Volume'] = {'value': f"{volume_ratio:.1f}x", 'status': 'bullish', 'reason': 'Above average'}
        else:
            indicators['Volume'] = {'value': f"{volume_ratio:.1f}x", 'status': 'neutral', 'reason': 'Below average'}
        
        # Determine signal
        if score >= 4:
            signal = "BUY"
        elif score >= 3:
            signal = "WATCH"
        else:
            signal = "WAIT"
        
        # Calculate entry, stop, target
        stop_price = current_price * (1 - STOP_LOSS)
        target_price = current_price * (1 + TAKE_PROFIT_2)
        
        return {
            'symbol': symbol,
            'price': current_price,
            'score': score,
            'signal': signal,
            'indicators': indicators,
            'rsi': rsi,
            'ema9': ema9,
            'ema21': ema21,
            'macd_histogram': histogram,
            'volume_ratio': volume_ratio,
            'stop_price': stop_price,
            'target_price': target_price,
            'is_crypto': is_crypto
        }
    except Exception as e:
        return None

def scan_all_assets(api, balance):
    """Scan all crypto and return analyzed results"""
    results = []
    for symbol in CRYPTO_UNIVERSE:
        analysis = analyze_asset(symbol, api, is_crypto=True)
        if analysis:
            shares = round((balance * MAX_RISK_PER_TRADE) / analysis['price'], 6)
            analysis['shares'] = shares
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
    'daily_trades': 0,
    'daily_pnl': 0.0,
    'last_date': None,
    'circuit_breaker': False,
    'peak_pnl': 0.0,
    'breakeven_active': False,
    'wins': 0,
    'losses': 0,
    'tier': 0,
    'scanned_assets': [],
    'last_scan_time': 0,
    'selected_asset': None,
    'scale_level': 0,
    'entry_price': 0,
    'position_size': 0
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ==================== PAGE: HOME ====================
def render_home():
    # Header with Logo
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #00FFA3; margin: 0; font-size: 3em;">🌱 PROJECT HOPE</h1>
        <p style="color: #808495; margin: 10px 0; font-size: 1.2em;">Trade Smart. Protected Always.</p>
        <p style="color: #FFD700; margin: 0;">The #1 Trading App for Everyday People</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation Menu
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = 'home'
    with col2:
        if st.button("📊 Trade", use_container_width=True):
            st.session_state.page = 'trade'
    with col3:
        if st.button("👤 About", use_container_width=True):
            st.session_state.page = 'about'
    with col4:
        if st.button("📖 How It Works", use_container_width=True):
            st.session_state.page = 'howto'
    
    st.markdown("---")
    
    # Value Proposition
    st.markdown("""
    <div style="text-align: center; padding: 30px;">
        <h2 style="color: white;">Wall Street Has Protection. Now You Do Too.</h2>
        <p style="color: #808495; font-size: 1.1em; max-width: 600px; margin: 20px auto;">
            Built by a pizza delivery driver who taught himself to code. 
            For everyone Wall Street forgot.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tier Cards
    st.markdown("### Choose Your Plan")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="tier-card tier-starter">
            <h3 style="color: #00FFA3;">🌱 STARTER</h3>
            <h2 style="color: white;">$29<span style="font-size: 0.5em;">/month</span></h2>
            <p style="color: #808495;">Perfect for beginners</p>
            <hr style="border-color: rgba(255,255,255,0.1);">
            <p style="color: white; text-align: left;">✅ Real-time Scanner</p>
            <p style="color: white; text-align: left;">✅ Technical Analysis</p>
            <p style="color: white; text-align: left;">✅ Signal Explanations</p>
            <p style="color: white; text-align: left;">✅ Manual Trading</p>
            <p style="color: white; text-align: left;">✅ Stocks (Market Hours)</p>
            <p style="color: #808495; text-align: left;">❌ Crypto 24/7</p>
            <p style="color: #808495; text-align: left;">❌ Auto Trading</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Select Starter", key="tier1", use_container_width=True):
            st.session_state.tier = 1
            st.session_state.page = 'trade'
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="tier-card tier-builder" style="transform: scale(1.02);">
            <span style="background: #00E5FF; color: black; padding: 5px 15px; border-radius: 20px; font-size: 0.8em;">POPULAR</span>
            <h3 style="color: #00E5FF; margin-top: 10px;">🚀 BUILDER</h3>
            <h2 style="color: white;">$79<span style="font-size: 0.5em;">/month</span></h2>
            <p style="color: #808495;">For serious traders</p>
            <hr style="border-color: rgba(255,255,255,0.1);">
            <p style="color: white; text-align: left;">✅ Everything in Starter</p>
            <p style="color: white; text-align: left;">✅ Crypto 24/7 (No PDT!)</p>
            <p style="color: white; text-align: left;">✅ Semi-Auto Trading</p>
            <p style="color: white; text-align: left;">✅ Push Notifications</p>
            <p style="color: white; text-align: left;">✅ Priority Support</p>
            <p style="color: #808495; text-align: left;">❌ Full Autopilot</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Select Builder", key="tier2", use_container_width=True):
            st.session_state.tier = 2
            st.session_state.page = 'trade'
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="tier-card tier-master">
            <span style="background: #FFD700; color: black; padding: 5px 15px; border-radius: 20px; font-size: 0.8em;">BEST VALUE</span>
            <h3 style="color: #FFD700; margin-top: 10px;">⚡ MASTER</h3>
            <h2 style="color: white;">$149<span style="font-size: 0.5em;">/month</span></h2>
            <p style="color: #808495;">Full automation</p>
            <hr style="border-color: rgba(255,255,255,0.1);">
            <p style="color: white; text-align: left;">✅ Everything in Builder</p>
            <p style="color: white; text-align: left;">✅ FULL AUTOPILOT</p>
            <p style="color: white; text-align: left;">✅ Scaling Profit System</p>
            <p style="color: white; text-align: left;">✅ Apple Watch Alerts</p>
            <p style="color: white; text-align: left;">✅ 1-on-1 Setup Call</p>
            <p style="color: white; text-align: left;">✅ VIP Support</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Select Master", key="tier3", use_container_width=True):
            st.session_state.tier = 3
            st.session_state.page = 'trade'
            st.rerun()
    
    # Access Code Section
    st.markdown("---")
    st.markdown("### Already have an access code?")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        code = st.text_input("Enter Code", type="password", placeholder="Enter your access code...")
        if code == "HOPE200":
            st.session_state.tier = 1
            st.success("✅ Starter Access Granted!")
        elif code == "HOPE247":
            st.session_state.tier = 2
            st.success("✅ Builder Access Granted!")
        elif code == "HOPE777":
            st.session_state.tier = 3
            st.success("✅ Master Access Granted!")
        elif code:
            st.error("Invalid code")
        
        if st.session_state.tier > 0:
            if st.button("🚀 Enter Trading Dashboard", use_container_width=True, type="primary"):
                st.session_state.page = 'trade'
                st.rerun()

# ==================== PAGE: ABOUT ====================
def render_about():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #00FFA3; margin: 0;">🌱 PROJECT HOPE</h1>
        <p style="color: #808495;">About Us</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
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
        if st.button("👤 About", use_container_width=True, key="nav3"):
            pass
    with col4:
        if st.button("📖 How It Works", use_container_width=True, key="nav4"):
            st.session_state.page = 'howto'
            st.rerun()
    
    st.markdown("---")
    
    # Author Section
    st.markdown("## 👤 Meet the Founder")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        <div class="author-card">
            <div style="font-size: 80px; margin-bottom: 15px;">👨‍💻</div>
            <h3 style="color: #FFD700; margin: 0;">Stephen Martinez</h3>
            <p style="color: #00FFA3; margin: 5px 0;">Founder & Developer</p>
            <p style="color: #808495; font-size: 0.9em;">Lancaster, PA</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="padding: 20px;">
            <h3 style="color: white;">From Pizza Delivery to Code</h3>
            <p style="color: #E0E0E0; line-height: 1.8;">
                I'm Stephen Martinez - a pizza delivery driver who taught himself to code because 
                I was tired of watching my coworkers lose money on trading apps that were designed 
                to make them trade more, not trade smarter.
            </p>
            <p style="color: #E0E0E0; line-height: 1.8;">
                Every night after my shifts, I'd hear the same stories: "I was up $50, then lost it all." 
                "The app showed green, I bought, then it crashed." "I don't understand why I keep losing."
            </p>
            <p style="color: #E0E0E0; line-height: 1.8;">
                The truth? Those apps aren't broken - they're working exactly as designed. They make money 
                when you trade more. They don't care if you win.
            </p>
            <p style="color: #00FFA3; line-height: 1.8; font-weight: 600;">
                Project Hope is different. We succeed when YOU succeed. Period.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Mission Section
    st.markdown("## 🎯 Our Mission")
    
    st.markdown("""
    <div style="background: rgba(0,255,163,0.1); border-radius: 20px; padding: 30px; text-align: center; border: 1px solid rgba(0,255,163,0.3);">
        <h2 style="color: #00FFA3; margin-bottom: 20px;">"Democratize professional-grade trading protection for the 99%"</h2>
        <p style="color: #E0E0E0; font-size: 1.1em; max-width: 700px; margin: 0 auto;">
            Wall Street has had algorithmic protection for decades. Hedge funds never risk more than they can afford. 
            They have circuit breakers, trailing stops, and scaling systems built into everything they do.
            <br><br>
            The everyday person? They get confetti animations when they lose money.
            <br><br>
            <span style="color: #FFD700; font-weight: 600;">We're changing that.</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Why Project Hope
    st.markdown("## 💡 Why Project Hope?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-item">
            <div style="font-size: 40px; margin-bottom: 10px;">🛡️</div>
            <h4 style="color: #00FFA3;">Protection First</h4>
            <p style="color: #808495;">7 layers of protection before any profit talk. Your capital is sacred.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-item">
            <div style="font-size: 40px; margin-bottom: 10px;">🧠</div>
            <h4 style="color: #00E5FF;">Real Analysis</h4>
            <p style="color: #808495;">RSI, MACD, EMA, Volume - not just "is it green?" Actually understand WHY.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-item">
            <div style="font-size: 40px; margin-bottom: 10px;">💰</div>
            <h4 style="color: #FFD700;">Small Account Focus</h4>
            <p style="color: #808495;">Built for $200-$5,000 accounts. We treat your money like it matters - because it does.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Contact
    st.markdown("## 📬 Contact")
    st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <p style="color: #E0E0E0;">📧 Email: <a href="mailto:thetradingprotocol@gmail.com" style="color: #00FFA3;">thetradingprotocol@gmail.com</a></p>
        <p style="color: #E0E0E0;">🌐 Web: <a href="https://project-hope-461.onrender.com" style="color: #00FFA3;">project-hope-461.onrender.com</a></p>
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
    
    # Navigation
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
        if st.button("📖 How It Works", use_container_width=True, key="hnav4"):
            pass
    
    st.markdown("---")
    
    # Technical Analysis
    st.markdown("## 📊 Our Technical Analysis System")
    st.markdown("""
    <p style="color: #E0E0E0;">We don't guess. We use 5 proven indicators that must align before any trade:</p>
    """, unsafe_allow_html=True)
    
    indicators = [
        ("RSI (14)", "Relative Strength Index", "Must be 30-65 (not overbought/oversold)", "#00FFA3"),
        ("MACD", "Moving Average Convergence Divergence", "Must be bullish or crossing up", "#00E5FF"),
        ("EMA 9", "9-Period Exponential Moving Average", "Price must be above (short-term bullish)", "#FFD700"),
        ("EMA 21", "21-Period Exponential Moving Average", "EMA 9 must be above (trend confirmed)", "#FF6B6B"),
        ("Volume", "Trading Volume Analysis", "Must be above average (real buyers)", "#9B59B6"),
    ]
    
    for name, full_name, requirement, color in indicators:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.05); border-left: 4px solid {color}; padding: 15px; margin: 10px 0; border-radius: 0 10px 10px 0;">
            <h4 style="color: {color}; margin: 0;">{name}</h4>
            <p style="color: #808495; margin: 5px 0; font-size: 0.9em;">{full_name}</p>
            <p style="color: #E0E0E0; margin: 0;">✅ {requirement}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Signal Scoring
    st.markdown("## ⭐ Signal Scoring")
    st.markdown("""
    <div style="background: rgba(255,215,0,0.1); border-radius: 15px; padding: 20px; border: 1px solid rgba(255,215,0,0.3);">
        <p style="color: #E0E0E0; margin-bottom: 15px;">Each asset gets scored 1-5 based on how many indicators align:</p>
        <p style="color: #00FFA3; font-size: 1.1em;">⭐⭐⭐⭐⭐ (5/5) = <b>STRONG BUY</b> - Auto-trade immediately</p>
        <p style="color: #00FFA3; font-size: 1.1em;">⭐⭐⭐⭐ (4/5) = <b>BUY</b> - Auto-trade with confirmation</p>
        <p style="color: #FFA500; font-size: 1.1em;">⭐⭐⭐ (3/5) = <b>WATCH</b> - Manual only</p>
        <p style="color: #FF4B4B; font-size: 1.1em;">⭐⭐ or less = <b>NO TRADE</b> - Wait for better setup</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 7-Layer Protection
    st.markdown("## 🛡️ The 7-Layer Protection System™")
    
    protections = [
        ("1", "Position Size Limit", "Maximum 5% of account per trade", "#00FFA3"),
        ("2", "Smart Entry", "4/5 indicators must align", "#00E5FF"),
        ("3", "Breakeven Protection", "Stop moves to entry at +0.5%", "#FFD700"),
        ("4", "Trailing Stop", "Locks profits as price rises", "#FF6B6B"),
        ("5", "Scaling Take Profit", "Sells in 25% chunks", "#9B59B6"),
        ("6", "Stop Loss", "Maximum -1% loss per trade", "#E74C3C"),
        ("7", "Daily Circuit Breaker", "-3% daily loss stops all trading", "#C0392B"),
    ]
    
    for num, name, desc, color in protections:
        st.markdown(f"""
        <div style="display: flex; align-items: center; background: rgba(255,255,255,0.03); padding: 15px; margin: 8px 0; border-radius: 10px;">
            <div style="background: {color}; color: black; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 15px;">{num}</div>
            <div>
                <h4 style="color: white; margin: 0;">{name}</h4>
                <p style="color: #808495; margin: 0;">{desc}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Scaling System
    st.markdown("## 📈 Smart Profit Scaling")
    st.markdown("""
    <p style="color: #E0E0E0;">We don't exit 100% at the first sign of profit. We scale out to catch big moves:</p>
    """, unsafe_allow_html=True)
    
    scales = [
        ("+0.5%", "Sell 25%", "Move stop to breakeven", "75%"),
        ("+1.0%", "Sell 25%", "Trail stop to +0.5%", "50%"),
        ("+2.0%", "Sell 25%", "Trail stop to +1.0%", "25%"),
        ("+3.0%+", "Let it RUN", "Trail stop at +1.5%", "25%"),
    ]
    
    for target, action, protection, remaining in scales:
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, rgba(0,255,163,0.2), rgba(0,255,163,0.05)); padding: 15px; margin: 8px 0; border-radius: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #00FFA3; font-weight: bold; font-size: 1.2em;">{target}</span>
            <span style="color: white;">{action}</span>
            <span style="color: #808495;">{protection}</span>
            <span style="color: #FFD700;">{remaining} left</span>
        </div>
        """, unsafe_allow_html=True)

# ==================== PAGE: TRADE ====================
def render_trade():
    if st.session_state.tier == 0:
        st.warning("⚠️ Please select a tier or enter an access code on the Home page.")
        if st.button("← Back to Home"):
            st.session_state.page = 'home'
            st.rerun()
        return
    
    tier_names = {1: "🌱 STARTER", 2: "🚀 BUILDER", 3: "⚡ MASTER"}
    
    # Header
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 15px; margin-bottom: 20px;">
        <div>
            <h2 style="color: #00FFA3; margin: 0;">🌱 PROJECT HOPE</h2>
            <p style="color: #808495; margin: 0;">{tier_names[st.session_state.tier]}</p>
        </div>
        <div style="text-align: right;">
            <span class="live-badge">🔴 LIVE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="tnav1"):
            st.session_state.page = 'home'
            st.rerun()
    with col2:
        if st.button("📊 Trade", use_container_width=True, key="tnav2"):
            pass
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
        st.error("❌ API not connected. Check your Alpaca credentials.")
        return
    
    # Get account info
    try:
        account = api.get_account()
        balance = float(account.equity)
    except:
        st.error("❌ Could not connect to account")
        return
    
    # Account Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Balance", f"${balance:,.2f}")
    with col2:
        st.metric("📊 Daily P&L", f"${st.session_state.daily_pnl:,.2f}")
    with col3:
        total = st.session_state.wins + st.session_state.losses
        wr = (st.session_state.wins / total * 100) if total > 0 else 0
        st.metric("🏆 Win Rate", f"{wr:.0f}%")
    with col4:
        st.metric("📈 Trades", f"{st.session_state.daily_trades}/{MAX_TRADES_PER_DAY}")
    
    # Protection Badge
    st.markdown("""
    <div class="protection-badge">
        🛡️ <b>7-LAYER PROTECTION ACTIVE</b> | Max Loss: 1% per trade | Circuit Breaker: 3% daily
    </div>
    """, unsafe_allow_html=True)
    
    # Scanner Section
    st.markdown("### 🔍 Real-Time Scanner")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 SCAN NOW", use_container_width=True, type="primary"):
            with st.spinner("Analyzing all assets..."):
                st.session_state.scanned_assets = scan_all_assets(api, balance)
                st.session_state.last_scan_time = time.time()
    
    # Display scanned assets
    if st.session_state.scanned_assets:
        st.markdown(f"*Last scan: {int(time.time() - st.session_state.last_scan_time)}s ago*")
        
        for asset in st.session_state.scanned_assets:
            score = asset['score']
            stars = "⭐" * score + "☆" * (5 - score)
            
            signal_class = "signal-buy" if asset['signal'] == "BUY" else "signal-wait" if asset['signal'] == "WATCH" else "signal-wait"
            
            with st.expander(f"{asset['symbol']} - ${asset['price']:,.2f} | {stars} | {asset['signal']}", expanded=(score >= 4)):
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📊 Indicators:**")
                    for name, data in asset['indicators'].items():
                        color = "#00FFA3" if data['status'] == 'bullish' else "#FF4B4B" if data['status'] == 'bearish' else "#808495"
                        icon = "✅" if data['status'] == 'bullish' else "❌" if data['status'] == 'bearish' else "⚠️"
                        st.markdown(f"{icon} **{name}:** {data['value']} - *{data['reason']}*")
                
                with col2:
                    st.markdown("**🎯 Trade Setup:**")
                    st.markdown(f"**Entry:** ${asset['price']:,.2f}")
                    st.markdown(f"**Stop Loss:** ${asset['stop_price']:,.2f} (-1%)")
                    st.markdown(f"**Target:** ${asset['target_price']:,.2f} (+1%)")
                    st.markdown(f"**Size:** {asset['shares']:.6f} units")
                
                # Trade buttons based on tier
                if score >= 4:
                    if st.session_state.tier >= 2:
                        if st.button(f"🟢 BUY {asset['symbol']}", key=f"buy_{asset['symbol']}", use_container_width=True, type="primary"):
                            try:
                                api.submit_order(
                                    symbol=asset['symbol'],
                                    qty=asset['shares'],
                                    side='buy',
                                    type='market',
                                    time_in_force='gtc'
                                )
                                st.session_state.daily_trades += 1
                                send_notification("🟢 BUY EXECUTED", f"{asset['symbol']} @ ${asset['price']:,.2f}\nScore: {score}/5")
                                st.success(f"✅ Bought {asset['symbol']}!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Order failed: {e}")
                    else:
                        st.info("🔒 Upgrade to Builder or Master tier for auto-trading")
                else:
                    st.warning(f"⏳ Score {score}/5 - Need 4+ for auto-trade")
    else:
        st.info("👆 Click SCAN NOW to analyze all assets")
    
    # Check for existing positions
    st.markdown("---")
    st.markdown("### 📈 Active Positions")
    
    try:
        positions = api.list_positions()
        if positions:
            for pos in positions:
                pnl_pct = float(pos.unrealized_plpc) * 100
                pnl_color = "#00FFA3" if pnl_pct >= 0 else "#FF4B4B"
                
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; border-left: 4px solid {pnl_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="color: white; margin: 0;">{pos.symbol}</h3>
                            <p style="color: #808495; margin: 0;">{pos.qty} units @ ${float(pos.avg_entry_price):,.2f}</p>
                        </div>
                        <div style="text-align: right;">
                            <h2 style="color: {pnl_color}; margin: 0;">{pnl_pct:+.2f}%</h2>
                            <p style="color: {pnl_color}; margin: 0;">${float(pos.unrealized_pl):+,.2f}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if pnl_pct > 0:
                        if st.button(f"🔒 Lock Profit ({pnl_pct:+.2f}%)", key=f"lock_{pos.symbol}", use_container_width=True):
                            api.close_position(pos.symbol)
                            st.session_state.wins += 1
                            send_notification("🔒 PROFIT LOCKED", f"{pos.symbol} +{pnl_pct:.2f}%")
                            st.success("Profit locked!")
                            st.rerun()
                with col2:
                    if st.button(f"🚪 Exit Position", key=f"exit_{pos.symbol}", use_container_width=True):
                        api.close_position(pos.symbol)
                        if pnl_pct >= 0:
                            st.session_state.wins += 1
                        else:
                            st.session_state.losses += 1
                        send_notification("🚪 POSITION CLOSED", f"{pos.symbol} {pnl_pct:.2f}%")
                        st.rerun()
        else:
            st.info("No active positions. Scan for opportunities above!")
    except Exception as e:
        st.error(f"Could not load positions: {e}")

# ==================== MAIN APP ====================
def main():
    # Auto-refresh for live data
    st_autorefresh(interval=5000, key="refresh")
    
    # Reset daily stats if new day
    tz = pytz.timezone('US/Eastern')
    today = str(datetime.now(tz).date())
    if st.session_state.last_date != today:
        st.session_state.daily_trades = 0
        st.session_state.daily_pnl = 0.0
        st.session_state.last_date = today
        st.session_state.circuit_breaker = False
        st.session_state.wins = 0
        st.session_state.losses = 0
    
    # Route to correct page
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
