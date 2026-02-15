import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import logging
from datetime import datetime
import time
import os
from pivot_calculator import calculate_pivot_levels
from chart_generator import generate_lightweight_chart
from bulk_fetcher import bulk_fetch_intraday, bulk_fetch_previous_day

# --- Configuration & Styling ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="Professional Stock Dashboard")

st.markdown("""
<style>
    .stApp { max-width: 100%; }
    .chart-container { width: 100%; height: 550px; margin-bottom: 2rem; }
    .auto-refresh-info { 
        background-color: #f0f2f6; padding: 10px; border-radius: 5px; 
        margin-bottom: 20px; text-align: center; border: 1px solid #d1d5db;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
# Stores detected signals to prevent them from vanishing on refresh
if "detected_stocks" not in st.session_state:
    st.session_state.detected_stocks = {"CE": {}, "PE": {}}
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True

# --- Logging & Persistence Logic ---
def log_signal(stock, type_, price, signal_time):
    """Logs the signal to a daily CSV if not already logged today."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"signal_log_{date_str}.csv"
    
    new_entry = {
        'Stock': stock,
        'Type': type_,
        'Price': round(price, 2),
        'Signal_Time': signal_time,
        'Detected_At': datetime.now().strftime('%H:%M:%S')
    }

    if os.path.exists(filename):
        try:
            df_log = pd.read_csv(filename)
            # Prevent repetition for the same stock and direction
            if not ((df_log['Stock'] == stock) & (df_log['Type'] == type_)).any():
                pd.concat([df_log, pd.DataFrame([new_entry])], ignore_index=True).to_csv(filename, index=False)
        except Exception as e:
            logger.error(f"Error updating log: {e}")
    else:
        pd.DataFrame([new_entry]).to_csv(filename, index=False)

# --- Data Engine (Optimized Bulk Fetching) ---
@st.cache_data(ttl=60)
def get_market_data():
    symbols_df = pd.read_csv("updated_list.csv")
    symbols = symbols_df["Symbol"].tolist()
    # Bulk fetch to solve the 3-minute latency issue
    intraday = bulk_fetch_intraday(symbols)
    prevday = bulk_fetch_previous_day(symbols)
    return symbols, intraday, prevday

# --- Analysis Logic ---
def run_analysis():
    symbols, intraday_map, prevday_map = get_market_data()
    
    # Progress UI indicator
    progress_bar = st.empty()
    status_text = st.empty()
    total = len(symbols)

    for i, stock in enumerate(symbols):
        # UI Progress Update
        percent = int(((i + 1) / total) * 100)
        progress_bar.progress(percent)
        status_text.text(f"🔍 Scanning {stock}... ({percent}%)")

        stock_data = intraday_map.get(stock)
        prev_data = prevday_map.get(stock)

        if stock_data is None or prev_data is None or stock_data.empty:
            continue

        # 1. Technical Calculations (Vectorized)
        pivots = calculate_pivot_levels(prev_data)
        prev_high, prev_low = prev_data['high'].max(), prev_data['low'].min()
        stock_data['EMA_9'] = stock_data['close'].ewm(span=9, adjust=False).mean()
        stock_data['EMA_15'] = stock_data['close'].ewm(span=15, adjust=False).mean()

        # 2. Strict Signal Conditions
        buy_mask = (stock_data['close'] > pivots['r3']) & \
                   (stock_data['close'] > stock_data['EMA_9']) & \
                   (stock_data['close'] > stock_data['EMA_15']) & \
                   (stock_data['close'] > prev_high)

        sell_mask = (stock_data['close'] < pivots['s3']) & \
                    (stock_data['close'] < stock_data['EMA_9']) & \
                    (stock_data['close'] < stock_data['EMA_15']) & \
                    (stock_data['close'] < prev_low)

        # 3. Handle First-Occurrence Signal Persistence
        if buy_mask.any():
            sig = stock_data[buy_mask].iloc[0] # Grab the first candle timestamp
            if stock not in st.session_state.detected_stocks["CE"]:
                st.session_state.detected_stocks["CE"][stock] = {
                    'data': stock_data, 'pivots': pivots, 'price': sig['close'], 'time': sig['Date']
                }
                log_signal(stock, "CE", sig['close'], sig['Date'])

        if sell_mask.any():
            sig = stock_data[sell_mask].iloc[0]
            if stock not in st.session_state.detected_stocks["PE"]:
                st.session_state.detected_stocks["PE"][stock] = {
                    'data': stock_data, 'pivots': pivots, 'price': sig['close'], 'time': sig['Date']
                }
                log_signal(stock, "PE", sig['close'], sig['Date'])

    progress_bar.empty()
    status_text.empty()

# --- Dashboard View Logic ---
def display_dashboard():
    col_ce, col_pe = st.columns(2)
    
    for side, col in [("CE", col_ce), ("PE", col_pe)]:
        with col:
            st.header(f"{'🔺 Bullish' if side == 'CE' else '🔻 Bearish'} Dashboard")
            # Render stored stocks from session state memory
            for stock, info in st.session_state.detected_stocks[side].items():
                st.subheader(f"📊 {stock}")
                st.info(f"Signal at: {info['time']} | Entry: {info['price']:.2f}")

                # Prepare Chart Layers
                df_c = info['data'][['Date', 'open', 'high', 'low', 'close']].copy()
                df_c['time'] = pd.to_datetime(df_c['Date']).dt.strftime('%Y-%m-%dT%H:%M:%S')
                
                e9 = info['data'][['Date', 'EMA_9']].rename(columns={'Date': 'time', 'EMA_9': 'value'})
                e15 = info['data'][['Date', 'EMA_15']].rename(columns={'Date': 'time', 'EMA_15': 'value'})
                e9['time'] = pd.to_datetime(e9['time']).dt.strftime('%Y-%m-%dT%H:%M:%S')
                e15['time'] = pd.to_datetime(e15['time']).dt.strftime('%Y-%m-%dT%H:%M:%S')

                # Render Component
                chart_code = generate_lightweight_chart(df_c[['time','open','high','low','close']], e9, e15, info['pivots'], stock)
                components.html(f"<div class='chart-container'>{chart_code}</div>", height=550)

# --- Sidebar Control Center ---
with st.sidebar:
    st.title("⚙️ Controls")
    st.session_state.auto_refresh = st.checkbox("Auto-Scan (1m)", value=st.session_state.auto_refresh)
    
    if st.button("🗑️ Reset Charts"):
        st.session_state.detected_stocks = {"CE": {}, "PE": {}}
        st.rerun()
    
    st.markdown("---")
    date_str = datetime.now().strftime('%Y-%m-%d')
    log_file = f"signal_log_{date_str}.csv"
    
    if os.path.exists(log_file):
        df_full = pd.read_csv(log_file)
        
        # Dual Table Sidebar Layout
        st.subheader("📈 CE Signals")
        ce_tab = df_full[df_full['Type'] == 'CE'].sort_values(by="Signal_Time", ascending=False)
        st.dataframe(ce_tab[['Stock', 'Price', 'Signal_Time']], hide_index=True)
        st.download_button("Download CE CSV", ce_tab.to_csv(index=False), f"CE_{date_str}.csv", "text/csv")

        st.markdown("---")
        st.subheader("📉 PE Signals")
        pe_tab = df_full[df_full['Type'] == 'PE'].sort_values(by="Signal_Time", ascending=False)
        st.dataframe(pe_tab[['Stock', 'Price', 'Signal_Time']], hide_index=True)
        st.download_button("Download PE CSV", pe_tab.to_csv(index=False), f"PE_{date_str}.csv", "text/csv")
    else:
        st.info("Scanner running... No signals yet.")

# --- Execution Flow ---
st.title("Asset Edge Scanner")
run_analysis()
display_dashboard()

# Continuous Refresh Logic
elapsed = time.time() - st.session_state.last_refresh
if st.session_state.auto_refresh:
    if elapsed >= 60:
        st.session_state.last_refresh = time.time()
        st.rerun()
    else:
        st.markdown(f"<div class='auto-refresh-info'>Refining scan in {int(60 - elapsed)}s</div>", unsafe_allow_html=True)
        time.sleep(1)
        st.rerun()