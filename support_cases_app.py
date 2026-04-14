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
    st.title("📋 Support Cases Dashboard")
    st.markdown("A comprehensive view of all support cases with filtering and search capabilities.")

with col3:
    st.image("./img/cynet_logo.png", width=150)

# Load data from CSV
@st.cache_data
def load_data(csv_path):
    """Load support cases data from CSV file"""
    if not os.path.exists(csv_path):
        st.error(f"CSV file not found at {csv_path}")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        # Convert date columns to datetime if they exist
        if 'Date/Time Opened' in df.columns:
            df['Date/Time Opened'] = pd.to_datetime(df['Date/Time Opened'], errors='coerce')
        if 'Last Update Date' in df.columns:
            df['Last Update Date'] = pd.to_datetime(df['Last Update Date'], errors='coerce')
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

# Initialize session state for edited data
if 'edited_df' not in st.session_state:
    st.session_state.edited_df = df.copy()

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

# Contact Name filter
if 'Contact Name' in df.columns:
    contact_options = ["All"] + sorted(df['Contact Name'].dropna().unique().tolist())
    selected_contact = st.sidebar.multiselect("Contact", contact_options, default=["All"])
else:
    selected_contact = ["All"]

# Data refresh date
if 'Data Refresh Date' in df.columns:
    refresh_date = df['Data Refresh Date'].dropna().iloc[-1] if not df['Data Refresh Date'].dropna().empty else None
    if refresh_date:
        st.sidebar.divider()
        st.sidebar.caption(f"Data as of: {refresh_date}")

# Apply filters with error handling
filtered_df = st.session_state.edited_df.copy()

# Handle Status filter
if selected_status and "All" not in selected_status:
    filtered_df = filtered_df[filtered_df['Status'].isin(selected_status)]
elif not selected_status:
    # If no status selected, show all
    filtered_df = st.session_state.edited_df.copy()

# Handle Severity filter
if selected_severity and "All" not in selected_severity:
    filtered_df = filtered_df[filtered_df['Severity'].isin(selected_severity)]
elif not selected_severity:
    # If no severity selected, show all
    filtered_df = st.session_state.edited_df.copy()

# Handle Contact Name filter
if selected_contact and "All" not in selected_contact and 'Contact Name' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Contact Name'].isin(selected_contact)]

# Handle search term
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
    if len(filtered_df) > 0:
        status_counts = filtered_df['Status'].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Cases by Status",
            hole=0.3
        )
        fig_status.update_layout(height=400)
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("No data available for Status distribution")

# Chart 2: Severity Distribution (Pie Chart)
with col2:
    if len(filtered_df) > 0:
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
    else:
        st.info("No data available for Severity distribution")

# Chart 3: Status vs Severity (Stacked Bar Chart)
col1, col2 = st.columns([2, 1])

with col1:
    if len(filtered_df) > 0:
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
    else:
        st.info("No data available for Status vs Severity")

# Chart 4: Cases Over Time (Line Chart)
with col2:
    if len(filtered_df) > 0 and pd.notna(filtered_df['Date/Time Opened']).any():
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
    else:
        st.info("No date data available for timeline")

# Chart 5: Case Count by Status (Horizontal Bar Chart)
col1, col2 = st.columns([1, 2])

with col2:
    if len(filtered_df) > 0:
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
    else:
        st.info("No data available for Status count")

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
            if pd.notna(row.get('Contact Name')):
                st.markdown(f"*{row['Contact Name']}*")

        with col2:
            st.markdown(f"**{row['Subject']}**")
            st.markdown(f"*Status:* {row['Status']}")

        # Date and Link row
        col1, col2 = st.columns([2, 1])

        with col1:
            if pd.notna(row.get('Date/Time Opened')):
                date_str = pd.Timestamp(row['Date/Time Opened']).strftime('%b %d, %Y %I:%M %p')
                st.markdown(f"*Opened:* {date_str}")
            if pd.notna(row.get('Last Update Date')):
                update_str = pd.Timestamp(row['Last Update Date']).strftime('%b %d, %Y %I:%M %p')
                st.markdown(f"*Last Update:* {update_str}")

        with col2:
            if pd.notna(row.get('Link')):
                st.markdown(f"[🔗 View Case]({row['Link']})")

        # Summary
        if pd.notna(row.get('Summary')):
            st.markdown(f"**Summary:** {row['Summary']}")

st.divider()

# Data Management Section
st.subheader("⚙️ Data Management")

# Tabs for different data operations
tab1, tab2, tab3 = st.tabs(["📥 Export Data", "✏️ Edit Data", "📊 View/Edit Table"])

with tab1:
    st.markdown("**Download filtered data as CSV**")
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="support_cases_filtered.csv",
        mime="text/csv"
    )

with tab2:
    st.markdown("**Add a new case**")
    
    col1, col2 = st.columns(2)

    with col1:
        new_case_num = st.text_input("Case #", key="new_case_num")
        new_subject = st.text_input("Subject", key="new_subject")
        new_status = st.selectbox("Status", sorted(df['Status'].unique()), key="new_status")
        new_contact = st.text_input("Contact Name (optional)", key="new_contact")

    with col2:
        new_severity = st.selectbox("Severity", sorted(df['Severity'].unique()), key="new_severity")
        new_date = st.date_input("Date/Time Opened", key="new_date")
        new_link = st.text_input("Link (optional)", key="new_link")
        new_update_date = st.date_input("Last Update Date", key="new_update_date")

    new_details = st.text_area("Summary", key="new_details")

    if st.button("Add Case"):
        if new_case_num and new_subject:
            new_row = pd.DataFrame({
                'Case #': [new_case_num],
                'Subject': [new_subject],
                'Status': [new_status],
                'Severity': [new_severity],
                'Date/Time Opened': [pd.Timestamp(new_date)],
                'Link': [new_link if new_link else None],
                'Summary': [new_details if new_details else None],
                'Contact Name': [new_contact if new_contact else None],
                'Last Update Date': [pd.Timestamp(new_update_date)],
                'Data Refresh Date': [datetime.today().strftime('%m/%d/%Y')]
            })
            st.session_state.edited_df = pd.concat([st.session_state.edited_df, new_row], ignore_index=True)
            st.success("✅ Case added successfully!")
            st.rerun()
        else:
            st.error("Please fill in Case # and Subject")

with tab3:
    st.markdown("**View and edit all cases**")
    
    # Prepare data for editing
    edit_df = st.session_state.edited_df.copy()
    
    # Format date columns for display
    if 'Date/Time Opened' in edit_df.columns:
        edit_df['Date/Time Opened'] = edit_df['Date/Time Opened'].dt.strftime('%Y-%m-%d')
    if 'Last Update Date' in edit_df.columns:
        edit_df['Last Update Date'] = edit_df['Last Update Date'].dt.strftime('%Y-%m-%d')
    
    # Use data_editor for inline editing
    edited_data = st.data_editor(
        edit_df,
        use_container_width=True,
        num_rows="dynamic",
        key="data_editor"
    )
    
    # Save changes button
    if st.button("💾 Save Changes"):
        # Convert date strings back to datetime
        if 'Date/Time Opened' in edited_data.columns:
            edited_data['Date/Time Opened'] = pd.to_datetime(edited_data['Date/Time Opened'], errors='coerce')
        if 'Last Update Date' in edited_data.columns:
            edited_data['Last Update Date'] = pd.to_datetime(edited_data['Last Update Date'], errors='coerce')
        
        st.session_state.edited_df = edited_data
        
        # Save to CSV
        edited_data.to_csv(csv_file_path, index=False)
        st.success("✅ Changes saved to CSV!")
        st.rerun()

st.divider()

# Display table view
st.subheader("📊 Table View")

# Format the dataframe for display
display_df = filtered_df.copy()
if 'Date/Time Opened' in display_df.columns:
    display_df['Date/Time Opened'] = display_df['Date/Time Opened'].dt.strftime('%b %d, %Y %I:%M %p')
if 'Last Update Date' in display_df.columns:
    display_df['Last Update Date'] = display_df['Last Update Date'].dt.strftime('%b %d, %Y %I:%M %p')

if len(display_df) > 0:
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Case Link")
        }
    )
else:
    st.info("No cases to display with current filters")
