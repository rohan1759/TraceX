import streamlit as st
from pages.helper import db_queries

st.set_page_config(
    page_title="TraceX — Geospatial Map",
    page_icon="resources/tracex_icon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

from pages.helper.auth_manager import require_auth
if not require_auth():
    st.switch_page("Home.py")

from pages.helper.ui_theme import apply_theme, render_sidebar_user_profile
apply_theme()
user_info = st.session_state.get("user_info", {})
role = st.session_state.get("role", "Officer")
render_sidebar_user_profile(user_info, role)

st.markdown("""
<div style="margin-bottom: 1.75rem;">
    <div style="font-size: 10px; color: #52525B; font-weight: 700; text-transform: uppercase;
                letter-spacing: 0.1em; margin-bottom: 6px;">TRACEX GEOSPATIAL INTELLIGENCE</div>
    <div style="font-size: 26px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em; line-height: 1.1;">
        National Sighting &amp; Case Concentration Map
    </div>
    <div style="font-size: 12px; color: #71717A; margin-top: 6px; line-height: 1.6;">
        City-deterministic clustering of active cases and confirmed sightings across Indian cities.
        Marker size denotes case density; color indicates resolution status.
    </div>
</div>
""", unsafe_allow_html=True)

try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    st.error("Map dependencies not installed. Run: `pip install folium streamlit-folium`")
    st.stop()

# City coordinate lookup — deterministic placement by city name
CITY_COORDS = {
    "Delhi": (28.6139, 77.2090), "New Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777), "Bangalore": (12.9716, 77.5946),
    "Bengaluru": (12.9716, 77.5946), "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707), "Kolkata": (22.5726, 88.3639),
    "Pune": (18.5204, 73.8567), "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873), "Lucknow": (26.8467, 80.9462),
    "Chandigarh": (30.7333, 76.7794), "Bhopal": (23.2599, 77.4126),
    "Patna": (25.5941, 85.1376), "Ranchi": (23.3441, 85.3096),
    "Jamshedpur": (22.8046, 86.2029), "Dehradun": (30.3165, 78.0322),
    "Varanasi": (25.3176, 82.9739), "Agra": (27.1767, 78.0081),
    "Amritsar": (31.6340, 74.8723), "Surat": (21.1702, 72.8311),
    "Kanpur": (26.4499, 80.3319), "Nagpur": (21.1458, 79.0882),
    "Indore": (22.7196, 75.8577), "Thane": (19.2183, 72.9781),
    "Visakhapatnam": (17.6868, 83.2185), "Vadodara": (22.3072, 73.1812),
    "Ghaziabad": (28.6692, 77.4538), "Ludhiana": (30.9010, 75.8573),
    "Coimbatore": (11.0168, 76.9558), "Madurai": (9.9252, 78.1198),
    "Nashik": (19.9975, 73.7898), "Faridabad": (28.4089, 77.3178),
    "Meerut": (28.9845, 77.7064), "Rajkot": (22.3039, 70.8022),
    "Srinagar": (34.0837, 74.7973), "Aurangabad": (19.8762, 75.3433),
    "Dhanbad": (23.7957, 86.4304), "Navi Mumbai": (19.0330, 73.0297),
    "Allahabad": (25.4358, 81.8463), "Howrah": (22.5958, 88.2636),
    "Gwalior": (26.2183, 78.1828), "Jabalpur": (23.1815, 79.9864),
    "Vijayawada": (16.5062, 80.6480), "Jodhpur": (26.2389, 73.0243),
    "Raipur": (21.2514, 81.6296), "Kota": (25.2138, 75.8648),
    "Guwahati": (26.1445, 91.7362), "Noida": (28.5355, 77.3910),
    "Gurgaon": (28.4595, 77.0266), "Gurugram": (28.4595, 77.0266),
    "Kochi": (9.9312, 76.2673), "Thiruvananthapuram": (8.5241, 76.9366),
    "Bhubaneswar": (20.2961, 85.8245), "Kozhikode": (11.2588, 75.7804),
    "Mysore": (12.2958, 76.6394), "Thrissur": (10.5276, 76.2144),
    "Shimla": (31.1048, 77.1734), "Jammu": (32.7266, 74.8570),
    "Imphal": (24.8170, 93.9368), "Aizawl": (23.7271, 92.7176),
    "Puducherry": (11.9416, 79.8083), "Gandhinagar": (23.2156, 72.6369),
    "Unknown": (20.5937, 78.9629),
}

counts = db_queries.get_case_counts_by_city()

if not counts:
    st.markdown("""
    <div style="background:#121316;border:1px solid #1E2025;border-radius:6px;
                padding:3rem 1.5rem;text-align:center;">
        <div style="display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;
                    border-radius:5px;background:#18191E;border:1px solid #27272A;margin-bottom:12px;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3F3F46"
                 stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
            </svg>
        </div>
        <div style="font-size:14px;font-weight:600;color:#FFFFFF;margin-bottom:4px;">No Case Geodata Recorded Yet</div>
        <div style="font-size:12px;color:#71717A;line-height:1.6;">
            Register missing person cases with a <strong style="color:#A1A1AA;">City</strong> field
            to populate the national cluster distribution map.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Build Folium map
m = folium.Map(
    location=[20.5937, 78.9629],
    zoom_start=5,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    overlay=True,
    name="Labels",
    control=False,
).add_to(m)

placed = 0
skipped = []
for city, data in counts.items():
    total = data["found"] + data["not_found"]
    coords = CITY_COORDS.get(city)
    if coords is None:
        city_lower = city.lower()
        for key, val in CITY_COORDS.items():
            if key.lower() == city_lower:
                coords = val
                break
    if coords is None:
        skipped.append(city)
        continue

    radius = max(8, min(40, total * 6))
    color = "#F43F5E" if data["not_found"] > 0 else "#10B981"
    tooltip = (
        f"<b>{city}</b><br>"
        f"Total: {total} &nbsp;|&nbsp; "
        f"Open: {data['not_found']} &nbsp;|&nbsp; "
        f"Resolved: {data['found']}"
    )
    folium.CircleMarker(
        location=coords,
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.65,
        weight=1.5,
        tooltip=folium.Tooltip(tooltip),
    ).add_to(m)
    placed += 1

st_folium(m, width="100%", height=520, returned_objects=[])

# ── Legend ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:20px;margin-top:12px;flex-wrap:wrap;">
    <span style="font-size:11px;color:#A1A1AA;display:flex;align-items:center;gap:6px;">
        <span style="width:10px;height:10px;border-radius:50%;background:#F43F5E;display:inline-block;"></span>
        Has Unresolved Cases
    </span>
    <span style="font-size:11px;color:#A1A1AA;display:flex;align-items:center;gap:6px;">
        <span style="width:10px;height:10px;border-radius:50%;background:#10B981;display:inline-block;"></span>
        All Cases Resolved
    </span>
    <span style="font-size:11px;color:#52525B;">Circle radius = case count density</span>
    <span style="font-size:11px;color:#52525B;">Markers placed by city name lookup</span>
</div>
""", unsafe_allow_html=True)

if skipped:
    st.markdown(f"""
    <div style="margin-top:8px;font-size:11px;color:#52525B;font-style:italic;">
        Cities not mapped (no coordinates): {", ".join(skipped)}
    </div>
    """, unsafe_allow_html=True)

# ── Summary table ─────────────────────────────────────────────────────────────
st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
            color:#52525B;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
    City Summary
    <span style="flex:1;height:1px;background:#1E2025;"></span>
</div>
""", unsafe_allow_html=True)

import pandas as pd
rows = [
    {"City": city, "Total": d["found"] + d["not_found"], "Resolved": d["found"], "Open": d["not_found"]}
    for city, d in counts.items()
]
df = pd.DataFrame(rows).sort_values("Total", ascending=False).reset_index(drop=True)
st.dataframe(df, use_container_width=True, hide_index=True)
