import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Support Cases Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display logos
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.image("./img/optimus_logo.png", width=150)
with col2:
    st.title("Support Cases Dashboard")
with col3:
    st.image("./img/cynet_logo.png", width=150)
st.divider()


# Load data from CSV
@st.cache_data
def load_data(csv_path):
    """Load support cases data from CSV file"""
    if not os.path.exists(csv_path):
        st.error(f"CSV file not found at {csv_path}")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        # Convert Date/Time Opened to datetime if it exists
        if 'Date/Time Opened' in df.columns:
            df['Date/Time Opened'] = pd.to_datetime(df['Date/Time Opened'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        return None

# Path to CSV file (in the same directory as the script)
csv_file_path = os.path.join(os.path.dirname(__file__), "support_cases.csv")

# Load the data
df = load_data(csv_file_path)

if df is None:
    st.stop()

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Status filter
status_options = ["All"] + sorted(df['Status'].unique().tolist())
selected_status = st.sidebar.multiselect(
    "Status",
    status_options,
    default=["All"]
)

# Severity filter
severity_options = ["All"] + sorted(df['Severity'].unique().tolist())
selected_severity = st.sidebar.multiselect(
    "Severity",
    severity_options,
    default=["All"]
)

# Search box
search_term = st.sidebar.text_input("Search by Case # or Subject", "")

# Apply filters
filtered_df = df.copy()

if "All" not in selected_status:
    filtered_df = filtered_df[filtered_df['Status'].isin(selected_status)]

if "All" not in selected_severity:
    filtered_df = filtered_df[filtered_df['Severity'].isin(selected_severity)]

if search_term:
    filtered_df = filtered_df[
        (filtered_df['Case #'].astype(str).str.contains(search_term, case=False)) |
        (filtered_df['Subject'].str.contains(search_term, case=False))
    ]

# Display metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Cases", len(filtered_df))

with col2:
    high_severity = len(filtered_df[filtered_df['Severity'] == 'High'])
    st.metric("High Severity", high_severity)

with col3:
    in_progress = len(filtered_df[filtered_df['Status'] == 'In Progress'])
    st.metric("In Progress", in_progress)

with col4:
    open_cases = len(filtered_df[filtered_df['Status'] == 'Open'])
    st.metric("Open Cases", open_cases)

st.divider()

# Analytics Section
st.subheader("📊 Analytics & Visualizations")

# Create two columns for charts
col1, col2 = st.columns(2)

# Chart 1: Status Distribution (Pie Chart)
with col1:
    status_counts = filtered_df['Status'].value_counts()
    fig_status = px.pie(
        values=status_counts.values,
        names=status_counts.index,
        title="Cases by Status",
        hole=0.3
    )
    fig_status.update_layout(height=400)
    st.plotly_chart(fig_status, use_container_width=True)

# Chart 2: Severity Distribution (Pie Chart)
with col2:
    severity_counts = filtered_df['Severity'].value_counts()
    fig_severity = px.pie(
        values=severity_counts.values,
        names=severity_counts.index,
        title="Cases by Severity",
        color_discrete_map={'High': '#FF6B6B', 'Medium': '#FFA500', 'Low': '#4CAF50'},
        hole=0.3
    )
    fig_severity.update_layout(height=400)
    st.plotly_chart(fig_severity, use_container_width=True)

# Chart 3: Status vs Severity (Stacked Bar Chart)
col1, col2 = st.columns([2, 1])

with col1:
    status_severity = pd.crosstab(filtered_df['Status'], filtered_df['Severity'])
    fig_status_severity = go.Figure()
    
    for severity in ['High', 'Medium', 'Low']:
        if severity in status_severity.columns:
            fig_status_severity.add_trace(go.Bar(
                name=severity,
                x=status_severity.index,
                y=status_severity[severity],
                marker_color={'High': '#FF6B6B', 'Medium': '#FFA500', 'Low': '#4CAF50'}.get(severity, '#999')
            ))
    
    fig_status_severity.update_layout(
        title="Cases by Status and Severity",
        barmode='stack',
        xaxis_title="Status",
        yaxis_title="Number of Cases",
        height=400,
        hovermode='x unified'
    )
    st.plotly_chart(fig_status_severity, use_container_width=True)

# Chart 4: Cases Over Time (Line Chart)
with col2:
    # Group by date and count cases
    cases_by_date = filtered_df.groupby(filtered_df['Date/Time Opened'].dt.date).size().reset_index(name='count')
    cases_by_date.columns = ['Date', 'Cases']
    
    fig_timeline = px.line(
        cases_by_date,
        x='Date',
        y='Cases',
        title="Cases Opened Over Time",
        markers=True
    )
    fig_timeline.update_layout(height=400)
    st.plotly_chart(fig_timeline, use_container_width=True)

# Chart 5: Case Count by Status (Horizontal Bar Chart)
col1, col2 = st.columns([1, 2])

with col2:
    status_counts_sorted = filtered_df['Status'].value_counts().sort_values()
    fig_status_bar = px.bar(
        x=status_counts_sorted.values,
        y=status_counts_sorted.index,
        title="Case Count by Status",
        labels={'x': 'Number of Cases', 'y': 'Status'},
        orientation='h'
    )
    fig_status_bar.update_layout(height=300)
    st.plotly_chart(fig_status_bar, use_container_width=True)

st.divider()

# Display cases
st.subheader(f"📌 Cases ({len(filtered_df)})")

# Create a more readable display
for idx, row in filtered_df.iterrows():
    # Color code based on severity
    if row['Severity'] == 'High':
        severity_color = "🔴"
    elif row['Severity'] == 'Medium':
        severity_color = "🟡"
    else:
        severity_color = "🟢"
    
    with st.container(border=True):
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.markdown(f"**Case #{row['Case #']}**")
            st.markdown(f"{severity_color} {row['Severity']}")
        
        with col2:
            st.markdown(f"**{row['Subject']}**")
            st.markdown(f"*Status:* {row['Status']}")
        
        # Date and Link row
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if pd.notna(row.get('Date/Time Opened')):
                date_str = pd.Timestamp(row['Date/Time Opened']).strftime('%b %d, %Y %I:%M %p')
                st.markdown(f"*Opened:* {date_str}")
        
        with col2:
            if pd.notna(row.get('Link')):
                st.markdown(f"[🔗 View Case]({row['Link']})")
        
        # Key Details
        if pd.notna(row.get('Key Details')):
            st.markdown(f"**Details:** {row['Key Details']}")

st.divider()

# Download data as CSV
st.subheader("📥 Export Data")
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="Download as CSV",
    data=csv,
    file_name="support_cases.csv",
    mime="text/csv"
)

# Display table view
st.subheader("📊 Table View")

# Format the dataframe for display
display_df = filtered_df.copy()
if 'Date/Time Opened' in display_df.columns:
    display_df['Date/Time Opened'] = display_df['Date/Time Opened'].dt.strftime('%b %d, %Y %I:%M %p')

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Link": st.column_config.LinkColumn("Case Link")
    }
)
