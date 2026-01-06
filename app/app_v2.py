import streamlit as st
import pandas as pd
from databricks import sql
import os
import json
from math import radians, sin, cos, sqrt, atan2
import streamlit.components.v1 as components

# ============================================
# STREAMLIT CONFIG - HIDE ALL UI
# ============================================
st.set_page_config(
    page_title="Hunger Satisfaction Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide all Streamlit UI elements
st.markdown("""
<style>
    /* Hide Streamlit branding and chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Remove all padding */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Make iframe fill screen */
    iframe {
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# BACKEND DATA FUNCTIONS
# ============================================

def get_user_token():
    """Get authentication token from environment variable"""
    return os.getenv("DATABRICKS_TOKEN")

@st.cache_data(ttl=600)
def query(_token, sql_query):
    """Execute SQL query using Databricks SQL Connector"""
    from databricks import sql as dbsql

    hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME", "e2-demo-west.cloud.databricks.com")
    http_path = os.getenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/75fd8278393d07eb")

    if not _token:
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
        return pd.DataFrame()

def load_current_network_data(user_token):
    """Load all data for Current Network mode from viz_* gold tables"""
    try:
        # Use viz_existing_stores (gold layer) instead of silver
        stores = query(user_token, """
            SELECT store_number, city, state, latitude, longitude,
                   population, poi_count as total_poi_count,
                   h3_cell_id, geometry_geojson
            FROM jdub_demo_aws.geo_gold.viz_existing_stores
        """)

        # Add placeholder for revenue if not present
        if not stores.empty and 'annual_revenue' not in stores.columns:
            stores['annual_revenue'] = 0
    except Exception as e:
        stores = pd.DataFrame()

    try:
        isochrones = query(user_token, """
            SELECT location_id as store_number, ST_AsGeoJSON(geometry) as isochrone_geojson
            FROM jdub_demo_aws.geo_silver.isochrones_lce
        """)
    except:
        isochrones = pd.DataFrame()

    try:
        # Use viz_convenience (gold layer) with candidate proximity info
        convenience_isochrones = query(user_token, """
            SELECT id as location_id, geometry_geojson as isochrone_geojson,
                   candidate_count_in_isochrone, total_candidate_sales_in_isochrone
            FROM jdub_demo_aws.geo_gold.viz_convenience
        """)
    except Exception as e:
        convenience_isochrones = pd.DataFrame()

    try:
        # Use viz_convenience for store info
        convenience_stores = query(user_token, """
            SELECT name, latitude, longitude, store_type as poi_category
            FROM jdub_demo_aws.geo_gold.viz_convenience
        """)
    except Exception as e:
        convenience_stores = pd.DataFrame()

    try:
        # Use viz_competitors (gold layer)
        competitors = query(user_token, """
            SELECT name, latitude, longitude, poi_category, poi_subcategory
            FROM jdub_demo_aws.geo_gold.viz_competitors
        """)
    except:
        competitors = pd.DataFrame()

    # MA boundary no longer needed - data is pre-filtered via H3 grid membership
    # But keep for optional map outline display
    ma_boundary = query(user_token, """
        SELECT ST_AsGeoJSON(geometry) as geometry_geojson
        FROM jdub_demo_aws.geo_bronze.census_states
        WHERE state_abbr = 'MA'
    """)

    return {
        'stores': stores.to_dict('records') if not stores.empty else [],
        'isochrones': isochrones.to_dict('records') if not isochrones.empty else [],
        'convenience_isochrones': convenience_isochrones.to_dict('records') if not convenience_isochrones.empty else [],
        'convenience_stores': convenience_stores.to_dict('records') if not convenience_stores.empty else [],
        'competitors': competitors.to_dict('records') if not competitors.empty else [],
        'ma_boundary': json.loads(ma_boundary.iloc[0]['geometry_geojson']) if not ma_boundary.empty and ma_boundary.iloc[0].get('geometry_geojson') else None
    }

def load_expansion_data(user_token):
    """Load all data for Expansion Analysis mode from viz_* gold tables

    Enhanced viz_expansion_candidates includes pre-computed:
    - min_distance_to_existing: Distance to nearest existing store (replaces runtime Haversine)
    - nearest_existing_store: Store number of nearest existing store
    - within_convenience_isochrone: Boolean flag (replaces runtime point-in-polygon)
    - convenience_store_name, convenience_city: Partner info if within isochrone
    - fulfillment_strategy: 'partner' or 'new_store' (pre-computed recommendation)
    - quality_tier: 'top_25', 'top_50', 'top_75', 'bottom_25'
    """
    candidates = query(user_token, """
        SELECT h3_cell_id as store_number,
               COALESCE(
                   CASE
                       WHEN convenience_city IS NOT NULL THEN convenience_city
                       WHEN urbanicity = 'urban' THEN 'Boston Metro'
                       WHEN urbanicity = 'suburban' THEN 'Greater Boston'
                       ELSE 'Massachusetts'
                   END,
                   'Massachusetts'
               ) as city,
               'MA' as state,
               latitude, longitude,
               predicted_annual_sales, population, total_poi as total_poi_count,
               min_distance_to_existing, nearest_existing_store,
               within_convenience_isochrone, convenience_store_name,
               convenience_city, convenience_drive_time,
               fulfillment_strategy, quality_tier,
               center_lat, center_lon, geometry_geojson
        FROM jdub_demo_aws.geo_gold.viz_expansion_candidates
    """)

    # Use viz_existing_stores (gold layer)
    current_stores = query(user_token, """
        SELECT store_number, city, state, latitude, longitude,
               population, poi_count as total_poi_count,
               h3_cell_id, geometry_geojson
        FROM jdub_demo_aws.geo_gold.viz_existing_stores
    """)

    try:
        # Use viz_convenience for store info
        convenience_stores = query(user_token, """
            SELECT name, latitude, longitude, store_type as poi_category
            FROM jdub_demo_aws.geo_gold.viz_convenience
        """)
    except Exception as e:
        convenience_stores = pd.DataFrame()

    try:
        # Use viz_competitors (gold layer)
        competitors = query(user_token, """
            SELECT name, latitude, longitude, poi_category, poi_subcategory
            FROM jdub_demo_aws.geo_gold.viz_competitors
        """)
    except:
        competitors = pd.DataFrame()

    return {
        'candidates': candidates.to_dict('records') if not candidates.empty else [],
        'current_stores': current_stores.to_dict('records') if not current_stores.empty else [],
        'convenience_stores': convenience_stores.to_dict('records') if not convenience_stores.empty else [],
        'competitors': competitors.to_dict('records') if not competitors.empty else []
    }

def load_optimization_results(user_token):
    """Load pre-computed optimization results from viz_optimization_results

    Returns all parameter combinations with their selected H3 cells.
    The app can then do O(1) lookup instead of O(n²) runtime optimization.
    """
    try:
        results = query(user_token, """
            SELECT max_stores, min_distance_new, min_distance_existing,
                   selected_h3_cells, selected_count, total_predicted_sales
            FROM jdub_demo_aws.geo_gold.viz_optimization_results
        """)
        return results.to_dict('records') if not results.empty else []
    except Exception as e:
        return []

def load_network_metrics(user_token):
    """Load pre-computed network metrics from viz_network_metrics (singleton row)"""
    try:
        metrics = query(user_token, """
            SELECT * FROM jdub_demo_aws.geo_gold.viz_network_metrics
        """)
        return metrics.to_dict('records')[0] if not metrics.empty else {}
    except Exception as e:
        return {}

def distance_miles(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two coordinates"""
    R = 3959
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def run_optimization(candidates_data, existing_data, params):
    """Run optimization algorithm"""
    candidates_df = pd.DataFrame(candidates_data)
    existing_df = pd.DataFrame(existing_data)

    selected = []
    max_stores = params['max_stores']
    min_dist_new = params['min_dist_new']
    min_dist_existing = params['min_dist_existing']

    for _, candidate in candidates_df.sort_values('predicted_annual_sales', ascending=False).iterrows():
        if len(selected) >= max_stores:
            break

        too_close_existing = any(
            distance_miles(candidate.latitude, candidate.longitude, row.latitude, row.longitude) < min_dist_existing
            for _, row in existing_df.iterrows()
        )
        if too_close_existing:
            continue

        if selected:
            too_close_selected = any(
                distance_miles(candidate.latitude, candidate.longitude, s['latitude'], s['longitude']) < min_dist_new
                for s in selected
            )
            if too_close_selected:
                continue

        selected.append(candidate.to_dict())

    return selected

# ============================================
# LOAD LOGO AS BASE64
# ============================================
import base64

def get_logo_base64():
    """Convert logo to base64 for embedding in HTML"""
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "Little-Caesars-man-logo.png")
        with open(logo_path, "rb") as f:
            logo_data = f.read()
        return base64.b64encode(logo_data).decode()
    except:
        return None

# ============================================
# LOAD DATA ON STARTUP
# ============================================
user_token = get_user_token()

if 'data_loaded' not in st.session_state:
    if user_token:
        st.session_state.current_network_data = load_current_network_data(user_token)
        st.session_state.expansion_data = load_expansion_data(user_token)
        # Load pre-computed optimization results for O(1) lookup
        st.session_state.optimization_results_cache = load_optimization_results(user_token)
        # Load pre-computed network metrics (singleton aggregates)
        st.session_state.network_metrics = load_network_metrics(user_token)
        st.session_state.data_loaded = True
    else:
        st.session_state.current_network_data = {}
        st.session_state.expansion_data = {}
        st.session_state.optimization_results_cache = []
        st.session_state.network_metrics = {}
        st.session_state.data_loaded = False

# Load logo
logo_base64 = get_logo_base64()

# ============================================
# CUSTOM JAVASCRIPT FRONTEND
# ============================================

# Prepare data for JavaScript
current_network_json = json.dumps(st.session_state.current_network_data) if st.session_state.data_loaded else "{}"
expansion_json = json.dumps(st.session_state.expansion_data) if st.session_state.data_loaded else "{}"
# Pre-computed optimization results for O(1) lookup (replaces O(n²) runtime optimization)
optimization_cache_json = json.dumps(st.session_state.optimization_results_cache) if st.session_state.data_loaded else "[]"
# Pre-computed network metrics
network_metrics_json = json.dumps(st.session_state.network_metrics) if st.session_state.data_loaded else "{}"
logo_data_uri = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hunger Satisfaction Dashboard</title>

    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #F0F4F8;
            overflow: hidden;
        }}

        #app-container {{
            display: flex;
            height: 100vh;
            width: 100vw;
        }}

        /* Header */
        #app-header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 64px;
            background: #F06B38;
            display: flex;
            align-items: center;
            padding: 0 24px;
            box-shadow: 0 2px 8px rgba(240, 107, 56, 0.2);
            z-index: 1000;
        }}

        #app-header .logo {{
            height: 48px;
            margin-right: 16px;
        }}

        #app-header h1 {{
            color: white;
            font-size: 20px;
            font-weight: 600;
            margin: 0;
        }}

        #app-header .subtitle {{
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            margin-left: 16px;
        }}

        /* Sidebar */
        #sidebar {{
            width: 320px;
            background: white;
            border-right: 1px solid #E0E7EF;
            overflow-y: auto;
            margin-top: 64px;
            height: calc(100vh - 64px);
            padding: 16px;
        }}

        .section-header {{
            font-size: 12px;
            font-weight: 600;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 32px 0 12px 0;
            padding-top: 16px;
            border-top: 1px solid #E0E7EF;
        }}

        .section-header:first-child {{
            margin-top: 0;
            padding-top: 0;
            border-top: none;
        }}

        /* Extra spacing above metrics section */
        #metrics-container {{
            margin-top: 24px;
        }}

        #metrics-container .section-header {{
            margin-top: 48px;
            padding-top: 24px;
        }}

        /* Tabs for view modes */
        .mode-tabs {{
            display: flex;
            background: #F9FAFB;
            border-radius: 8px;
            padding: 4px;
            margin-bottom: 16px;
        }}

        .mode-tab {{
            flex: 1;
            padding: 8px 12px;
            background: transparent;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 13px;
            color: #6B7280;
            font-weight: 500;
            text-align: center;
        }}

        .mode-tab:hover {{
            color: #374151;
            background: #E0E7EF;
        }}

        .mode-tab.active {{
            background: #F06B38;
            color: white;
        }}

        /* Checkbox controls */
        .control-group {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .checkbox-control {{
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }}

        .checkbox-control input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            cursor: pointer;
        }}

        .checkbox-control label {{
            font-size: 14px;
            color: #374151;
            cursor: pointer;
        }}

        /* Slider controls */
        .slider-control {{
            margin-bottom: 16px;
        }}

        .slider-control label {{
            display: block;
            font-size: 14px;
            color: #374151;
            margin-bottom: 8px;
            font-weight: 500;
        }}

        .slider-control input[type="range"] {{
            width: 100%;
            height: 6px;
            background: #E0E7EF;
            border-radius: 3px;
            outline: none;
        }}

        .slider-control input[type="range"]::-webkit-slider-thumb {{
            appearance: none;
            width: 18px;
            height: 18px;
            background: #F06B38;
            border-radius: 50%;
            cursor: pointer;
        }}

        .slider-value {{
            font-size: 12px;
            color: #6B7280;
            margin-top: 4px;
        }}

        /* Number input */
        .number-control {{
            margin-bottom: 16px;
        }}

        .number-control label {{
            display: block;
            font-size: 14px;
            color: #374151;
            margin-bottom: 8px;
            font-weight: 500;
        }}

        .number-control input[type="number"],
        .number-control select {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #E0E7EF;
            border-radius: 6px;
            font-size: 14px;
            background-color: white;
            cursor: pointer;
        }}

        .number-control select {{
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 8px center;
            background-size: 16px;
            padding-right: 32px;
        }}

        /* Buttons */
        .btn {{
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .btn-primary {{
            background: #F06B38;
            color: white;
        }}

        .btn-primary:hover {{
            background: #d85f30;
        }}

        .btn-secondary {{
            background: white;
            color: #F06B38;
            border: 1px solid #F06B38;
        }}

        .btn-secondary:hover {{
            background: #F06B38;
            color: white;
        }}

        /* Metrics */
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
            margin: 16px 0;
        }}

        .metric-card {{
            background: white;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #E0E7EF;
        }}

        .metric-label {{
            font-size: 11px;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metric-value {{
            font-size: 20px;
            color: #F06B38;
            font-weight: 600;
            margin-top: 4px;
        }}

        /* Map container */
        #map-container {{
            flex: 1;
            margin-top: 64px;
            height: calc(100vh - 64px);
            position: relative;
        }}

        #map {{
            width: 100%;
            height: 100%;
        }}

        /* Map legend */
        .map-legend {{
            position: absolute;
            top: 24px;
            right: 24px;
            background: white;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #E0E7EF;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            z-index: 500;
        }}

        .map-legend h4 {{
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 12px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            font-size: 13px;
            color: #374151;
        }}

        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid;
        }}

        /* Detail panel */
        #detail-panel {{
            position: fixed;
            right: 0;
            top: 64px;
            width: 384px;
            height: calc(100vh - 64px);
            background: white;
            border-left: 1px solid #E0E7EF;
            box-shadow: -4px 0 16px rgba(0, 0, 0, 0.15);
            transform: translateX(384px);
            transition: transform 300ms ease-out;
            z-index: 1001;
            overflow-y: auto;
        }}

        #detail-panel.open {{
            transform: translateX(0);
        }}

        .panel-header {{
            padding: 16px;
            border-bottom: 1px solid #E0E7EF;
            position: sticky;
            top: 0;
            background: white;
            z-index: 10;
        }}

        .panel-label {{
            font-size: 12px;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .panel-title {{
            font-size: 20px;
            color: #F06B38;
            font-weight: 600;
            margin-top: 4px;
        }}

        .close-btn {{
            position: absolute;
            top: 16px;
            right: 16px;
            background: none;
            border: none;
            font-size: 24px;
            color: #6B7280;
            cursor: pointer;
            width: 24px;
            height: 24px;
            line-height: 24px;
            text-align: center;
        }}

        .close-btn:hover {{
            color: #374151;
        }}

        .panel-section {{
            padding: 16px;
            border-bottom: 1px solid #E0E7EF;
        }}

        .stat-card {{
            background: #F9FAFB;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
        }}

        .stat-label {{
            color: #6B7280;
            font-size: 12px;
            margin-bottom: 4px;
        }}

        .stat-value {{
            color: #374151;
            font-size: 16px;
            font-weight: 600;
        }}

        .metric-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .metric-row-label {{
            color: #6B7280;
            font-size: 14px;
        }}

        .metric-row-value {{
            color: #374151;
            font-size: 14px;
            font-weight: 600;
        }}

        /* Loading spinner */
        .spinner {{
            border: 3px solid #E0E7EF;
            border-top: 3px solid #F06B38;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        .divider {{
            height: 1px;
            background: #E0E7EF;
            margin: 16px 0;
        }}

        /* Step Indicators */
        .step-indicator {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%);
            border-left: 4px solid #F06B38;
            border-radius: 8px;
            margin: 20px 0 16px 0;
        }}

        .step-number {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            background: #F06B38;
            color: white;
            font-weight: 700;
            font-size: 16px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .step-label {{
            font-size: 15px;
            font-weight: 600;
            color: #374151;
            letter-spacing: 0.3px;
        }}

        /* Recommendation Section */
        .recommendation-card {{
            background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
            border: 2px solid #F59E0B;
            border-radius: 12px;
            padding: 16px;
            margin: 16px 0;
        }}

        .recommendation-card.partner {{
            background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
            border: 2px solid #3B82F6;
        }}

        .recommendation-header {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #92400E;
            margin-bottom: 8px;
        }}

        .recommendation-card.partner .recommendation-header {{
            color: #1E3A8A;
        }}

        .recommendation-title {{
            font-size: 18px;
            font-weight: 700;
            color: #92400E;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .recommendation-card.partner .recommendation-title {{
            color: #1E3A8A;
        }}

        .recommendation-rationale {{
            font-size: 13px;
            color: #78350F;
            line-height: 1.5;
            margin-bottom: 8px;
        }}

        .recommendation-card.partner .recommendation-rationale {{
            color: #1E40AF;
        }}

        .recommendation-details {{
            background: rgba(255, 255, 255, 0.6);
            border-radius: 8px;
            padding: 12px;
            margin-top: 12px;
        }}

        .recommendation-detail-row {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 6px;
        }}

        .recommendation-detail-row:last-child {{
            margin-bottom: 0;
        }}

        .recommendation-detail-label {{
            color: #6B7280;
            font-weight: 500;
        }}

        .recommendation-detail-value {{
            color: #374151;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <div id="app-header">
        {"<img src='" + logo_data_uri + "' alt='Little Caesars Logo' class='logo'>" if logo_data_uri else ""}
        <h1>Hunger Satisfaction Dashboard</h1>
        <span class="subtitle">Powered by Databricks</span>
    </div>

    <!-- Main Container -->
    <div id="app-container">
        <!-- Sidebar -->
        <div id="sidebar">
            <div class="mode-tabs">
                <button class="mode-tab active" data-mode="current">Existing</button>
                <button class="mode-tab" data-mode="expansion">Expansion</button>
                <button class="mode-tab" data-mode="chat">Chat</button>
            </div>

            <div id="controls-container">
                <!-- Controls will be dynamically inserted here -->
            </div>

            <div id="metrics-container">
                <!-- Metrics will be dynamically inserted here -->
            </div>
        </div>

        <!-- Map Container -->
        <div id="map-container">
            <div id="map"></div>

            <!-- Map Legend -->
            <div class="map-legend">
                <h4>Map Legend</h4>
                <div class="legend-item">
                    <span class="legend-dot" style="background: #fbbf24; border-color: #f59e0b;"></span>
                    <span>Expansion Candidates</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot" style="background: rgba(251, 191, 36, 0.2); border: 1.5px solid #f59e0b;"></span>
                    <span>H3 Hexagons</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot" style="background: #34d399; border-color: #10b981;"></span>
                    <span>Current Stores</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot" style="background: #60a5fa; border-color: #3b82f6;"></span>
                    <span>Convenience</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot" style="background: #ef4444; border-color: #dc2626;"></span>
                    <span>Competitors</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Detail Panel -->
    <div id="detail-panel">
        <div class="panel-header">
            <div class="panel-label">Store Details</div>
            <div class="panel-title" id="panel-title">Store #</div>
            <button class="close-btn" onclick="closeDetailPanel()">×</button>
        </div>
        <div id="detail-content">
            <!-- Detail content will be dynamically inserted -->
        </div>
    </div>

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <script>
        // Data from backend
        const currentNetworkData = {current_network_json};
        const expansionData = {expansion_json};
        // Pre-computed optimization results for O(1) lookup (replaces O(n²) runtime optimization)
        const optimizationResultsCache = {optimization_cache_json};
        // Pre-computed network metrics
        const networkMetrics = {network_metrics_json};

        // Application state
        let currentMode = 'current';
        let map = null;
        let layers = {{'stores': true, 'trade_areas': true, 'convenience': true, 'competitors': false}};
        let filters = {{min_sales: null, max_sales: null, min_population: null, max_population: null}};
        let optimizationParams = {{max_stores: 5, min_dist_new: 3.0, min_dist_existing: 2.0}};
        let optimizationResults = null;
        // Available parameter grid values (must match what's pre-computed in pipeline)
        const paramGrid = {{
            max_stores: [5, 10, 15, 20, 25, 30],
            min_dist_new: [1.0, 2.0, 3.0, 5.0],
            min_dist_existing: [1.0, 2.0, 3.0, 5.0]
        }};

        // Initialize map
        function initMap() {{
            map = L.map('map').setView([42.4072, -71.3824], 9);

            // Add dark tile layer (matching notebook styling)
            L.tileLayer('https://cartodb-basemaps-{{s}}.global.ssl.fastly.net/dark_all/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                maxZoom: 20
            }}).addTo(map);

            // Create custom panes for better z-index control
            map.createPane('isochrones');
            map.getPane('isochrones').style.zIndex = 400;

            map.createPane('markers');
            map.getPane('markers').style.zIndex = 450;

            // Render initial data
            renderMap();
        }}

        // Render map based on current mode and state
        function renderMap() {{
            // Clear existing layers
            map.eachLayer(layer => {{
                if (layer instanceof L.Marker || layer instanceof L.CircleMarker || layer instanceof L.GeoJSON) {{
                    map.removeLayer(layer);
                }}
            }});

            if (currentMode === 'current') {{
                renderCurrentNetworkMap();
            }} else if (currentMode === 'expansion') {{
                renderExpansionMap();
            }}
        }}

        // Render Current Network mode map
        function renderCurrentNetworkMap() {{
            const data = currentNetworkData;

            // Add LCE trade area isochrones if enabled
            if (layers.trade_areas && data.isochrones) {{
                data.isochrones.forEach(iso => {{
                    if (iso.isochrone_geojson) {{
                        try {{
                            const geojson = JSON.parse(iso.isochrone_geojson);
                            L.geoJSON(geojson, {{
                                pane: 'isochrones',
                                style: {{
                                    color: '#10b981',
                                    weight: 1.5,
                                    fillOpacity: 0.15,
                                    fillColor: '#10b981'
                                }}
                            }}).addTo(map);
                        }} catch (e) {{
                            console.error('Failed to parse LCE isochrone:', e);
                        }}
                    }}
                }});
            }}

            // Add convenience store trade area isochrones if enabled
            if (layers.convenience && data.convenience_isochrones) {{
                data.convenience_isochrones.forEach(iso => {{
                    if (iso.isochrone_geojson) {{
                        try {{
                            const geojson = JSON.parse(iso.isochrone_geojson);
                            L.geoJSON(geojson, {{
                                pane: 'isochrones',
                                style: {{
                                    color: '#3b82f6',
                                    weight: 1.5,
                                    fillOpacity: 0.15,
                                    fillColor: '#3b82f6'
                                }}
                            }}).addTo(map);
                        }} catch (e) {{
                            console.error('Failed to parse convenience isochrone:', e);
                        }}
                    }}
                }});
            }}

            // Add stores
            if (layers.stores && data.stores) {{
                data.stores.forEach(store => {{
                    const marker = L.circleMarker([store.latitude, store.longitude], {{
                        pane: 'markers',
                        radius: 8,
                        fillColor: '#10b981',
                        color: '#065f46',
                        weight: 2,
                        fillOpacity: 0.9
                    }});

                    marker.bindPopup(`
                        <b>Store ${{store.store_number}}</b><br/>
                        ${{store.city}}, ${{store.state}}<br/>
                        <hr style="margin: 5px 0;">
                        <b>Population:</b> ${{Math.round(store.population).toLocaleString()}}<br/>
                        <b>POI Count:</b> ${{store.total_poi_count.toLocaleString()}}
                    `);

                    marker.on('click', () => showDetailPanel(store));
                    marker.addTo(map);
                }});
            }}

            // Add convenience stores
            if (layers.convenience && data.convenience_stores) {{
                data.convenience_stores.forEach(store => {{
                    L.circleMarker([store.latitude, store.longitude], {{
                        pane: 'markers',
                        radius: 5,
                        fillColor: '#3b82f6',
                        color: '#1e3a8a',
                        weight: 2,
                        fillOpacity: 0.9
                    }}).bindPopup(`<b>${{store.name}}</b>`).addTo(map);
                }});
            }}

            // Add competitors
            if (layers.competitors && data.competitors) {{
                data.competitors.forEach(comp => {{
                    L.circleMarker([comp.latitude, comp.longitude], {{
                        pane: 'markers',
                        radius: 5,
                        fillColor: '#ef4444',
                        color: '#dc2626',
                        weight: 2,
                        fillOpacity: 0.7
                    }}).bindPopup(`<b>${{comp.name}}</b>`).addTo(map);
                }});
            }}

            // Update metrics
            updateMetrics();
        }}

        // Render Expansion mode map
        function renderExpansionMap() {{
            const data = expansionData;

            // Add LCE trade area isochrones (always visible)
            if (currentNetworkData.isochrones) {{
                currentNetworkData.isochrones.forEach(iso => {{
                    if (iso.isochrone_geojson) {{
                        try {{
                            const geojson = JSON.parse(iso.isochrone_geojson);
                            L.geoJSON(geojson, {{
                                pane: 'isochrones',
                                style: {{
                                    color: '#10b981',
                                    weight: 1.5,
                                    fillOpacity: 0.15,
                                    fillColor: '#10b981'
                                }}
                            }}).addTo(map);
                        }} catch (e) {{
                            console.error('Failed to parse LCE isochrone:', e);
                        }}
                    }}
                }});
            }}

            // Add convenience store trade area isochrones if enabled
            if (layers.convenience && currentNetworkData.convenience_isochrones) {{
                currentNetworkData.convenience_isochrones.forEach(iso => {{
                    if (iso.isochrone_geojson) {{
                        try {{
                            const geojson = JSON.parse(iso.isochrone_geojson);
                            L.geoJSON(geojson, {{
                                pane: 'isochrones',
                                style: {{
                                    color: '#3b82f6',
                                    weight: 1.5,
                                    fillOpacity: 0.15,
                                    fillColor: '#3b82f6'
                                }}
                            }}).addTo(map);
                        }} catch (e) {{
                            console.error('Failed to parse convenience isochrone:', e);
                        }}
                    }}
                }});
            }}

            // Add current stores
            if (layers.current_stores && data.current_stores) {{
                data.current_stores.forEach(store => {{
                    const marker = L.circleMarker([store.latitude, store.longitude], {{
                        pane: 'markers',
                        radius: 6,
                        fillColor: '#10b981',
                        color: '#065f46',
                        weight: 2,
                        fillOpacity: 0.9
                    }});

                    marker.bindPopup(`<b>Current Store ${{store.store_number}}</b>`);
                    marker.on('click', () => showDetailPanel(store));
                    marker.addTo(map);
                }});
            }}

            // Add candidates (filtered) - only if no optimization results or if candidates layer is enabled
            if (layers.candidates && data.candidates && !optimizationResults) {{
                let filtered = data.candidates;

                // Apply filters
                if (filters.min_sales) {{
                    filtered = filtered.filter(c => c.predicted_annual_sales >= filters.min_sales);
                }}
                if (filters.min_population) {{
                    filtered = filtered.filter(c => c.population >= filters.min_population);
                }}

                // Render H3 hexagons if enabled
                if (layers.h3_hexagons) {{
                    filtered.forEach(candidate => {{
                        if (candidate.geometry_geojson) {{
                            try {{
                                const geojson = JSON.parse(candidate.geometry_geojson);
                                const hexagon = L.geoJSON(geojson, {{
                                    pane: 'isochrones',
                                    style: {{
                                        color: '#f59e0b',
                                        weight: 1.5,
                                        fillColor: '#fbbf24',
                                        fillOpacity: 0.2
                                    }}
                                }});

                                hexagon.bindPopup(`
                                    <b>H3 Cell: ${{candidate.store_number}}</b><br/>
                                    <b>Predicted Sales:</b> $${{candidate.predicted_annual_sales.toLocaleString()}}<br/>
                                    <b>Population:</b> ${{Math.round(candidate.population).toLocaleString()}}
                                `);

                                hexagon.on('click', () => showDetailPanel(candidate));
                                hexagon.addTo(map);
                            }} catch (e) {{
                                console.error('Error rendering H3 hexagon:', e);
                            }}
                        }}
                    }});
                }}

                // Render centroid markers
                filtered.forEach(candidate => {{
                    const marker = L.circleMarker([candidate.latitude, candidate.longitude], {{
                        pane: 'markers',
                        radius: 8,
                        fillColor: '#fbbf24',
                        color: '#f59e0b',
                        weight: 2,
                        fillOpacity: 0.8
                    }});

                    marker.bindPopup(`
                        <b>Expansion Location ${{candidate.store_number}}</b><br/>
                        <b>Predicted Sales:</b> $${{candidate.predicted_annual_sales.toLocaleString()}}<br/>
                        <b>Population:</b> ${{Math.round(candidate.population).toLocaleString()}}
                    `);

                    marker.on('click', () => showDetailPanel(candidate));
                    marker.addTo(map);
                }});
            }}

            // Add optimized locations if available
            if (optimizationResults) {{
                // Render H3 hexagons if enabled
                if (layers.h3_hexagons) {{
                    optimizationResults.forEach(location => {{
                        if (location.geometry_geojson) {{
                            try {{
                                const geojson = JSON.parse(location.geometry_geojson);
                                const hexagon = L.geoJSON(geojson, {{
                                    pane: 'isochrones',
                                    style: {{
                                        color: '#f59e0b',
                                        weight: 2,
                                        fillColor: '#fbbf24',
                                        fillOpacity: 0.3
                                    }}
                                }});

                                hexagon.bindPopup(`
                                    <b>Optimized H3 Cell</b><br/>
                                    <b>Predicted Sales:</b> $${{location.predicted_annual_sales.toLocaleString()}}<br/>
                                    <b>Population:</b> ${{Math.round(location.population).toLocaleString()}}
                                `);

                                hexagon.on('click', () => showDetailPanel(location));
                                hexagon.addTo(map);
                            }} catch (e) {{
                                console.error('Error rendering optimized H3 hexagon:', e);
                            }}
                        }}
                    }});
                }}

                // Render centroid markers
                optimizationResults.forEach(location => {{
                    const marker = L.circleMarker([location.latitude, location.longitude], {{
                        pane: 'markers',
                        radius: 9,
                        fillColor: '#fbbf24',
                        color: '#f59e0b',
                        weight: 3,
                        fillOpacity: 0.9
                    }});

                    marker.bindPopup(`
                        <b>Optimized Location</b><br/>
                        <b>Predicted Sales:</b> $${{location.predicted_annual_sales.toLocaleString()}}<br/>
                        <b>Population:</b> ${{Math.round(location.population).toLocaleString()}}
                    `);

                    marker.on('click', () => showDetailPanel(location));
                    marker.addTo(map);
                }});
            }}

            // Add convenience/competitors if enabled
            // Use convenience stores from expansion data, or fall back to current network data
            const convenienceStoresSource = (data.convenience_stores && data.convenience_stores.length > 0)
                ? data.convenience_stores
                : currentNetworkData.convenience_stores;

            if (layers.convenience && convenienceStoresSource) {{
                convenienceStoresSource.forEach(store => {{
                    L.circleMarker([store.latitude, store.longitude], {{
                        pane: 'markers',
                        radius: 5,
                        fillColor: '#3b82f6',
                        color: '#1e3a8a',
                        weight: 2,
                        fillOpacity: 0.9
                    }}).bindPopup(`<b>${{store.name}}</b>`).addTo(map);
                }});
            }}

            if (layers.competitors && data.competitors) {{
                data.competitors.forEach(comp => {{
                    L.circleMarker([comp.latitude, comp.longitude], {{
                        pane: 'markers',
                        radius: 5,
                        fillColor: '#ef4444',
                        color: '#dc2626',
                        weight: 2,
                        fillOpacity: 0.7
                    }}).bindPopup(`<b>${{comp.name}}</b>`).addTo(map);
                }});
            }}

            updateMetrics();
        }}


        // NOTE: pointInPolygon() and checkConvenienceStoreProximity() have been REMOVED
        // These functions are no longer needed because:
        // - fulfillment_strategy is now pre-computed in viz_expansion_candidates
        // - within_convenience_isochrone is now a pre-computed boolean column
        // - convenience_store_name, convenience_city, convenience_drive_time are pre-computed
        // This removes ~90 lines of JavaScript and replaces O(n*vertices) computation with O(1) lookup

        // Show detail panel
        function showDetailPanel(storeData) {{
            document.getElementById('panel-title').textContent = `Store #${{storeData.store_number || 'N/A'}}`;

            let detailHTML = `
                <div class="panel-section">
                    <div class="stat-card">
                        <div class="stat-label">Location</div>
                        <div class="stat-value">${{storeData.city || 'N/A'}}, ${{storeData.state || 'N/A'}}</div>
                    </div>
                </div>
                <div class="panel-section">
            `;

            // Revenue (if available)
            if (storeData.annual_revenue !== undefined || storeData.revenue !== undefined) {{
                const revenue = storeData.annual_revenue || storeData.revenue;
                detailHTML += `
                    <div class="metric-row">
                        <div class="metric-row-label">Annual Revenue</div>
                        <div class="metric-row-value">$${{revenue.toLocaleString()}}</div>
                    </div>
                `;
            }}

            // POI Count (always show for current stores)
            if (storeData.total_poi_count !== undefined) {{
                detailHTML += `
                    <div class="metric-row">
                        <div class="metric-row-label">POI Count</div>
                        <div class="metric-row-value">${{storeData.total_poi_count.toLocaleString()}}</div>
                    </div>
                `;
            }}

            // Population
            detailHTML += `
                <div class="metric-row">
                    <div class="metric-row-label">Population</div>
                    <div class="metric-row-value">${{Math.round(storeData.population || 0).toLocaleString()}}</div>
                </div>
            `;

            // Predicted Sales (for expansion candidates)
            if (storeData.predicted_annual_sales !== undefined) {{
                detailHTML += `
                    <div class="metric-row">
                        <div class="metric-row-label">Predicted Sales</div>
                        <div class="metric-row-value">$${{storeData.predicted_annual_sales.toLocaleString()}}</div>
                    </div>
                `;
            }}

            detailHTML += '</div>';

            // Fulfillment Recommendation (uses pre-computed fulfillment_strategy from pipeline)
            // This replaces ~75 lines of JavaScript point-in-polygon code with O(1) property read
            if (storeData.predicted_annual_sales !== undefined && currentMode === 'expansion') {{
                // Use pre-computed fulfillment_strategy column (replaces runtime checkConvenienceStoreProximity)
                const strategy = storeData.fulfillment_strategy || 'new_store';
                const isPartner = strategy === 'partner' || storeData.within_convenience_isochrone;

                if (isPartner) {{
                    // Partner with convenience store (pre-computed data available)
                    detailHTML += `
                        <div class="panel-section">
                            <div class="recommendation-card partner">
                                <div class="recommendation-header">Fulfillment Recommendation</div>
                                <div class="recommendation-title">
                                    🤝 Partner with Convenience Store
                                </div>
                                <div class="recommendation-rationale">
                                    This location falls within a 5-minute drive time of an existing convenience store, making it an ideal partnership opportunity.
                                </div>
                                <div class="recommendation-details">
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Partner Store</span>
                                        <span class="recommendation-detail-value">${{storeData.convenience_store_name || '7-Eleven'}}</span>
                                    </div>
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Location</span>
                                        <span class="recommendation-detail-value">${{storeData.convenience_city || 'N/A'}}</span>
                                    </div>
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Drive Time</span>
                                        <span class="recommendation-detail-value">${{storeData.convenience_drive_time || 5}} minutes</span>
                                    </div>
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Strategy</span>
                                        <span class="recommendation-detail-value">Micro-fulfillment</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }} else {{
                    // Open new store (pre-computed nearest store info available)
                    detailHTML += `
                        <div class="panel-section">
                            <div class="recommendation-card">
                                <div class="recommendation-header">Fulfillment Recommendation</div>
                                <div class="recommendation-title">
                                    🏪 Open New Store
                                </div>
                                <div class="recommendation-rationale">
                                    This location is not within a 5-minute drive time of any existing convenience stores. Building a new store would provide optimal market coverage and customer access.
                                </div>
                                <div class="recommendation-details">
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Strategy</span>
                                        <span class="recommendation-detail-value">New Build</span>
                                    </div>
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Nearest LCE Store</span>
                                        <span class="recommendation-detail-value">#${{storeData.nearest_existing_store || 'N/A'}}</span>
                                    </div>
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Distance</span>
                                        <span class="recommendation-detail-value">${{storeData.min_distance_to_existing ? storeData.min_distance_to_existing.toFixed(1) : 'N/A'}} miles</span>
                                    </div>
                                    <div class="recommendation-detail-row">
                                        <span class="recommendation-detail-label">Opportunity</span>
                                        <span class="recommendation-detail-value">Capture untapped market</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }}
            }}

            document.getElementById('detail-content').innerHTML = detailHTML;
            document.getElementById('detail-panel').classList.add('open');
        }}

        // Close detail panel
        function closeDetailPanel() {{
            document.getElementById('detail-panel').classList.remove('open');
        }}

        // Get currently visible candidates (filtered or optimized)
        function getVisibleCandidates() {{
            const data = expansionData;
            if (!data.candidates || data.candidates.length === 0) return [];

            // If optimization is active, return optimized results
            if (optimizationResults) {{
                return optimizationResults;
            }}

            // Otherwise, return filtered candidates
            let visible = data.candidates;

            // Apply filters
            if (filters.min_sales) {{
                visible = visible.filter(c => c.predicted_annual_sales >= filters.min_sales);
            }}
            if (filters.min_population) {{
                visible = visible.filter(c => c.population >= filters.min_population);
            }}

            return visible;
        }}

        // Update metrics
        function updateMetrics() {{
            const container = document.getElementById('metrics-container');

            if (currentMode === 'current') {{
                // Use pre-computed network metrics from viz_network_metrics table
                const metrics = networkMetrics;

                if (metrics && metrics.total_existing_stores) {{
                    // Format total market reach (population in millions)
                    const marketReach = metrics.total_network_population;
                    const marketReachFormatted = marketReach >= 1000000
                        ? `${{(marketReach / 1000000).toFixed(1)}}M`
                        : `${{Math.round(marketReach / 1000).toLocaleString()}}K`;

                    container.innerHTML = `
                        <div class="section-header">Network Metrics</div>
                        <div class="metrics">
                            <div class="metric-card">
                                <div class="metric-label">Total Stores</div>
                                <div class="metric-value">${{metrics.total_existing_stores}}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Total Market Reach</div>
                                <div class="metric-value">${{marketReachFormatted}}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Avg Store Population</div>
                                <div class="metric-value">${{Math.round(metrics.avg_store_population).toLocaleString()}}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Avg POIs per Store</div>
                                <div class="metric-value">${{Math.round(metrics.avg_store_poi).toLocaleString()}}</div>
                            </div>
                        </div>
                    `;
                }}
            }} else if (currentMode === 'expansion') {{
                const data = expansionData;
                const metrics = networkMetrics;

                if (data.candidates && data.candidates.length > 0) {{
                    // Get visible candidates (filtered or optimized)
                    const visibleCandidates = getVisibleCandidates();

                    // Calculate metrics from visible candidates only
                    const totalRevenue = visibleCandidates.reduce((sum, c) => sum + c.predicted_annual_sales, 0);
                    const partnershipCount = visibleCandidates.filter(c => c.fulfillment_strategy === 'partner').length;

                    // Calculate median revenue from visible candidates
                    const salesSorted = visibleCandidates
                        .map(c => c.predicted_annual_sales)
                        .sort((a, b) => a - b);
                    const medianRevenue = salesSorted.length > 0
                        ? salesSorted[Math.floor(salesSorted.length / 2)]
                        : 0;

                    container.innerHTML = `
                        <div class="section-header">Expansion Metrics</div>
                        <div class="metrics">
                            <div class="metric-card">
                                <div class="metric-label">Expansion Candidates</div>
                                <div class="metric-value">${{visibleCandidates.length}}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Total Revenue Potential</div>
                                <div class="metric-value">$${{(totalRevenue / 1000000).toFixed(1)}}M</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Median Candidate Revenue</div>
                                <div class="metric-value">$${{Math.round(medianRevenue).toLocaleString()}}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Partnership Opportunities</div>
                                <div class="metric-value">${{partnershipCount}}</div>
                            </div>
                        </div>
                    `;
                }}
            }}
        }}

        // Render controls based on mode
        function renderControls() {{
            const container = document.getElementById('controls-container');

            if (currentMode === 'current') {{
                container.innerHTML = `
                    <div class="section-header">Layer Controls</div>
                    <div class="control-group">
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-stores" ${{layers.stores ? 'checked' : ''}}>
                            <label for="layer-stores">Current Stores</label>
                        </div>
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-trade" ${{layers.trade_areas ? 'checked' : ''}}>
                            <label for="layer-trade">5-min Trade Area</label>
                        </div>
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-convenience" ${{layers.convenience ? 'checked' : ''}}>
                            <label for="layer-convenience">Convenience Stores</label>
                        </div>
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-competitors" ${{layers.competitors ? 'checked' : ''}}>
                            <label for="layer-competitors">Competitors</label>
                        </div>
                    </div>
                `;

                // Add event listeners
                document.getElementById('layer-stores').addEventListener('change', e => {{
                    layers.stores = e.target.checked;
                    renderMap();
                }});
                document.getElementById('layer-trade').addEventListener('change', e => {{
                    layers.trade_areas = e.target.checked;
                    renderMap();
                }});
                document.getElementById('layer-convenience').addEventListener('change', e => {{
                    layers.convenience = e.target.checked;
                    renderMap();
                }});
                document.getElementById('layer-competitors').addEventListener('change', e => {{
                    layers.competitors = e.target.checked;
                    renderMap();
                }});

            }} else if (currentMode === 'expansion') {{
                const data = expansionData;
                const minSales = data.candidates ? Math.min(...data.candidates.map(c => c.predicted_annual_sales)) : 0;
                const maxSales = data.candidates ? Math.max(...data.candidates.map(c => c.predicted_annual_sales)) : 1000000;
                const minPop = data.candidates ? Math.min(...data.candidates.map(c => c.population)) : 0;
                const maxPop = data.candidates ? Math.max(...data.candidates.map(c => c.population)) : 100000;

                container.innerHTML = `
                    <div class="section-header">Layer Controls</div>
                    <div class="control-group">
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-candidates" ${{layers.candidates !== false ? 'checked' : ''}}>
                            <label for="layer-candidates">Expansion Candidates</label>
                        </div>
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-h3-hexagons" ${{layers.h3_hexagons ? 'checked' : ''}}>
                            <label for="layer-h3-hexagons">H3 Hexagons</label>
                        </div>
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-current" ${{layers.current_stores !== false ? 'checked' : ''}}>
                            <label for="layer-current">Current Stores</label>
                        </div>
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-convenience-exp" ${{layers.convenience ? 'checked' : ''}}>
                            <label for="layer-convenience-exp">Convenience Stores</label>
                        </div>
                        <div class="checkbox-control">
                            <input type="checkbox" id="layer-competitors-exp" ${{layers.competitors ? 'checked' : ''}}>
                            <label for="layer-competitors-exp">Competitors</label>
                        </div>
                    </div>

                    <div class="divider"></div>

                    <div class="step-indicator">
                        <div class="step-number">1</div>
                        <div class="step-label">Refine</div>
                    </div>

                    <div class="slider-control">
                        <label for="min-sales">Minimum Annual Sales</label>
                        <input type="range" id="min-sales" min="${{minSales}}" max="${{maxSales}}" value="${{filters.min_sales || minSales}}" step="1000">
                        <div class="slider-value">$${{(filters.min_sales || minSales).toLocaleString()}}</div>
                    </div>
                    <div class="slider-control">
                        <label for="min-pop">Minimum Population</label>
                        <input type="range" id="min-pop" min="${{Math.round(minPop)}}" max="${{Math.round(maxPop)}}" value="${{Math.round(filters.min_population || minPop)}}" step="100">
                        <div class="slider-value">${{Math.round(filters.min_population || minPop).toLocaleString()}}</div>
                    </div>

                    <div class="divider"></div>

                    <div class="step-indicator">
                        <div class="step-number">2</div>
                        <div class="step-label">Optimize</div>
                    </div>

                    <div class="number-control">
                        <label for="max-stores">Maximum New Stores</label>
                        <select id="max-stores">
                            ${{paramGrid.max_stores.map(val => `<option value="${{val}}" ${{val === optimizationParams.max_stores ? 'selected' : ''}}>${{val}} stores</option>`).join('')}}
                        </select>
                    </div>
                    <div class="slider-control">
                        <label for="min-dist-new">Min Distance Between New (miles)</label>
                        <input type="range" id="min-dist-new" min="1" max="10" step="0.5" value="${{optimizationParams.min_dist_new}}">
                        <div class="slider-value">${{optimizationParams.min_dist_new}} mi</div>
                    </div>
                    <div class="slider-control">
                        <label for="min-dist-existing">Min Distance from Existing (miles)</label>
                        <input type="range" id="min-dist-existing" min="1" max="10" step="0.5" value="${{optimizationParams.min_dist_existing}}">
                        <div class="slider-value">${{optimizationParams.min_dist_existing}} mi</div>
                    </div>

                    <div style="margin-top: 16px;">
                        <button class="btn btn-primary" onclick="runOptimization()">▶️ Run Optimization</button>
                        ${{optimizationResults ? '<button class="btn btn-secondary" style="margin-top: 8px;" onclick="clearOptimization()">Clear Results</button>' : ''}}
                    </div>
                `;

                // Add event listeners
                // Layer controls
                document.getElementById('layer-candidates').addEventListener('change', e => {{
                    layers.candidates = e.target.checked;
                    renderMap();
                }});
                document.getElementById('layer-h3-hexagons').addEventListener('change', e => {{
                    layers.h3_hexagons = e.target.checked;
                    renderMap();
                }});
                document.getElementById('layer-current').addEventListener('change', e => {{
                    layers.current_stores = e.target.checked;
                    renderMap();
                }});
                document.getElementById('layer-convenience-exp').addEventListener('change', e => {{
                    layers.convenience = e.target.checked;
                    renderMap();
                }});
                document.getElementById('layer-competitors-exp').addEventListener('change', e => {{
                    layers.competitors = e.target.checked;
                    renderMap();
                }});

                // Filters
                document.getElementById('min-sales').addEventListener('input', e => {{
                    filters.min_sales = parseInt(e.target.value);
                    e.target.nextElementSibling.textContent = `$${{filters.min_sales.toLocaleString()}}`;
                    renderMap();
                }});
                document.getElementById('min-pop').addEventListener('input', e => {{
                    filters.min_population = Math.round(parseInt(e.target.value));
                    e.target.nextElementSibling.textContent = Math.round(filters.min_population).toLocaleString();
                    renderMap();
                }});

                // Optimization
                document.getElementById('max-stores').addEventListener('change', e => {{
                    optimizationParams.max_stores = parseInt(e.target.value);
                }});
                document.getElementById('min-dist-new').addEventListener('input', e => {{
                    optimizationParams.min_dist_new = parseFloat(e.target.value);
                    e.target.nextElementSibling.textContent = `${{optimizationParams.min_dist_new}} mi`;
                }});
                document.getElementById('min-dist-existing').addEventListener('input', e => {{
                    optimizationParams.min_dist_existing = parseFloat(e.target.value);
                    e.target.nextElementSibling.textContent = `${{optimizationParams.min_dist_existing}} mi`;
                }});

            }}
        }}

        // Run optimization (send request to Streamlit backend)
        async function runOptimization() {{
            // Show loading state
            const button = document.querySelector('.btn-primary');
            const originalText = button.textContent;
            button.textContent = '⏳ Running...';
            button.disabled = true;

            try {{
                // Use Streamlit.setComponentValue to send data to backend
                if (window.parent.Streamlit) {{
                    window.parent.Streamlit.setComponentValue({{
                        type: 'runOptimization',
                        params: optimizationParams,
                        candidates: expansionData.candidates,
                        existing: expansionData.current_stores
                    }});
                }} else {{
                    // Fallback: run optimization in JavaScript
                    const results = runOptimizationJS(
                        expansionData.candidates,
                        expansionData.current_stores,
                        optimizationParams
                    );
                    optimizationResults = results;
                    renderControls();
                    renderMap();
                }}
            }} catch (error) {{
                console.error('Optimization error:', error);
                alert('Optimization failed. Check console for details.');
            }} finally {{
                button.textContent = originalText;
                button.disabled = false;
            }}
        }}

        // Snap value to nearest available in grid
        function snapToGrid(value, grid) {{
            return grid.reduce((prev, curr) =>
                Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
            );
        }}

        // Lookup pre-computed optimization results (O(1) instead of O(n²))
        // This replaces runOptimizationJS with a simple cache lookup
        function lookupOptimization(params) {{
            // Snap parameters to nearest pre-computed values
            const snappedParams = {{
                max_stores: snapToGrid(params.max_stores, paramGrid.max_stores),
                min_dist_new: snapToGrid(params.min_dist_new, paramGrid.min_dist_new),
                min_dist_existing: snapToGrid(params.min_dist_existing, paramGrid.min_dist_existing)
            }};

            // O(1) lookup from pre-computed cache
            const result = optimizationResultsCache.find(r =>
                r.max_stores === snappedParams.max_stores &&
                r.min_distance_new === snappedParams.min_dist_new &&
                r.min_distance_existing === snappedParams.min_dist_existing
            );

            if (result && result.selected_h3_cells) {{
                // Parse selected_h3_cells if it's a string (can happen with JSON serialization)
                let h3Cells = result.selected_h3_cells;
                if (typeof h3Cells === 'string') {{
                    try {{
                        h3Cells = JSON.parse(h3Cells);
                    }} catch (e) {{
                        console.error('Failed to parse selected_h3_cells:', e);
                        h3Cells = [];
                    }}
                }}

                // Map H3 cell IDs back to full candidate objects
                const selected = h3Cells
                    .map(h3 => expansionData.candidates.find(c => c.store_number === h3))
                    .filter(Boolean);

                console.log(`Optimization lookup: max=${{snappedParams.max_stores}}, dist_new=${{snappedParams.min_dist_new}}, dist_exist=${{snappedParams.min_dist_existing}} -> ${{selected.length}} stores`);
                return {{ selected, snappedParams, totalSales: result.total_predicted_sales }};
            }}

            // Fallback: return empty if no pre-computed result found
            console.warn('No pre-computed optimization result found for params:', snappedParams);
            return {{ selected: [], snappedParams, totalSales: 0 }};
        }}

        // Legacy function for backward compatibility (now uses lookup)
        function runOptimizationJS(candidates, existing, params) {{
            const result = lookupOptimization(params);
            return result.selected;
        }}

        // Calculate distance in miles (Haversine formula)
        function distanceMiles(lat1, lon1, lat2, lon2) {{
            const R = 3959; // Earth's radius in miles
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                     Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                     Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }}

        // Clear optimization results
        function clearOptimization() {{
            optimizationResults = null;
            renderControls();
            renderMap();
        }}

        // Mode selector (tabs)
        document.querySelectorAll('.mode-tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentMode = tab.dataset.mode;

                // Close detail panel when switching tabs
                closeDetailPanel();

                // Reset layer state for new mode
                if (currentMode === 'current') {{
                    layers = {{'stores': true, 'trade_areas': true, 'convenience': true, 'competitors': false}};
                }} else if (currentMode === 'expansion') {{
                    layers = {{'candidates': true, 'current_stores': true, 'convenience': true, 'competitors': false}};
                    filters = {{min_sales: null, min_population: null}};
                }} else if (currentMode === 'chat') {{
                    // Chat mode - show placeholder
                    document.getElementById('controls-container').innerHTML = `
                        <div style="text-align: center; padding: 40px 20px;">
                            <div style="font-size: 48px; margin-bottom: 16px;">💬</div>
                            <div style="font-size: 16px; color: #6B7280; margin-bottom: 8px;">Chat Assistant</div>
                            <div style="font-size: 14px; color: #9CA3AF;">Coming soon...</div>
                        </div>
                    `;
                    document.getElementById('metrics-container').innerHTML = '';
                    return;
                }}

                renderControls();
                renderMap();
            }});
        }});

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{
            initMap();
            renderControls();
        }});
    </script>
</body>
</html>
"""

# Render the full-page custom component
components.html(html_content, height=1000, scrolling=False)

# Listen for optimization requests
if 'optimization_request' in st.session_state:
    params = st.session_state.optimization_request
    results = run_optimization(
        st.session_state.expansion_data.get('candidates', []),
        st.session_state.expansion_data.get('current_stores', []),
        params
    )

    # Send results back to JavaScript
    st.session_state.optimization_results = results

    # Clear request
    del st.session_state.optimization_request

    # Trigger rerun to send results
    st.rerun()
