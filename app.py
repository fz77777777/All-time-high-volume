import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="ATH Volume Scanner",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 All-Time High (ATH) Volume Breakout Scanner")
st.markdown("### **Scans 2000+ Stocks to find companies trading at the HIGHEST VOLUME IN THEIR ENTIRE HISTORY today**")
st.write("---")

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.header("🎯 Strategy Parameters")

min_price_gain = st.sidebar.slider(
    "Minimum Price Move Today (%)", 
    min_value=2.0, max_value=20.0, value=5.0, step=0.5
)

st.sidebar.write("---")
st.sidebar.header("⏳ Historical Data Depth")
st.sidebar.info(
    "We pull the maximum possible historical data (up to 5-10 years based on Yahoo token) "
    "to ensure today's volume is compared against the stock's true history."
)

# ==========================================
# DYNAMIC 2000+ NSE TICKER ENGINE
# ==========================================
@st.cache_data(ttl=86400)
def load_complete_nse_universe():
    base_pool = []
    
    # Core Matrix 1: Fetch Nifty 500
    try:
        url_500 = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df_500 = pd.read_csv(url_500)
        df_500.columns = [c.upper().strip() for c in df_500.columns]
        symbol_col = 'SYMBOL' if 'SYMBOL' in df_500.columns else df_500.columns[2]
        company_col = 'COMPANY NAME' if 'COMPANY NAME' in df_500.columns else df_500.columns[0]

        for _, row in df_500.iterrows():
            base_pool.append({
                'Symbol_YF': str(row[symbol_col]).strip() + ".NS",
                'Company Name': row[company_col]
            })
    except Exception:
        pass

    # Core Matrix 2: Fetch Broad Market Equities
    try:
        url_total = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        df_total = pd.read_csv(url_total)
        df_total.columns = [c.upper().strip() for c in df_total.columns]
        
        symbol_col = 'SYMBOL' if 'SYMBOL' in df_total.columns else df_total.columns[0]
        name_col = 'NAME OF COMPANY' if 'NAME OF COMPANY' in df_total.columns else df_total.columns[1]
        series_col = 'SERIES' if 'SERIES' in df_total.columns else None
        
        if series_col and series_col in df_total.columns:
            df_total = df_total[df_total[series_col].astype(str).str.upper().str.strip() == 'EQ']
            
        existing_symbols = {item['Symbol_YF'] for item in base_pool}
        
        for _, row in df_total.iterrows():
            ticker = str(row[symbol_col]).strip()
            if not ticker or ticker.lower() == 'symbol':
                continue
                
            yf_symbol = ticker + ".NS"
            if yf_symbol not in existing_symbols:
                base_pool.append({
                    'Symbol_YF': yf_symbol,
                    'Company Name': row[name_col] if name_col in df_total.columns else ticker
                })
            if len(base_pool) >= 2300: 
                break
    except Exception:
        pass
        
    return pd.DataFrame(base_pool)

master_universe = load_complete_nse_universe()
TICKER_LIST = master_universe['Symbol_YF'].tolist()
TICKER_MAP = dict(zip(master_universe['Symbol_YF'], master_universe['Company Name']))

st.sidebar.success(f"🎯 Total Equities Loaded: {len(TICKER_LIST)} Stocks")

# ==========================================
# ULTRA-FAST MAXIMUM HISTORY BATCH DOWNLOAD
# ==========================================
@st.cache_data(ttl=1800)
def fetch_maximum_historical_data(tickers):
    end_date = datetime.today().strftime('%Y-%m-%d')
    # Pulling 5 years back to scan true all-time volume depth safely without timeout
    start_date = (datetime.today() - timedelta(days=5 * 365)).strftime('%Y-%m-%d')
    df = yf.download(tickers, start=start_date, end=end_date, interval="1d", group_by='ticker', progress=False)
    return df

# ==========================================
# SCAN EXECUTION MATRIX
# ==========================================
if st.button("🚀 Run All-Time High Volume Scan"):
    with st.spinner("Downloading up to 5 Years of Historical Data for 2000+ stocks..."):
        all_data = fetch_maximum_historical_data(TICKER_LIST)
        
    st.write("⚙️ **Checking and verifying All-Time Volume Records...**")
    
    scanned_data_pool = []
    
    for ticker in TICKER_LIST:
        try:
            if len(TICKER_LIST) > 1:
                df = all_data[ticker].dropna(subset=['Close', 'Volume'])
            else:
                df = all_data.dropna(subset=['Close', 'Volume'])
                
            # We need sufficient history to evaluate ATH status
            if len(df) < 100: 
                continue
                
            df = df.copy()
            df['Daily_Return'] = df['Close'].pct_change() * 100
            
            # Today's Node Metrics
            row_today = df.iloc[-1]
            today_volume = float(row_today['Volume'])
            today_return = float(row_today['Daily_Return'])
            current_close = float(row_today['Close'])
            
            if today_volume <= 0:
                continue
                
            # Historical Frame (Everything EXCEPT today)
            historical_df = df.iloc[:-1]
            all_time_high_volume_prior = float(historical_df['Volume'].max())
            
            # --- THE HOLY GRAIL CONDITION ---
            # Today's volume MUST break the lifetime record, and price action must be positive
            if today_volume > all_time_high_volume_prior and today_return >= min_price_gain:
                
                # Calculate how brutal the breakout is compared to the old record
                outperformance_ratio = today_volume / all_time_high_volume_prior
                avg_20_volume = float(historical_df['Volume'].tail(20).mean())
                times_higher_than_normal = today_volume / avg_20_volume if avg_20_volume > 0 else 1.0
                
                today_vol_mn = today_volume / 1_000_000
                old_record_vol_mn = all_time_high_volume_prior / 1_000_000
                
                scanned_data_pool.append({
                    "Ticker Symbol": ticker.replace('.NS', ''),
                    "Company Name": TICKER_MAP.get(ticker, "Unknown"),
                    "Current Price": f"₹{round(current_close, 2)}",
                    "Today Move %": f"{round(today_return, 2)}%",
                    "Today ATH Volume": f"{round(today_vol_mn, 2)} M",
                    "Previous Best Vol Record": f"{round(old_record_vol_mn, 2)} M",
                    "Shattered Record By": f"{round(outperformance_ratio, 2)}x",
                    "Times of 20-Day Avg": f"{round(times_higher_than_normal, 1)}x",
                    "Status": "👑 LIFETIME RECORD BROKEN"
                })
        except Exception:
            continue
            
    # Display Results Engine
    if scanned_data_pool:
        final_df = pd.DataFrame(scanned_data_pool).sort_values(by="Shattered Record By", ascending=False)
        st.success(f"🎯 **Boom!** Found **{len(final_df)} Stocks** where institutions just created All-Time High Volume today!")
        st.dataframe(final_df, use_container_width=True)
        
        # Plotly Candlestick Chart Render for the alpha momentum stock
        priority_ticker = final_df.iloc[0]['Ticker Symbol'] + ".NS"
        try:
            chart_df = all_data[priority_ticker].dropna().tail(90)
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], 
                low=chart_df['Low'], close=chart_df['Close'], name="Price Action"
            ))
            fig.update_layout(
                xaxis_rangeslider_visible=False, template="plotly_white", 
                height=500, title=f"📈 Lifetime Volume Breakout Chart Context: {priority_ticker.replace('.NS','')}"
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
            
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export ATH Volume Pool to CSV", csv, "ath_volume_breakouts.csv", "text/csv")
    else:
        st.warning("Aaj pure market me kisi bhi stock ne apna lifetime volume record nahi toda hai. Try lowering the 'Minimum Price Move' slider.")
