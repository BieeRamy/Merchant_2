# app1.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from tabulate import tabulate

# ------------------------------
# Load Data
# ------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("merchant_data.csv")
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    return df

df = load_data()

# ------------------------------
# Sidebar filters
# ------------------------------
st.sidebar.header("Filters")

# Date range
start_date = st.sidebar.date_input("Start Date", df['transaction_date'].min())
end_date = st.sidebar.date_input("End Date", df['transaction_date'].max())

# Top/Bottom selector
top_bottom = st.sidebar.selectbox("Top/Bottom Merchants", ['Top 10', 'Bottom 10'])

# Metrics
selected_metrics = st.sidebar.multiselect(
    "Select Growth Metrics (Bars)",
    ['Avg MoM Growth', 'Avg QoQ Growth', 'Avg YoY Growth'],
    default=['Avg MoM Growth', 'Avg QoQ Growth', 'Avg YoY Growth']
)

# Category filter
if 'category_x' in df.columns:
    categories = st.sidebar.multiselect(
        "Filter by Category", df['category_x'].unique(), default=None
    )
else:
    categories = None

# City filter
if 'city_x' in df.columns:
    cities = st.sidebar.multiselect(
        "Filter by City", df['city_x'].unique(), default=None
    )
else:
    cities = None

# Account status filter
if 'account_status' in df.columns:
    statuses = st.sidebar.multiselect(
        "Filter by Account Status", df['account_status'].unique(), default=None
    )
else:
    statuses = None

# ------------------------------
# Filter Data
# ------------------------------
df_filtered = df[(df['transaction_date'] >= pd.to_datetime(start_date)) &
                 (df['transaction_date'] <= pd.to_datetime(end_date))]

if categories:
    df_filtered = df_filtered[df_filtered['category_x'].isin(categories)]
if cities:
    df_filtered = df_filtered[df_filtered['city_x'].isin(cities)]
if statuses:
    df_filtered = df_filtered[df_filtered['account_status'].isin(statuses)]

# Prepare Year-Month
df_filtered['year_month'] = df_filtered['transaction_date'].dt.to_period('M').astype(str)

# Aggregate monthly per merchant
monthly = df_filtered.groupby(['merchant_id','year_month']).agg(
    txn_count=('transaction_id','count'),
    total_amount=('amount','sum')
).reset_index().sort_values(['merchant_id','year_month'])

# Calculate MoM/QoQ/YoY growth
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

# Calculate CAGR
n_years = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days / 365.25
merchant_summary['CAGR_num'] = ((merchant_summary['end_amt'] / merchant_summary['start_amt']) ** (1/n_years) -1) * 100

# Select top/bottom 10
if top_bottom.lower().startswith('top'):
    df_plot = merchant_summary.sort_values('avg_QoQ_txn', ascending=False).head(10)
else:
    df_plot = merchant_summary.sort_values('avg_QoQ_txn', ascending=True).head(10)

# ------------------------------
# Build Plotly Figure
# ------------------------------
fig = go.Figure()
colors = {'Avg MoM Growth':'royalblue','Avg QoQ Growth':'crimson','Avg YoY Growth':'green'}

metric_map = {
    'Avg MoM Growth':'avg_MoM_txn',
    'Avg QoQ Growth':'avg_QoQ_txn',
    'Avg YoY Growth':'avg_YoY_txn'
}

for metric in selected_metrics:
    fig.add_trace(go.Bar(
        x=df_plot['merchant_id'],
        y=df_plot[metric_map[metric]],
        name=metric,
        marker_color=colors.get(metric,'grey')
    ))

# Add CAGR line
fig.add_trace(go.Scatter(
    x=df_plot['merchant_id'],
    y=df_plot['CAGR_num'],
    mode='lines+markers',
    name='CAGR',
    line=dict(color='orange', width=3),
    yaxis='y2'
))

fig.update_layout(
    title=f"{top_bottom} Merchants - Growth Metrics",
    xaxis_title="Merchant ID",
    yaxis_title="Growth (%) (Bars)",
    yaxis2=dict(
        title="CAGR (%)",
        overlaying='y',
        side='right'
    ),
    barmode='group',
    template='plotly_white'
)

# ------------------------------
# Display
# ------------------------------
st.plotly_chart(fig, use_container_width=True)

# Display table
st.subheader("Merchant Summary Table")
st.text(tabulate(df_plot, headers='keys', tablefmt='psql', showindex=False))
