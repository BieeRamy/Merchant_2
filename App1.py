import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Load your data
df = pd.read_csv("merged_data.csv")  # Replace with your CSV path
df['transaction_date'] = pd.to_datetime(df['transaction_date'])

st.set_page_config(page_title="Merchant Growth Dashboard", layout="wide")

st.title("Dynamic Merchant Growth Dashboard")

# -------------------------------
# Sidebar filters
# -------------------------------
st.sidebar.header("Filters")

# Date range
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    [df['transaction_date'].min(), df['transaction_date'].max()]
)

# Top/Bottom selection
top_bottom = st.sidebar.selectbox("Top/Bottom Merchants", ["Top 10", "Bottom 10"])

# Metrics selection
metrics = st.sidebar.multiselect(
    "Select Growth Metrics (Bars)",
    ["Avg MoM Growth", "Avg QoQ Growth", "Avg YoY Growth"],
    default=["Avg MoM Growth", "Avg QoQ Growth", "Avg YoY Growth"]
)

# Category, City, Status filters
category_filter = st.sidebar.multiselect("Category", df['category_x'].unique())
city_filter = st.sidebar.multiselect("City", df['city_x'].unique())
status_filter = st.sidebar.multiselect("Account Status", df['account_status'].unique())

# -------------------------------
# Filter data
# -------------------------------
df_filtered = df[(df['transaction_date'] >= pd.to_datetime(start_date)) &
                 (df['transaction_date'] <= pd.to_datetime(end_date))]

if category_filter:
    df_filtered = df_filtered[df_filtered['category_x'].isin(category_filter)]
if city_filter:
    df_filtered = df_filtered[df_filtered['city_x'].isin(city_filter)]
if status_filter:
    df_filtered = df_filtered[df_filtered['account_status'].isin(status_filter)]

# -------------------------------
# Prepare monthly metrics
# -------------------------------
df_filtered['year_month'] = df_filtered['transaction_date'].dt.to_period('M').astype(str)
monthly = df_filtered.groupby(['merchant_id','year_month']).agg(
    txn_count=('transaction_id','count'),
    total_amount=('amount','sum')
).reset_index().sort_values(['merchant_id','year_month'])

# MoM, QoQ, YoY growth
monthly['MoM_txn'] = monthly.groupby('merchant_id')['txn_count'].pct_change() * 100
monthly['QoQ_txn'] = monthly.groupby('merchant_id')['txn_count'].pct_change(periods=3) * 100
monthly['YoY_txn'] = monthly.groupby('merchant_id')['txn_count'].pct_change(periods=12) * 100

# Average per merchant
merchant_summary = monthly.groupby('merchant_id').agg(
    avg_MoM_txn=('MoM_txn','mean'),
    avg_QoQ_txn=('QoQ_txn','mean'),
    avg_YoY_txn=('YoY_txn','mean'),
    start_amt=('total_amount','first'),
    end_amt=('total_amount','last')
).reset_index()

# CAGR
n_years = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days / 365.25
merchant_summary['CAGR'] = ((merchant_summary['end_amt'] / merchant_summary['start_amt']) ** (1/n_years) -1) * 100

# Top/Bottom 10
if top_bottom.startswith("Top"):
    df_plot = merchant_summary.sort_values('avg_QoQ_txn', ascending=False).head(10)
else:
    df_plot = merchant_summary.sort_values('avg_QoQ_txn', ascending=True).head(10)

# -------------------------------
# Plot chart
# -------------------------------
fig = go.Figure()
colors = {'Avg MoM Growth':'royalblue','Avg QoQ Growth':'crimson','Avg YoY Growth':'green'}

metric_map = {
    "Avg MoM Growth":"avg_MoM_txn",
    "Avg QoQ Growth":"avg_QoQ_txn",
    "Avg YoY Growth":"avg_YoY_txn"
}

for m in metrics:
    fig.add_trace(go.Bar(
        x=df_plot['merchant_id'],
        y=df_plot[metric_map[m]],
        name=m,
        marker_color=colors.get(m,'grey')
    ))

# CAGR line
fig.add_trace(go.Scatter(
    x=df_plot['merchant_id'],
    y=df_plot['CAGR'],
    mode='lines+markers',
    name='CAGR',
    line=dict(color='orange', width=3),
    yaxis='y2'
))

fig.update_layout(
    title=f"{top_bottom} Merchants - Growth Metrics",
    xaxis_title="Merchant ID",
    yaxis_title="Growth (%) (Bars)",
    yaxis2=dict(title="CAGR (%)", overlaying='y', side='right'),
    barmode='group',
    template='plotly_white',
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Display table
# -------------------------------
st.subheader("Merchant Summary Table")
st.dataframe(df_plot)
