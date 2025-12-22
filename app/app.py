import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import os
import json
from math import radians, sin, cos, sqrt, atan2
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="LCE Hunger Detection Platform",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "LCE Hunger Detection Platform - Powered by Databricks"
    }
)

# Dark theme professional styling
st.markdown("""
<style>
    /* Import professional font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global dark theme */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        font-family: 'Inter', sans-serif;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(90deg, #FF6000 0%, #FF8C00 100%);
        padding: 2rem 2rem 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(255, 96, 0, 0.4);
    }

    .logo-title {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.5rem;
    }

    .lce-logo {
        background: white;
        color: #FF6000;
        font-weight: 800;
        font-size: 2rem;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        letter-spacing: 2px;
    }

    h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 2.5rem !important;
        margin: 0 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .tagline {
        color: #e0e7ff;
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: 0.5rem;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: #1e293b;
        padding: 0.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        justify-content: center;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 500;
        font-size: 1rem;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #334155;
        color: #e0e7ff;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #FF6000 0%, #FF8C00 100%) !important;
        color: white !important;
    }

    /* Section headers */
    h2, h3 {
        color: #f1f5f9 !important;
        font-weight: 600 !important;
        margin-top: 2rem !important;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }

    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #475569;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }

    /* Dataframe styling */
    .stDataFrame {
        background-color: #1e293b;
        border-radius: 8px;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #FF6000 0%, #FF8C00 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        box-shadow: 0 4px 16px rgba(255, 96, 0, 0.4);
        transition: all 0.3s;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 96, 0, 0.6);
    }

    /* Slider */
    .stSlider {
        padding: 1rem 0;
    }

    /* Text and captions */
    p, .stCaption {
        color: #cbd5e1 !important;
    }

    /* Warning/info boxes */
    .stWarning, .stInfo, .stSuccess {
        background-color: #1e293b;
        border-radius: 8px;
    }

    /* Spinner */
    .stSpinner > div {
        border-color: #FF6000 !important;
    }

    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    [data-testid="collapsedControl"] {
        display: none;
    }

    /* Hide Streamlit header/toolbar */
    header[data-testid="stHeader"] {
        display: none;
    }

    /* Remove white space at top */
    .main .block-container {
        padding-top: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Get SQL connection using SDK's built-in SQL connector
@st.cache_resource
def get_connection():
    """Get SQL connection using WorkspaceClient's SQL connector"""
    hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    http_path = os.getenv("DATABRICKS_HTTP_PATH", "")
    warehouse_id = http_path.split("/")[-1] if http_path else "148ccb90800933a1"

    # Get the access token from Databricks Apps forwarded headers
    try:
        headers = st.context.headers
        user_token = headers.get("X-Forwarded-Access-Token") if headers else None
    except Exception as e:
        st.error(f"❌ Failed to read headers: {e}")
        return None

    if not user_token:
        st.error("❌ No access token found.")
        return None

    try:
        # Use WorkspaceClient to get SQL warehouse connection
        cfg = Config(
            host=f"https://{hostname}",
            token=user_token,
            auth_type="pat"
        )
        client = WorkspaceClient(config=cfg)

        # Get SQL warehouse connector from the client
        return client.warehouses.get(id=warehouse_id)

    except Exception as e:
        st.error(f"❌ Connection error: {e}")
        import traceback
        with st.expander("Full Error"):
            st.code(traceback.format_exc())
        return None

def get_user_token():
    """Get authentication token from environment variable"""
    token = os.getenv("DATABRICKS_TOKEN")

    if token:
        # Success message (only show once)
        if 'auth_message_shown' not in st.session_state:
            st.success("✓ Authenticated using PAT token")
            st.session_state.auth_message_shown = True
        return token

    st.error("❌ No DATABRICKS_TOKEN configured")
    st.info("Please ensure DATABRICKS_TOKEN is set in app.yaml")
    return None

@st.cache_data(ttl=600)
def query(_token, sql_query):
    """Execute SQL query using Databricks SQL Connector"""
    from databricks import sql as dbsql

    hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME", "e2-demo-west.cloud.databricks.com")
    http_path = os.getenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/75fd8278393d07eb")

    if not _token:
        st.error("No authentication token available")
        return pd.DataFrame()

    try:
        with dbsql.connect(
            server_hostname=hostname,
            http_path=http_path,
            access_token=_token,
            _use_arrow_native_complex_types=False
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=columns)

                # Convert numeric columns
                for col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='ignore')
                    except:
                        pass

                return df

    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__
        st.error(f"❌ Query failed: {error_type}: {error_str}")
        return pd.DataFrame()

def distance_miles(lat1, lon1, lat2, lon2):
    R = 3959
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

# Header with branding
col_logo, col_title = st.columns([1, 9])

with col_logo:
    st.image("Little-Caesars-man-logo.png", width=140)

with col_title:
    st.markdown("""
    <div class="main-header">
        <h1>LCE Hunger Detection Platform</h1>
        <div class="tagline">Powered by Databricks</div>
    </div>
    """, unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs(["Current Network", "Expansion Candidates", "Network Optimizer"])

with tab1:
    st.header("Current Store Network")

    # Get user token for OAuth
    user_token = get_user_token()
    if not user_token:
        st.error("Unable to authenticate. Please ensure you're logged in to Databricks.")
        st.stop()

    # Cache data in session state to avoid re-querying on toggle changes
    if 'tab1_data_loaded' not in st.session_state:
        with st.spinner("Loading store data..."):
            # First, get the base store data
            stores = query(user_token, """
                SELECT e.store_number,
                       COALESCE(e.city, r.city) as city,
                       COALESCE(e.state, r.state) as state,
                       e.latitude, e.longitude,
                       COALESCE(e.population, 0) as population,
                       COALESCE(e.total_retail_pois, 0) as total_retail_pois,
                       COALESCE(e.total_food_drink_pois, 0) as total_food_drink_pois,
                       COALESCE(e.total_leisure_pois, 0) as total_leisure_pois,
                       COALESCE(e.total_education_pois, 0) as total_education_pois,
                       COALESCE(e.total_healthcare_pois, 0) as total_healthcare_pois,
                       COALESCE(e.total_financial_pois, 0) as total_financial_pois,
                       COALESCE(e.total_tourism_pois, 0) as total_tourism_pois,
                       COALESCE(e.total_transportation_pois, 0) as total_transportation_pois,
                       r.address, r.zip_code
                FROM jdub_demo_aws.geo_silver.existing_stores_h3 e
                LEFT JOIN jdub_demo_aws.geo_bronze.lce_locations_mass r
                    ON e.store_number = r.store_number
            """)

            # Calculate total POI count
            if not stores.empty:
                stores['total_poi_count'] = (
                    stores['total_retail_pois'] + stores['total_food_drink_pois'] +
                    stores['total_leisure_pois'] + stores['total_education_pois'] +
                    stores['total_healthcare_pois'] + stores['total_financial_pois'] +
                    stores['total_tourism_pois'] + stores['total_transportation_pois']
                )

            # Load isochrones from isochrones_lce table (generated with OSRM)
            try:
                isochrones = query(user_token, """
                    SELECT location_id as store_number, ST_AsGeoJSON(geometry) as isochrone_geojson
                    FROM jdub_demo_aws.geo_silver.isochrones_lce
                """)
            except:
                isochrones = pd.DataFrame()

            # Load convenience store isochrones
            try:
                convenience_isochrones = query(user_token, """
                    SELECT location_id, ST_AsGeoJSON(geometry) as isochrone_geojson
                    FROM jdub_demo_aws.geo_silver.isochrones_convenience
                """)
            except:
                convenience_isochrones = pd.DataFrame()

            # Load convenience store locations
            try:
                convenience_stores = query(user_token, """
                    SELECT name, latitude, longitude, poi_category, poi_subcategory
                    FROM jdub_demo_aws.geo_silver.pois_convenience
                """)
            except:
                convenience_stores = pd.DataFrame()

            # Load competitor locations
            try:
                competitors = query(user_token, """
                    SELECT name, latitude, longitude, poi_category, poi_subcategory
                    FROM jdub_demo_aws.geo_silver.pois_competitors
                """)
            except:
                competitors = pd.DataFrame()

            # Load MA boundary
            ma_boundary = query(user_token, """
                SELECT ST_AsGeoJSON(geometry) as geometry_geojson
                FROM jdub_demo_aws.geo_bronze.census_states
                WHERE state_abbr = 'MA'
            """)

            # Store in session state
            st.session_state.tab1_stores = stores
            st.session_state.tab1_isochrones = isochrones
            st.session_state.tab1_convenience_isochrones = convenience_isochrones
            st.session_state.tab1_convenience_stores = convenience_stores
            st.session_state.tab1_competitors = competitors
            st.session_state.tab1_ma_boundary = ma_boundary
            st.session_state.tab1_data_loaded = True
    else:
        # Use cached data
        stores = st.session_state.tab1_stores
        isochrones = st.session_state.tab1_isochrones
        convenience_isochrones = st.session_state.tab1_convenience_isochrones
        convenience_stores = st.session_state.tab1_convenience_stores
        competitors = st.session_state.tab1_competitors
        ma_boundary = st.session_state.tab1_ma_boundary

    if not stores.empty:
        # Merge isochrone data if available
        if not isochrones.empty:
            stores = stores.merge(isochrones, on='store_number', how='left')
        else:
            stores['isochrone_geojson'] = None

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Stores", f"{len(stores):,}")
        col2.metric("Avg Population per Trade Area", f"{stores['population'].mean():,.0f}")
        col3.metric("Avg POI Count per Trade Area", f"{stores['total_poi_count'].mean():,.0f}")

        # Get toggle state from session state
        if 'show_trade_areas' not in st.session_state:
            st.session_state.show_trade_areas = False
        if 'show_convenience' not in st.session_state:
            st.session_state.show_convenience = False
        if 'show_competitors' not in st.session_state:
            st.session_state.show_competitors = False

        # Create 2-column layout: map (left) + table (right)
        map_col, table_col = st.columns([2, 1])

        with map_col:
            st.subheader("Store Locations")

            # Create base map centered on stores
            center_lat = stores['latitude'].mean()
            center_lon = stores['longitude'].mean()

            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=9,
                tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                attr='CartoDB'
            )

            # Add MA state boundary overlay
            if not ma_boundary.empty and ma_boundary.iloc[0]['geometry_geojson']:
                folium.GeoJson(
                    json.loads(ma_boundary.iloc[0]['geometry_geojson']),
                    style_function=lambda x: {
                        'color': '#FF6000',
                        'weight': 2,
                        'fillOpacity': 0,
                        'dashArray': '5, 5'
                    },
                    name='Massachusetts Boundary'
                ).add_to(m)

            # Add LCE trade area isochrones if toggle is on
            if st.session_state.show_trade_areas and 'isochrone_geojson' in stores.columns:
                for _, store in stores.iterrows():
                    if pd.notna(store.get('isochrone_geojson')) and store.get('isochrone_geojson'):
                        try:
                            folium.GeoJson(
                                json.loads(store['isochrone_geojson']),
                                style_function=lambda x: {
                                    'color': '#FF8C00',
                                    'weight': 1,
                                    'fillOpacity': 0.1,
                                    'fillColor': '#FF8C00'
                                }
                            ).add_to(m)
                        except:
                            pass

            # Add convenience store trade areas if toggle is on
            if st.session_state.show_convenience and not convenience_isochrones.empty:
                for _, conv in convenience_isochrones.iterrows():
                    if pd.notna(conv.get('isochrone_geojson')) and conv.get('isochrone_geojson'):
                        try:
                            folium.GeoJson(
                                json.loads(conv['isochrone_geojson']),
                                style_function=lambda x: {
                                    'color': '#3b82f6',
                                    'weight': 1,
                                    'fillOpacity': 0.08,
                                    'fillColor': '#3b82f6'
                                }
                            ).add_to(m)
                        except:
                            pass

            # Add convenience store markers with clustering if toggle is on (BLUE)
            if st.session_state.show_convenience and not convenience_stores.empty:
                conv_cluster = MarkerCluster(
                    name='Convenience Stores',
                    icon_create_function="""
                    function(cluster) {
                        return L.divIcon({
                            html: '<div style="background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%); color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-family: Inter, sans-serif; border: 3px solid #2563eb; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);"><span>' + cluster.getChildCount() + '</span></div>',
                            className: 'custom-cluster-icon',
                            iconSize: L.point(40, 40)
                        });
                    }
                    """
                ).add_to(m)
                for _, conv in convenience_stores.iterrows():
                    folium.CircleMarker(
                        location=[conv['latitude'], conv['longitude']],
                        radius=5,
                        popup=f"<b>{conv['name']}</b><br/>{conv.get('poi_subcategory', 'Convenience Store')}",
                        tooltip=f"Convenience: {conv['name']}",
                        color='#3b82f6',
                        fill=True,
                        fillColor='#60a5fa',
                        fillOpacity=0.7,
                        weight=2
                    ).add_to(conv_cluster)

            # Add competitor markers if toggle is on (NO clustering)
            if st.session_state.show_competitors and not competitors.empty:
                for _, comp in competitors.iterrows():
                    folium.CircleMarker(
                        location=[comp['latitude'], comp['longitude']],
                        radius=5,
                        popup=f"<b>{comp['name']}</b><br/>{comp.get('poi_subcategory', 'Pizza')}",
                        tooltip=f"Competitor: {comp['name']}",
                        color='#dc2626',
                        fill=True,
                        fillColor='#ef4444',
                        fillOpacity=0.7,
                        weight=2
                    ).add_to(m)

            # Add LCE store markers with clustering (GREEN)
            lce_cluster = MarkerCluster(
                name='LCE Stores',
                icon_create_function="""
                function(cluster) {
                    return L.divIcon({
                        html: '<div style="background: linear-gradient(135deg, #10b981 0%, #34d399 100%); color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-family: Inter, sans-serif; border: 3px solid #059669; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);"><span>' + cluster.getChildCount() + '</span></div>',
                        className: 'custom-cluster-icon',
                        iconSize: L.point(40, 40)
                    });
                }
                """
            ).add_to(m)

            for _, store in stores.iterrows():
                # Enhanced tooltip with all requested fields
                tooltip_text = f"""
                <div style="font-family: Arial; font-size: 12px;">
                    <b>Store {store['store_number']}</b><br/>
                    {store['address']}<br/>
                    {store['city']}, {store['state']} {store['zip_code']}<br/>
                    <hr style="margin: 5px 0;">
                    <b>Population:</b> {store['population']:,.0f}<br/>
                    <b>POI Count:</b> {store['total_poi_count']:,.0f}
                </div>
                """

                folium.CircleMarker(
                    location=[store['latitude'], store['longitude']],
                    radius=8,
                    popup=tooltip_text,
                    tooltip=tooltip_text,
                    color='#10b981',
                    fill=True,
                    fillColor='#34d399',
                    fillOpacity=0.8,
                    weight=2
                ).add_to(lce_cluster)

            # Display the map
            st_folium(m, use_container_width=True, height=500)

            # Toggles below the map
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            with col_t1:
                show_trade_areas = st.checkbox("Show LCE Trade Areas", value=st.session_state.show_trade_areas, key="toggle_trade_areas")
                if show_trade_areas != st.session_state.show_trade_areas:
                    st.session_state.show_trade_areas = show_trade_areas
                    st.rerun()
            with col_t2:
                show_convenience = st.checkbox("Show Convenience Stores", value=st.session_state.show_convenience, key="toggle_convenience")
                if show_convenience != st.session_state.show_convenience:
                    st.session_state.show_convenience = show_convenience
                    st.rerun()
            with col_t3:
                show_competitors = st.checkbox("Show Competitors", value=st.session_state.show_competitors, key="toggle_competitors")
                if show_competitors != st.session_state.show_competitors:
                    st.session_state.show_competitors = show_competitors
                    st.rerun()
            with col_t4:
                if st.button("🔄 Refresh Data", key="refresh_tab1"):
                    st.session_state.tab1_data_loaded = False
                    st.rerun()

        with table_col:
            st.markdown("""
            <h3 style='color: #FF6000; margin-bottom: 1rem; font-weight: 600;'>
                Top Locations by Trade Area
            </h3>
            """, unsafe_allow_html=True)

            # Create a styled table display
            stores_df = stores[['store_number', 'city', 'population', 'total_poi_count']].copy()
            stores_df = stores_df.sort_values('population', ascending=False).reset_index(drop=True)
            stores_df = stores_df.head(20)  # Top 20

            # Format values for display
            formatted_population = ['{:,.0f}'.format(val) for val in stores_df['population']]
            formatted_poi = ['{:,.0f}'.format(val) for val in stores_df['total_poi_count']]

            # Create Plotly table with Little Caesars branding
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=['<b>Store #</b>', '<b>City</b>', '<b>Population</b>', '<b>POI Count</b>'],
                    fill_color='#FF6000',  # Little Caesars orange
                    align='left',
                    font=dict(color='white', size=13, family='Inter'),
                    height=35
                ),
                cells=dict(
                    values=[
                        stores_df['store_number'],
                        stores_df['city'],
                        formatted_population,
                        formatted_poi
                    ],
                    fill_color=[['#2d2d2d', '#1a1a1a'] * len(stores_df)],  # Alternating dark rows
                    align='left',
                    font=dict(color='#f1f5f9', size=12, family='Inter'),
                    height=32
                )
            )])

            fig.update_layout(
                height=500,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("<h3 style='text-align: center; margin-bottom: 1rem;'>Trade Area Metrics</h3>", unsafe_allow_html=True)

        # Calculate values for POI breakdown
        retail_val = f"{stores['total_retail_pois'].mean():,.0f}"
        food_val = f"{stores['total_food_drink_pois'].mean():,.0f}"
        leisure_val = f"{stores['total_leisure_pois'].mean():,.0f}"
        total_poi_val = f"{stores['total_poi_count'].mean():,.0f}"

        # Clean card-based metrics (4 cards showing POI breakdown)
        driver_cols = st.columns(4)

        with driver_cols[0]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #FF6000; height: 160px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);">
                <div style="color: #999999; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Retail POIs</div>
                <div style="color: #666666; font-size: 11px; margin-bottom: 12px;">Avg per Trade Area</div>
                <div style="color: #FF6000; font-size: 36px; font-weight: 700;">{retail_val}</div>
            </div>
            """, unsafe_allow_html=True)

        with driver_cols[1]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #FF6000; height: 160px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);">
                <div style="color: #999999; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Food & Drink POIs</div>
                <div style="color: #666666; font-size: 11px; margin-bottom: 12px;">Avg per Trade Area</div>
                <div style="color: #FF6000; font-size: 36px; font-weight: 700;">{food_val}</div>
            </div>
            """, unsafe_allow_html=True)

        with driver_cols[2]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #FF6000; height: 160px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);">
                <div style="color: #999999; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Leisure POIs</div>
                <div style="color: #666666; font-size: 11px; margin-bottom: 12px;">Avg per Trade Area</div>
                <div style="color: #FF6000; font-size: 36px; font-weight: 700;">{leisure_val}</div>
            </div>
            """, unsafe_allow_html=True)

        with driver_cols[3]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #FF6000; height: 160px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);">
                <div style="color: #999999; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Total POIs</div>
                <div style="color: #666666; font-size: 11px; margin-bottom: 12px;">Avg per Trade Area</div>
                <div style="color: #FF6000; font-size: 36px; font-weight: 700;">{total_poi_val}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No data available. Ensure tables exist and permissions are granted.")

with tab2:
    # Get user token for OAuth
    user_token = get_user_token()
    if not user_token:
        st.error("Unable to authenticate. Please ensure you're logged in to Databricks.")
        st.stop()

    # Cache data in session state to avoid re-querying on toggle changes
    if 'tab2_data_loaded' not in st.session_state:
        with st.spinner("Loading candidate data..."):
            candidates = query(user_token, """
                SELECT h3_cell_id as store_number, 'TBD' as city, 'MA' as state, latitude, longitude,
                       predicted_annual_sales, population, total_poi as total_poi_count
                FROM jdub_demo_aws.geo_gold.expansion_candidates_h3_enhanced
            """)

            # Load MA boundary
            ma_boundary = query(user_token, """
                SELECT ST_AsGeoJSON(geometry) as geometry_geojson
                FROM jdub_demo_aws.geo_bronze.census_states
                WHERE state_abbr = 'MA'
            """)

            # Load current stores
            current_stores = query(user_token, """
                SELECT e.store_number,
                       COALESCE(e.city, r.city) as city,
                       COALESCE(e.state, r.state) as state,
                       e.latitude, e.longitude,
                       e.population,
                       r.address, r.zip_code
                FROM jdub_demo_aws.geo_silver.existing_stores_h3 e
                LEFT JOIN jdub_demo_aws.geo_bronze.lce_locations_mass r
                    ON e.store_number = r.store_number
            """)

            # Load convenience and competitor data
            try:
                convenience_stores_tab2 = query(user_token, """
                    SELECT name, latitude, longitude, poi_category, poi_subcategory
                    FROM jdub_demo_aws.geo_silver.pois_convenience
                """)
            except:
                convenience_stores_tab2 = pd.DataFrame()

            try:
                competitors_tab2 = query(user_token, """
                    SELECT name, latitude, longitude, poi_category, poi_subcategory
                    FROM jdub_demo_aws.geo_silver.pois_competitors
                """)
            except:
                competitors_tab2 = pd.DataFrame()

            # Store in session state
            st.session_state.tab2_candidates = candidates
            st.session_state.tab2_ma_boundary = ma_boundary
            st.session_state.tab2_current_stores = current_stores
            st.session_state.tab2_convenience_stores = convenience_stores_tab2
            st.session_state.tab2_competitors = competitors_tab2
            st.session_state.tab2_data_loaded = True
    else:
        # Use cached data
        candidates = st.session_state.tab2_candidates
        ma_boundary = st.session_state.tab2_ma_boundary
        current_stores = st.session_state.tab2_current_stores
        convenience_stores_tab2 = st.session_state.tab2_convenience_stores
        competitors_tab2 = st.session_state.tab2_competitors

    if not candidates.empty:
        # Create 2-column layout: metrics (left) + filters (right)
        metrics_col, filters_col = st.columns([1, 2])

        with metrics_col:
            st.markdown("### Expansion Candidate Locations")
            st.metric("Total Expansion Locations", f"{len(candidates):,}")
            st.metric("Avg Predicted Sales per Location", f"${candidates['predicted_annual_sales'].mean():,.0f}")

        with filters_col:
            st.markdown("### Expansion Location Filters")

            min_sales = st.slider(
                "Minimum Annual Sales per location for expansion feasibility",
                min_value=int(candidates['predicted_annual_sales'].min()),
                max_value=int(candidates['predicted_annual_sales'].max()),
                value=int(candidates['predicted_annual_sales'].min())
            )

            min_population = st.slider(
                "Target Population accessible to New Location (Per Trade Area)",
                min_value=int(candidates['population'].min()),
                max_value=int(candidates['population'].max()),
                value=int(candidates['population'].min())
            )

        # Apply filters
        filtered = candidates[candidates['predicted_annual_sales'] >= min_sales]
        filtered = filtered[filtered['population'] >= min_population]

        st.caption(f"Showing {len(filtered)} of {len(candidates)} expansion locations")

        st.subheader("Expansion Locations")

        # Add legend before map
        st.markdown("""
        <div style="background: #1e293b; padding: 12px; border-radius: 8px; margin-bottom: 16px;">
            <div style="font-weight: 600; margin-bottom: 8px; color: #f1f5f9;">Map Legend</div>
            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #34d399; border: 2px solid #10b981;"></div>
                    <span style="color: #e2e8f0; font-size: 13px;">Current LCE</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #fbbf24; border: 2px solid #f59e0b;"></div>
                    <span style="color: #e2e8f0; font-size: 13px;">Expansion Candidates</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 20px; height: 3px; background: #FF8C00; opacity: 0.3;"></div>
                    <span style="color: #e2e8f0; font-size: 13px;">LCE Trade Areas</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 20px; height: 3px; background: #3b82f6; opacity: 0.3;"></div>
                    <span style="color: #e2e8f0; font-size: 13px;">Convenience Trade Areas</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #60a5fa; border: 2px solid #3b82f6;"></div>
                    <span style="color: #e2e8f0; font-size: 13px;">Convenience (Toggle)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #ef4444; border: 2px solid #dc2626;"></div>
                    <span style="color: #e2e8f0; font-size: 13px;">Competitors (Toggle)</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Initialize session state for Tab 2 toggles
        if 'show_convenience_tab2' not in st.session_state:
            st.session_state.show_convenience_tab2 = False
        if 'show_competitors_tab2' not in st.session_state:
            st.session_state.show_competitors_tab2 = False

        m = folium.Map(
            location=[filtered['latitude'].mean(), filtered['longitude'].mean()],
            zoom_start=9,
            tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            attr='CartoDB'
        )

        # Add MA state boundary overlay
        if not ma_boundary.empty and ma_boundary.iloc[0]['geometry_geojson']:
            folium.GeoJson(
                json.loads(ma_boundary.iloc[0]['geometry_geojson']),
                style_function=lambda x: {
                    'color': '#FF6000',
                    'weight': 2,
                    'fillOpacity': 0,
                    'dashArray': '5, 5'
                },
                name='Massachusetts Boundary'
            ).add_to(m)

        # Add LCE trade area isochrones if available
        if 'tab1_isochrones' in st.session_state and not st.session_state.tab1_isochrones.empty:
            for _, iso in st.session_state.tab1_isochrones.iterrows():
                if pd.notna(iso.get('isochrone_geojson')) and iso.get('isochrone_geojson'):
                    try:
                        folium.GeoJson(
                            json.loads(iso['isochrone_geojson']),
                            style_function=lambda x: {
                                'color': '#FF8C00',
                                'weight': 1,
                                'fillOpacity': 0.05,
                                'fillColor': '#FF8C00'
                            }
                        ).add_to(m)
                    except:
                        pass

        # Add convenience trade area isochrones if available
        if 'tab1_convenience_isochrones' in st.session_state and not st.session_state.tab1_convenience_isochrones.empty:
            for _, iso in st.session_state.tab1_convenience_isochrones.iterrows():
                if pd.notna(iso.get('isochrone_geojson')) and iso.get('isochrone_geojson'):
                    try:
                        folium.GeoJson(
                            json.loads(iso['isochrone_geojson']),
                            style_function=lambda x: {
                                'color': '#3b82f6',
                                'weight': 1,
                                'fillOpacity': 0.03,
                                'fillColor': '#3b82f6'
                            }
                        ).add_to(m)
                    except:
                        pass

        # Add current Little Caesars locations with clustering (GREEN)
        if not current_stores.empty:
            lce_cluster_tab2 = MarkerCluster(
                name='LCE Stores',
                options={
                    'maxClusterRadius': 50,
                    'iconCreateFunction': '''
                        function(cluster) {
                            return L.divIcon({
                                html: '<div style="background-color: #10b981; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid #059669;"><span>' + cluster.getChildCount() + '</span></div>',
                                className: 'marker-cluster',
                                iconSize: L.point(40, 40)
                            });
                        }
                    '''
                }
            ).add_to(m)

            for _, store in current_stores.iterrows():
                tooltip_text = f"""
                <div style="font-family: Arial; font-size: 12px;">
                    <b>Current Store {store['store_number']}</b><br/>
                    {store['address']}<br/>
                    {store['city']}, {store['state']} {store['zip_code']}<br/>
                    <hr style="margin: 5px 0;">
                    <b>Population:</b> {store['population']:,.0f}
                </div>
                """
                folium.CircleMarker(
                    location=[store['latitude'], store['longitude']],
                    radius=6,
                    popup=tooltip_text,
                    tooltip=tooltip_text,
                    color='#10b981',
                    fill=True,
                    fillColor='#34d399',
                    fillOpacity=0.8,
                    weight=2
                ).add_to(lce_cluster_tab2)

        # Add convenience store markers with clustering if toggle is on (BLUE)
        if st.session_state.show_convenience_tab2 and not convenience_stores_tab2.empty:
            conv_cluster_tab2 = MarkerCluster(
                name='Convenience Stores',
                options={
                    'maxClusterRadius': 50,
                    'iconCreateFunction': '''
                        function(cluster) {
                            return L.divIcon({
                                html: '<div style="background-color: #3b82f6; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid #2563eb;"><span>' + cluster.getChildCount() + '</span></div>',
                                className: 'marker-cluster',
                                iconSize: L.point(40, 40)
                            });
                        }
                    '''
                }
            ).add_to(m)
            for _, conv in convenience_stores_tab2.iterrows():
                folium.CircleMarker(
                    location=[conv['latitude'], conv['longitude']],
                    radius=5,
                    popup=f"<b>{conv['name']}</b><br/>{conv.get('poi_subcategory', 'Convenience Store')}",
                    tooltip=f"Convenience: {conv['name']}",
                    color='#3b82f6',
                    fill=True,
                    fillColor='#60a5fa',
                    fillOpacity=0.7,
                    weight=2
                ).add_to(conv_cluster_tab2)

        # Add competitor markers if toggle is on (NO clustering)
        if st.session_state.show_competitors_tab2 and not competitors_tab2.empty:
            for _, comp in competitors_tab2.iterrows():
                folium.CircleMarker(
                    location=[comp['latitude'], comp['longitude']],
                    radius=5,
                    popup=f"<b>{comp['name']}</b><br/>{comp.get('poi_subcategory', 'Pizza')}",
                    tooltip=f"Competitor: {comp['name']}",
                    color='#dc2626',
                    fill=True,
                    fillColor='#ef4444',
                    fillOpacity=0.7,
                    weight=2
                ).add_to(m)

        # Add expansion candidates (gold/orange markers)
        for _, candidate in filtered.iterrows():
            tooltip_text = f"""
            <div style="font-family: Arial; font-size: 12px;">
                <b>Expansion Location {candidate['store_number']}</b><br/>
                {candidate['city']}, {candidate['state']}<br/>
                <hr style="margin: 5px 0;">
                <b>Predicted Sales:</b> ${candidate['predicted_annual_sales']:,.0f}
            </div>
            """
            folium.CircleMarker(
                location=[candidate['latitude'], candidate['longitude']],
                radius=8,
                popup=tooltip_text,
                tooltip=tooltip_text,
                color='#f59e0b',
                fill=True,
                fillColor='#fbbf24',
                fillOpacity=0.8,
                weight=2
            ).add_to(m)

        # Use unique key based on toggle states
        map_key_tab2 = f"tab2_map_{st.session_state.show_convenience_tab2}_{st.session_state.show_competitors_tab2}"
        st_folium(m, width=None, height=500, key=map_key_tab2)

        # Add toggle checkboxes below the map
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.session_state.show_convenience_tab2 = st.checkbox("Show Convenience Stores", value=st.session_state.show_convenience_tab2, key="conv_tab2")
        with col_t2:
            st.session_state.show_competitors_tab2 = st.checkbox("Show Competitors", value=st.session_state.show_competitors_tab2, key="comp_tab2")
        with col_t3:
            if st.button("🔄 Refresh Data", key="refresh_tab2"):
                st.session_state.tab2_data_loaded = False
                st.rerun()

        # Button below the map
        if st.button(f"Optimize Filtered Locations ({len(filtered)} locations)", type="primary", use_container_width=True):
            st.session_state['optimization_candidates'] = filtered.copy()
            st.success(f"✓ {len(filtered)} locations selected for optimization. Go to Network Optimizer tab to run optimization.")
    else:
        st.warning("No data available. Ensure tables exist and permissions are granted.")

with tab3:
    st.header("Network Optimization")

    # Get user token for OAuth
    user_token = get_user_token()
    if not user_token:
        st.error("Unable to authenticate. Please ensure you're logged in to Databricks.")
        st.stop()

    # Check if using pre-selected candidates from Tab 2
    using_preselected = 'optimization_candidates' in st.session_state and st.session_state['optimization_candidates'] is not None

    with st.spinner("Loading optimization data..."):
        existing = query(user_token, """
            SELECT e.latitude, e.longitude
            FROM jdub_demo_aws.geo_silver.existing_stores_h3 e
        """)

        if using_preselected:
            candidates = st.session_state['optimization_candidates']
            st.info(f"Using {len(candidates)} pre-selected locations from Expansion Candidates tab")
            if st.button("Clear Selection & Use All Candidates"):
                st.session_state['optimization_candidates'] = None
                st.rerun()
        else:
            candidates = query(user_token, """
                SELECT h3_cell_id as store_number, 'TBD' as city, 'MA' as state, latitude, longitude, 
                       predicted_annual_sales, population
                FROM jdub_demo_aws.geo_gold.expansion_candidates_h3_enhanced
            """)

    if not existing.empty and not candidates.empty:
        st.subheader("Optimization Parameters")
        col1, col2, col3 = st.columns(3)
        with col1:
            max_stores = st.number_input("Maximum New Stores", min_value=1, max_value=20, value=5)
        with col2:
            min_dist_new = st.number_input("Minimum Distance Between New Stores (miles)", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
        with col3:
            min_dist_existing = st.number_input("Minimum Distance from Existing Stores (miles)", min_value=1.0, max_value=10.0, value=2.0, step=0.5)

        if st.button("Run Optimization", type="primary", use_container_width=True):
            with st.spinner("Optimizing network..."):
                selected = []
                for _, candidate in candidates.sort_values('predicted_annual_sales', ascending=False).iterrows():
                    if len(selected) >= max_stores:
                        break

                    # Check distance constraints
                    too_close_existing = any(distance_miles(candidate.latitude, candidate.longitude, row.latitude, row.longitude) < min_dist_existing
                                           for _, row in existing.iterrows())
                    if too_close_existing:
                        continue

                    if selected:
                        too_close_selected = any(distance_miles(candidate.latitude, candidate.longitude, s['latitude'], s['longitude']) < min_dist_new
                                               for s in selected)
                        if too_close_selected:
                            continue

                    selected.append(candidate.to_dict())

                selected_df = pd.DataFrame(selected)

                # Store results in session state
                st.session_state['optimization_results'] = selected_df
                st.session_state['optimization_existing'] = existing
                st.session_state['optimization_candidates'] = candidates

        # Display results if they exist in session state
        if 'optimization_results' in st.session_state and st.session_state['optimization_results'] is not None:
            selected_df = st.session_state['optimization_results']
            existing = st.session_state['optimization_existing']
            candidates = st.session_state['optimization_candidates']

            st.success(f"Optimization complete: {len(selected_df)} locations selected")

            col1, col2, col3 = st.columns(3)
            col1.metric("Locations Selected", f"{len(selected_df)}")
            col2.metric("Total Predicted Revenue", f"${selected_df['predicted_annual_sales'].sum():,.0f}")
            col3.metric("Average Revenue per Location", f"${selected_df['predicted_annual_sales'].mean():,.0f}")

            st.subheader("Optimized Network Map")
            m = folium.Map(
                location=[candidates['latitude'].mean(), candidates['longitude'].mean()],
                zoom_start=9,
                tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                attr='CartoDB'
            )
            # Add existing stores
            for _, store in existing.iterrows():
                folium.CircleMarker(
                    location=[store['latitude'], store['longitude']],
                    radius=6,
                    tooltip="Existing Store",
                    color='#10b981',
                    fill=True,
                    fillColor='#34d399',
                    fillOpacity=0.6,
                    weight=2
                ).add_to(m)
            # Add recommended new locations
            for _, location in selected_df.iterrows():
                folium.CircleMarker(
                    location=[location['latitude'], location['longitude']],
                    radius=9,
                    popup=f"<b>New Location {location['store_number']}</b><br/>City: {location['city']}<br/>Predicted Sales: ${location['predicted_annual_sales']:,.0f}",
                    tooltip=f"Recommended: {location['city']}",
                    color='#f59e0b',
                    fill=True,
                    fillColor='#fbbf24',
                    fillOpacity=0.9,
                    weight=3
                ).add_to(m)
            st_folium(m, width=None, height=500)

            st.caption("Green: Existing Stores | Gold: Recommended New Locations")

            st.subheader("Recommended Locations")

            # Create a styled Plotly table
            display_df = selected_df[['store_number', 'predicted_annual_sales', 'population']].sort_values('predicted_annual_sales', ascending=False).reset_index(drop=True)

            # Format the values for display
            formatted_sales = ['${:,.0f}'.format(val) for val in display_df['predicted_annual_sales']]
            formatted_pop = ['{:,.0f}'.format(val) for val in display_df['population']]

            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=['<b>Store #</b>', '<b>Predicted Annual Sales</b>', '<b>Trade Area Population</b>'],
                    fill_color='#FF6000',
                    align='left',
                    font=dict(color='white', size=14, family='Inter')
                ),
                cells=dict(
                    values=[
                        display_df['store_number'],
                        formatted_sales,
                        formatted_pop
                    ],
                    fill_color=[['#1e293b', '#334155'] * len(display_df)],
                    align='left',
                    font=dict(color='#f1f5f9', size=13, family='Inter'),
                    height=35
                )
            )])

            fig.update_layout(
                height=min(400, len(display_df) * 40 + 60),
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )

            st.plotly_chart(fig, use_container_width=True)

            # Save to Delta Table button
            if st.button("Save Results to Delta Table", type="secondary", use_container_width=True):
                with st.spinner("Saving to Delta table..."):
                    try:
                        # Get the store numbers from selected results
                        store_numbers = selected_df['store_number'].tolist()
                        store_numbers_str = ','.join([f"'{sn}'" for sn in store_numbers])

                        # Create the expansion_locations_final table by joining with enriched data
                        save_query = f"""
                        CREATE OR REPLACE TABLE jdub_demo_aws.geo_gold.lce_expansion_final AS
                        SELECT e.*
                        FROM jdub_demo_aws.geo_gold.expansion_candidates_h3_enhanced e
                        WHERE e.h3_cell_id IN ({store_numbers_str})
                        """

                        query(user_token, save_query)
                        st.success(f"✓ Saved {len(store_numbers)} locations to jdub_demo_aws.geo_gold.lce_expansion_final")
                    except Exception as e:
                        st.error(f"Failed to save results: {e}")
    else:
        st.warning("No data available. Ensure tables exist and permissions are granted.")
