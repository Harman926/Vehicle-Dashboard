import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # kept if you extend later
from plotly.subplots import make_subplots  # kept if you extend later
from datetime import datetime
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Initialize app data if needed (for cloud deployment)
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from init_app import initialize_app
    initialize_app()
except Exception as e:
    st.warning(f"Initialization warning: {e}")

from data_processor import VehicleDataProcessor
from database import DatabaseManager

# ---------- Visual theme (distinct from defaults) ----------
TEMPLATE = "plotly_white"
COLOR_SEQ = [
    "#0EA5E9", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6",
    "#14B8A6", "#E11D48", "#A3E635", "#F97316", "#10B981"
]

def style_figure(fig, height=500):
    fig.update_layout(
        template=TEMPLATE,
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(title='', orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# Page configuration
st.set_page_config(
    page_title="Vehicle Registration Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (new palette + card look)
st.markdown("""
<style>
    :root {
        --brand-1: #0ea5e9;  /* sky-500 */
        --brand-2: #8b5cf6;  /* violet-500 */
        --ink-1:   #0f172a;  /* slate-900 */
        --ink-2:   #334155;  /* slate-700 */
        --soft:    #f1f5f9;  /* slate-100 */
    }
    .main-header {
        font-size: 2.6rem;
        background: linear-gradient(90deg, var(--brand-1), var(--brand-2));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        text-align: center;
        margin-bottom: 1.25rem;
        font-weight: 800;
        letter-spacing: .3px;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(14,165,233,.14) 0%, rgba(139,92,246,.14) 100%);
        padding: 1rem;
        border-radius: 14px;
        color: var(--ink-1);
        text-align: center;
        border: 1px solid rgba(15,23,42,.06);
    }
    .stMetric label, .stSelectbox label, .stMultiSelect label {
        font-weight: 600;
        color: var(--ink-2);
    }
    .sidebar .sidebar-content { background-color: #ffffff; }
    .stTabs [role="tab"] { padding: 10px 14px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

class VehicleDashboard:
    """
    Main dashboard class (names intact to avoid breaking imports elsewhere)
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.processor = VehicleDataProcessor()

    def run(self):
        """Main dashboard function"""
        st.markdown('<h1 class="main-header">🚗 Vehicle Registration Analytics Dashboard</h1>', unsafe_allow_html=True)
        st.markdown("---")

        self.create_sidebar()

        if not self.check_data_availability():
            return

        self.create_main_content()

    def check_data_availability(self):
        """Check if data is available in the database"""
        stats = self.db.get_summary_stats()
        if stats.get('total_records', 0) == 0:
            st.error("No data found in the database!")
            st.info("Please run the data collector first: `python src/data_collector.py`")
            with st.expander("How to generate sample data"):
                st.code("""
# Navigate to project directory
cd vehicle-dashboard

# Install dependencies
pip install -r requirements.txt

# Generate sample data
python src/data_collector.py

# Run the dashboard
streamlit run src/dashboard.py
                """)
            return False
        return True

    def create_sidebar(self):
        """Create sidebar with filters"""
        st.sidebar.header("⚙️ Filters")

        # Date range
        date_range = self.db.get_date_range()
        if date_range['min_date'] and date_range['max_date']:
            min_date = pd.to_datetime(date_range['min_date']).date()
            max_date = pd.to_datetime(date_range['max_date']).date()

            st.sidebar.subheader("📅 Date Range")
            start_date = st.sidebar.date_input("Start", min_date, min_value=min_date, max_value=max_date)
            end_date = st.sidebar.date_input("End", max_date, min_value=min_date, max_value=max_date)

            st.session_state.start_date = start_date.strftime('%Y-%m-%d')
            st.session_state.end_date = end_date.strftime('%Y-%m-%d')

        # Vehicle categories
        st.sidebar.subheader("🚙 Categories")
        categories = self.db.get_unique_values('vehicle_category')
        st.session_state.selected_categories = st.sidebar.multiselect(
            "Choose categories", categories, default=categories
        )

        # Manufacturers
        st.sidebar.subheader("🏭 Manufacturers")
        manufacturers = self.db.get_unique_values('manufacturer')
        st.session_state.selected_manufacturers = st.sidebar.multiselect(
            "Pick manufacturers", manufacturers, default=manufacturers[:8]  # slightly different default
        )

        # States
        st.sidebar.subheader("🗺️ States")
        states = self.db.get_unique_values('state_name')
        st.session_state.selected_states = st.sidebar.multiselect(
            "Select states", states, default=states[:6]  # slightly different default
        )

    def get_filtered_data(self):
        """
        Get filtered data based on sidebar selections (kept method name)
        """
        start_date = st.session_state.get('start_date')
        end_date = st.session_state.get('end_date')
        categories = st.session_state.get('selected_categories', [])
        manufacturers = st.session_state.get('selected_manufacturers', [])
        states = st.session_state.get('selected_states', [])

        # Convert state names to codes for database query
        if states:
            all_states = self.db.execute_query("SELECT DISTINCT state_code, state_name FROM vehicle_registrations")
            state_map = dict(zip(all_states['state_name'], all_states['state_code']))
            state_codes = [state_map.get(s) for s in states if state_map.get(s)]
        else:
            state_codes = None

        return self.db.get_filtered_data(
            start_date=start_date,
            end_date=end_date,
            vehicle_categories=categories if categories else None,
            manufacturers=manufacturers if manufacturers else None,
            states=state_codes
        )

    def create_main_content(self):
        """Create main dashboard content"""
        data = self.get_filtered_data()

        if data.empty:
            st.warning("No data available for the selected filters.")
            return

        # Ensure consistent date column for sorting/plots
        if {'year', 'month'}.issubset(data.columns):
            data = data.copy()
            data['period'] = pd.to_datetime(
                data[['year', 'month']].assign(day=1),
                errors='coerce'
            )

        self.display_key_metrics(data)

        tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "📊 Growth Analysis", "🏆 Market Share", "📋 Detailed Data"])
        with tab1:
            self.create_trends_tab(data)
        with tab2:
            self.create_growth_tab(data)
        with tab3:
            self.create_market_share_tab(data)
        with tab4:
            self.create_data_tab(data)

    def display_key_metrics(self, data: pd.DataFrame):
        """Display key performance metrics"""
        st.subheader("📊 Key Performance Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_registrations = int(data['registrations'].sum())
            st.metric("Total Registrations", f"{total_registrations:,}")

        with col2:
            unique_manufacturers = int(data['manufacturer'].nunique())
            st.metric("Active Manufacturers", unique_manufacturers)

        with col3:
            monthly_totals = (data
                              .groupby(['year', 'month'], as_index=False)['registrations']
                              .sum()
                              .sort_values(['year', 'month']))
            avg_monthly = monthly_totals['registrations'].mean() if not monthly_totals.empty else 0
            st.metric("Avg Monthly Registrations", f"{avg_monthly:,.0f}")

        with col4:
            if 'period' in data.columns:
                latest_month_val = (data.groupby('period')['registrations']
                                    .sum()
                                    .sort_index()
                                    .iloc[-1])
            else:
                latest_month_val = (data.groupby(['year', 'month'])['registrations']
                                    .sum()
                                    .iloc[-1])
            st.metric("Latest Month Registrations", f"{int(latest_month_val):,}")

    # ---------- TABS (kept names; changed visuals & internals) ----------

    def create_trends_tab(self, data: pd.DataFrame):
        """Create trends analysis tab"""
        st.subheader("📈 Registration Trends")

        # Monthly trends by category
        monthly = (data
                   .groupby(['year', 'month', 'vehicle_category'], as_index=False)['registrations']
                   .sum())
        monthly['date'] = pd.to_datetime(monthly[['year', 'month']].assign(day=1), errors='coerce')

        fig = px.line(
            monthly,
            x='date',
            y='registrations',
            color='vehicle_category',
            title='Monthly Registration Trends by Vehicle Category',
            labels={'registrations': 'Registrations', 'date': 'Date'},
            color_discrete_sequence=COLOR_SEQ
        )
        fig.update_traces(mode='lines+markers', marker=dict(size=6), line=dict(width=2.4))
        style_figure(fig)
        st.plotly_chart(fig, use_container_width=True)

        # Top manufacturers trend
        st.subheader("🏭 Top Manufacturers Trend")

        top_mfr = (data.groupby('manufacturer')['registrations'].sum()
                   .nlargest(5).index)
        mfr_monthly = (data[data['manufacturer'].isin(top_mfr)]
                       .groupby(['year', 'month', 'manufacturer'], as_index=False)['registrations'].sum())
        mfr_monthly['date'] = pd.to_datetime(mfr_monthly[['year', 'month']].assign(day=1), errors='coerce')

        fig2 = px.line(
            mfr_monthly,
            x='date',
            y='registrations',
            color='manufacturer',
            title='Monthly Trends — Top 5 Manufacturers',
            labels={'registrations': 'Registrations', 'date': 'Date'},
            color_discrete_sequence=COLOR_SEQ
        )
        fig2.update_traces(mode='lines+markers', marker=dict(size=6), line=dict(width=2.4))
        style_figure(fig2)
        st.plotly_chart(fig2, use_container_width=True)

    def create_growth_tab(self, data: pd.DataFrame):
        """Create growth analysis tab"""
        st.subheader("📊 Growth Analysis")

        col1, col2 = st.columns(2)

        # YoY
        with col1:
            st.subheader("Year-over-Year Growth")
            yoy_data = self.processor.calculate_yoy_growth(data)
            if not yoy_data.empty:
                latest_yoy = (yoy_data.groupby('vehicle_category', as_index=False)['yoy_growth']
                              .last()
                              .dropna())
                if not latest_yoy.empty:
                    fig_yoy = px.bar(
                        latest_yoy,
                        x='vehicle_category',
                        y='yoy_growth',
                        title='Latest YoY Growth Rate by Category',
                        labels={'yoy_growth': 'YoY Growth (%)', 'vehicle_category': 'Category'},
                        color='vehicle_category',
                        color_discrete_sequence=COLOR_SEQ
                    )
                    style_figure(fig_yoy, height=420)
                    st.plotly_chart(fig_yoy, use_container_width=True)
                else:
                    st.info("Insufficient data for YoY calculation")
            else:
                st.info("No YoY data available")

        # QoQ
        with col2:
            st.subheader("Quarter-over-Quarter Growth")
            qoq_data = self.processor.calculate_qoq_growth(data)
            if not qoq_data.empty:
                latest_qoq = (qoq_data.groupby('vehicle_category', as_index=False)['qoq_growth']
                              .last()
                              .dropna())
                if not latest_qoq.empty:
                    fig_qoq = px.bar(
                        latest_qoq,
                        x='vehicle_category',
                        y='qoq_growth',
                        title='Latest QoQ Growth Rate by Category',
                        labels={'qoq_growth': 'QoQ Growth (%)', 'vehicle_category': 'Category'},
                        color='vehicle_category',
                        color_discrete_sequence=COLOR_SEQ
                    )
                    style_figure(fig_qoq, height=420)
                    st.plotly_chart(fig_qoq, use_container_width=True)
                else:
                    st.info("Insufficient data for QoQ calculation")
            else:
                st.info("No QoQ data available")

        # Growth trends over time (YoY)
        st.subheader("Growth Trends Over Time")
        if 'yoy_data' in locals() and not yoy_data.empty:
            yoy_trend = (yoy_data.groupby(['year_month', 'vehicle_category'], as_index=False)['yoy_growth']
                         .mean())
            # Make a proper date from year_month (e.g., '2024-03')
            yoy_trend['date'] = pd.to_datetime(yoy_trend['year_month'].astype(str), errors='coerce')

            fig_trend = px.line(
                yoy_trend,
                x='date',
                y='yoy_growth',
                color='vehicle_category',
                title='YoY Growth Trend by Category',
                labels={'yoy_growth': 'YoY Growth (%)', 'date': 'Period'},
                color_discrete_sequence=COLOR_SEQ
            )
            fig_trend.update_traces(mode='lines+markers', marker=dict(size=5), line=dict(width=2.2))
            style_figure(fig_trend)
            st.plotly_chart(fig_trend, use_container_width=True)

    def create_market_share_tab(self, data: pd.DataFrame):
        """Create market share analysis tab"""
        st.subheader("🏆 Market Share Analysis")

        market_share = self.processor.calculate_market_share(data)

        if not market_share.empty:
            # Latest market share by category
            latest_period = market_share['year_month'].max()
            latest_share = market_share[market_share['year_month'] == latest_period]

            for category in latest_share['vehicle_category'].unique():
                st.subheader(f"{category} — Market Share")
                cat = (latest_share[latest_share['vehicle_category'] == category]
                       .nlargest(10, 'market_share'))

                fig = px.pie(
                    cat,
                    values='market_share',
                    names='manufacturer',
                    title=f'{category} Market Share (Top 10)',
                    color='manufacturer',
                    color_discrete_sequence=COLOR_SEQ
                )
                style_figure(fig, height=420)
                st.plotly_chart(fig, use_container_width=True)

        # Market share trends (Top 3 per category)
        st.subheader("Market Share Trends")
        if not market_share.empty:
            top3 = (market_share
                    .groupby(['vehicle_category', 'manufacturer'], as_index=False)['market_share']
                    .mean()
                    .sort_values(['vehicle_category', 'market_share'], ascending=[True, False])
                    .groupby('vehicle_category', as_index=False).head(3))

            for category in top3['vehicle_category'].unique():
                chosen = top3[top3['vehicle_category'] == category]['manufacturer']
                trend = market_share[
                    (market_share['vehicle_category'] == category) &
                    (market_share['manufacturer'].isin(chosen))
                ].copy()
                trend['date'] = pd.to_datetime(trend['year_month'].astype(str), errors='coerce')

                fig = px.line(
                    trend,
                    x='date',
                    y='market_share',
                    color='manufacturer',
                    title=f'{category} — Market Share Trends (Top 3)',
                    labels={'market_share': 'Market Share (%)', 'date': 'Period'},
                    color_discrete_sequence=COLOR_SEQ
                )
                fig.update_traces(mode='lines+markers', marker=dict(size=5), line=dict(width=2.2))
                style_figure(fig, height=420)
                st.plotly_chart(fig, use_container_width=True)

    def create_data_tab(self, data: pd.DataFrame):
        """Create detailed data tab"""
        st.subheader("📋 Detailed Registration Data")

        # Summary statistics
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Summary by Category")
            category_summary = (data.groupby('vehicle_category')
                                .agg(Total=('registrations', 'sum'),
                                     Average=('registrations', 'mean'),
                                     Records=('registrations', 'count'))
                                .round(2))
            st.dataframe(category_summary)

        with col2:
            st.subheader("Top States by Total Registrations")
            state_summary = (data.groupby('state_name')
                             .agg(Total_Registrations=('registrations', 'sum'))
                             .sort_values('Total_Registrations', ascending=False)
                             .head(10))
            st.dataframe(state_summary)

        # Raw data with search
        st.subheader("Raw Data")
        search_term = st.text_input("Search (manufacturer, state, category)")

        display_data = data.copy()
        if search_term:
            s = str(search_term)
            mask = (
                display_data['manufacturer'].astype(str).str.contains(s, case=False, na=False) |
                display_data['state_name'].astype(str).str.contains(s, case=False, na=False) |
                display_data['vehicle_category'].astype(str).str.contains(s, case=False, na=False)
            )
            display_data = display_data[mask]

        # Sort for readability if 'period' exists
        if 'period' in display_data.columns:
            display_data = display_data.sort_values(['period', 'state_name', 'vehicle_category', 'manufacturer'])
        else:
            display_data = display_data.sort_values(['year', 'month', 'state_name', 'vehicle_category', 'manufacturer'])

        st.dataframe(display_data, use_container_width=True)

        # Download
        csv = display_data.drop(columns=['period'], errors='ignore').to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"vehicle_registrations_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def main():
    """Main function to run the dashboard"""
    dashboard = VehicleDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
