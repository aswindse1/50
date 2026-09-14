import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(page_title="Nifty 50 Order Flow", layout="wide", page_icon="📈")

st.title("📈 Nifty 50 Order Flow Finder")
st.caption("Basic market depth + imbalance | Plug in broker API for real tick/order-flow data")

# ---------------- Sidebar ----------------
st.sidebar.header("Settings")
refresh_sec = st.sidebar.slider("Auto-refresh (seconds)", 5, 60, 10)
use_simulation = st.sidebar.checkbox("Use Simulated Depth (for demo)", value=True)

# ---------------- Data Fetch ----------------
@st.cache_data(ttl=30)
def get_nifty_price():
    try:
        nifty = yf.Ticker("^NSEI")
        data = nifty.history(period="1d", interval="1m")
        if data.empty:
            return None, None
        last = data.iloc[-1]
        return float(last["Close"]), data
    except Exception as e:
        st.error(f"yfinance error: {e}")
        return None, None

ltp, hist = get_nifty_price()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Nifty 50 LTP", f"{ltp:,.2f}" if ltp else "—")
with col2:
    change = (ltp - hist["Close"].iloc[0]) if hist is not None and len(hist) > 0 else 0
    st.metric("Change (today)", f"{change:+.2f}")
with col3:
    st.metric("Time (IST)", datetime.now().strftime("%H:%M:%S"))

# ---------------- Simulated / Real Market Depth ----------------
st.subheader("Market Depth (Order Book)")

def generate_simulated_depth(ltp, levels=10):
    """Generate realistic looking depth for demo"""
    np.random.seed(int(time.time()) // 5)  # changes every few seconds
    bids = []
    asks = []
    for i in range(levels):
        bid_price = round(ltp - (i + 1) * 0.25 - np.random.uniform(0, 0.5), 2)
        ask_price = round(ltp + (i + 1) * 0.25 + np.random.uniform(0, 0.5), 2)
        bid_qty = int(np.random.randint(50, 800) * (1.5 if i < 3 else 1))
        ask_qty = int(np.random.randint(50, 800) * (1.5 if i < 3 else 1))
        bids.append({"price": bid_price, "qty": bid_qty, "orders": np.random.randint(1, 15)})
        asks.append({"price": ask_price, "qty": ask_qty, "orders": np.random.randint(1, 15)})
    return pd.DataFrame(bids), pd.DataFrame(asks)

if use_simulation and ltp:
    bid_df, ask_df = generate_simulated_depth(ltp)
else:
    # TODO: Replace this block with real broker depth
    # Example for Angel One / Zerodha quote() → depth
    st.warning("Real depth requires broker API. Currently showing simulation.")
    bid_df, ask_df = generate_simulated_depth(ltp or 24500)

# Display depth side by side
c1, c2 = st.columns(2)
with c1:
    st.write("**Bids (Buy)**")
    st.dataframe(
        bid_df.style.format({"price": "{:.2f}", "qty": "{:,}"}),
        use_container_width=True, hide_index=True
    )
with c2:
    st.write("**Asks (Sell)**")
    st.dataframe(
        ask_df.style.format({"price": "{:.2f}", "qty": "{:,}"}),
        use_container_width=True, hide_index=True
    )

# ---------------- Order Flow Metrics ----------------
st.subheader("Order Flow Metrics")

total_bid_qty = bid_df["qty"].sum()
total_ask_qty = ask_df["qty"].sum()
imbalance = (total_bid_qty - total_ask_qty) / (total_bid_qty + total_ask_qty + 1e-9) * 100

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Bid Qty", f"{total_bid_qty:,}")
m2.metric("Total Ask Qty", f"{total_ask_qty:,}")
m3.metric("Imbalance %", f"{imbalance:+.1f}%")
m4.metric("Best Bid / Ask", f"{bid_df.iloc[0]['price']:.2f} / {ask_df.iloc[0]['price']:.2f}")

# Simple visual imbalance bar
fig = go.Figure()
fig.add_trace(go.Bar(x=["Bids"], y=[total_bid_qty], name="Bids", marker_color="green"))
fig.add_trace(go.Bar(x=["Asks"], y=[total_ask_qty], name="Asks", marker_color="red"))
fig.update_layout(title="Bid vs Ask Quantity", height=300, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# ---------------- How to add real Order Flow ----------------
with st.expander("🔌 How to connect real Order Flow (Angel One / Zerodha)"):
    st.markdown("""
    ### Angel One SmartAPI (recommended for footprint)
    1. Create app at https://smartapi.angelbroking.com
    2. Install: `pip install smartapi-python pyotp`
    3. Use WebSocket for ticks + depth
    4. Process ticks into footprint bars (see the GitHub repo above)

    ### Zerodha Kite Connect
    ```python
    from kiteconnect import KiteConnect, KiteTicker
    kite = KiteConnect(api_key="...")
    kite.set_access_token("...")
    # Full mode gives 5-level depth
    kws = KiteTicker("api_key", "access_token")
    kws.subscribe([256265])  # Nifty 50 token
    kws.set_mode(kws.MODE_FULL, [256265])
    ```

    For true **footprint / order flow** you need:
    - Tick-by-tick data (last price + quantity + buy/sell aggressor)
    - Aggregate volume at each price level inside a candle
    - Calculate Delta = Buy volume − Sell volume
    """)

# Auto refresh
if st.sidebar.button("Refresh Now") or True:
    time.sleep(0.1)
    st.rerun()
