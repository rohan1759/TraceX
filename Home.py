import base64
import yaml
import streamlit as st
from yaml import SafeLoader
import streamlit_authenticator as stauth

from pages.helper import db_queries
from pages.helper.ui_theme import apply_theme, apply_login_theme, render_sidebar_user_profile

# Initialise DB once at startup
db_queries.create_db()

# ── Streamlit Page Configuration ──────────────────────────────────────────────
st.set_page_config(
    page_title="TraceX — Officer Portal",
    page_icon="resources/tracex_icon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load Authentication Configuration ─────────────────────────────────────────
# ── Check Authentication & Auto-Login from Stored Cookie ──────────────────────
from pages.helper.auth_manager import is_authenticated, login_user

if not is_authenticated():
    apply_login_theme()

    # Load brand logo for crisp monochrome header
    try:
        with open("resources/tracex_logo.png", "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 38px; width: auto; margin-bottom: 0.6rem;" />'
    except Exception:
        logo_html = '<div style="font-size: 24px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;">TraceX</div>'

    with st.form("tracex_auth_form", clear_on_submit=False):
        st.markdown(
            f'''
            <div style="text-align: center; margin-bottom: 1.75rem;">
                {logo_html}
                <div style="font-size: 13px; color: #71717A; letter-spacing: -0.01em;">
                    Sign in to access your account
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        username_input = st.text_input("Username", placeholder="Enter your username")
        password_input = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not username_input or not password_input:
                st.markdown(
                    '''
                    <div style="background: #1C1315; border: 1px solid #3F1D24; border-radius: 6px; padding: 10px 14px; font-size: 12px; color: #FCA5A5; text-align: center; margin-top: 12px;">
                        Please enter both username and password.
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
            else:
                success, error_msg = login_user(username_input.strip(), password_input)
                if not success:
                    st.markdown(
                        f'''
                        <div style="background: #1C1315; border: 1px solid #3F1D24; border-radius: 6px; padding: 10px 14px; font-size: 12px; color: #FCA5A5; text-align: center; margin-top: 12px;">
                            {error_msg or "Invalid credentials. Please verify your details."}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

    st.stop()


# ── Post-login: Authenticated Dashboard ───────────────────────────────────────
apply_theme()

user_info = st.session_state.get("user_info", {})
role = st.session_state.get("role", "Officer")
is_admin = role.lower() == "admin"
st.session_state["login_status"] = True

# Persistent profile badge & sign out button in sidebar
render_sidebar_user_profile(user_info, role)

role_chip_class = "tx-chip-rose" if is_admin else "tx-chip-emerald"


# ── Precision Officer Header Bar ──────────────────────────────────────────────
st.markdown(
    f"""
    <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 22px 26px; margin-bottom: 1.25rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="font-size: 10px; font-weight: 600; color: #71717A; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">
                    INVESTIGATING OFFICER PORTAL
                </div>
                <div style="font-size: 22px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.02em;">
                    Welcome, {user_info["name"]}
                </div>
                <div style="display:flex; align-items:center; gap:8px; margin-top: 8px; flex-wrap:wrap;">
                    <span class="tx-chip {role_chip_class}">{role}</span>
                    <span class="tx-chip">
                        {user_info["area"]}, {user_info["city"]}
                    </span>
                    <span class="tx-chip tx-chip-emerald">
                        ● InsightFace 512-d ArcFace
                    </span>
                </div>
            </div>
            <div>
                <div class="tx-chip" style="font-family: ui-monospace, monospace; font-size: 11px;">
                    Match Distance Cutoff: <b style="color: #FFFFFF; margin-left: 4px;">0.48</b>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Database Metrics Fetch ────────────────────────────────────────────────────
found_cases = db_queries.get_registered_cases_count(
    st.session_state["user"], "F", is_admin=is_admin
)
non_found_cases = db_queries.get_registered_cases_count(
    st.session_state["user"], "NF", is_admin=is_admin
)
public_sightings = db_queries.get_public_cases_count()
total_registered = len(found_cases) + len(non_found_cases)

# ── KPI Cards: Equal Pixel-Perfect Dimensions (Height: 114px) ─────────────────
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(
        f"""
        <div class="tx-kpi-card">
            <div class="tx-kpi-head">
                <span class="tx-kpi-title">TOTAL REGISTERED</span>
                <span style="width: 6px; height: 6px; border-radius: 50%; background: #71717A;"></span>
            </div>
            <div class="tx-kpi-value">{total_registered}</div>
            <div class="tx-kpi-sub">All indexed case files</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f"""
        <div class="tx-kpi-card">
            <div class="tx-kpi-head">
                <span class="tx-kpi-title">ACTIVE SEARCHING</span>
                <span style="width: 6px; height: 6px; border-radius: 50%; background: #F59E0B;"></span>
            </div>
            <div class="tx-kpi-value">{len(non_found_cases)}</div>
            <div class="tx-kpi-sub">Unresolved case records</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f"""
        <div class="tx-kpi-card">
            <div class="tx-kpi-head">
                <span class="tx-kpi-title">SOLVED & FOUND</span>
                <span style="width: 6px; height: 6px; border-radius: 50%; background: #10B981;"></span>
            </div>
            <div class="tx-kpi-value">{len(found_cases)}</div>
            <div class="tx-kpi-sub">Matches confirmed & closed</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi4:
    st.markdown(
        f"""
        <div class="tx-kpi-card">
            <div class="tx-kpi-head">
                <span class="tx-kpi-title">PUBLIC SIGHTINGS</span>
                <span style="width: 6px; height: 6px; border-radius: 50%; background: #06B6D4;"></span>
            </div>
            <div class="tx-kpi-value">{public_sightings}</div>
            <div class="tx-kpi-sub">Citizen reports received</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

# ── Geographic Case Distribution ──────────────────────────────────────────────
st.markdown(
    """
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.75rem;">
        <div style="font-size: 13px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.04em; text-transform: uppercase;">
            GEOGRAPHIC CASE DISTRIBUTION
        </div>
        <div style="font-size: 11px; color: #52525B;">
            National Sighting Grid &bull; Esri Dark Telemetry
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    import folium
    from streamlit_folium import st_folium

    CITY_COORDS = {
        "Delhi": (28.6139, 77.2090),
        "Mumbai": (19.0760, 72.8777),
        "Bangalore": (12.9716, 77.5946),
        "Kolkata": (22.5726, 88.3639),
        "Chennai": (13.0827, 80.2707),
        "Hyderabad": (17.3850, 78.4867),
        "Pune": (18.5204, 73.8567),
        "Ahmedabad": (23.0225, 72.5714),
        "Jaipur": (26.9124, 75.7873),
        "Lucknow": (26.8467, 80.9462),
        "Chandigarh": (30.7333, 76.7794),
        "Bhopal": (23.2599, 77.4126),
        "Patna": (25.5941, 85.1376),
        "Ranchi": (23.3441, 85.3096),
        "Jamshedpur": (22.8046, 86.2029),
        "Dehradun": (30.3165, 78.0322),
        "Varanasi": (25.3176, 82.9739),
        "Agra": (27.1767, 78.0081),
        "Amritsar": (31.6340, 74.8723),
        "Surat": (21.1702, 72.8311),
        "Kanpur": (26.4499, 80.3319),
        "Nagpur": (21.1458, 79.0882),
        "Indore": (22.7196, 75.8577),
        "Thane": (19.2183, 72.9781),
        "Visakhapatnam": (17.6868, 83.2185),
        "Pimpri-Chinchwad": (18.6298, 73.7997),
        "Vadodara": (22.3072, 73.1812),
        "Ghaziabad": (28.6692, 77.4538),
        "Ludhiana": (30.9010, 75.8573),
        "Coimbatore": (11.0168, 76.9558),
        "Madurai": (9.9252, 78.1198),
        "Nashik": (19.9975, 73.7898),
        "Faridabad": (28.4089, 77.3178),
        "Meerut": (28.9845, 77.7064),
        "Rajkot": (22.3039, 70.8022),
        "Kalyan-Dombivli": (19.2403, 73.1305),
        "Vasai-Virar": (19.4259, 72.8225),
        "Varanasi": (25.3176, 82.9739),
        "Srinagar": (34.0837, 74.7973),
        "Aurangabad": (19.8762, 75.3433),
        "Dhanbad": (23.7957, 86.4304),
        "Amritsar": (31.6340, 74.8723),
        "Navi Mumbai": (19.0330, 73.0297),
        "Allahabad": (25.4358, 81.8463),
        "Howrah": (22.5958, 88.2636),
        "Gwalior": (26.2183, 78.1828),
        "Jabalpur": (23.1815, 79.9864),
        "Coimbatore": (11.0168, 76.9558),
        "Vijayawada": (16.5062, 80.6480),
        "Jodhpur": (26.2389, 73.0243),
        "Madurai": (9.9252, 78.1198),
        "Raipur": (21.2514, 81.6296),
        "Kota": (25.2138, 75.8648),
        "Guwahati": (26.1445, 91.7362),
        "Chandigarh": (30.7333, 76.7794),
        "Solapur": (17.6599, 75.9064),
        "Hubli-Dharwad": (15.3647, 75.1240),
        "Bareilly": (28.3670, 79.4304),
        "Moradabad": (28.8386, 78.7733),
        "Mysore": (12.2958, 76.6394),
        "Gurgaon": (28.4595, 77.0266),
        "Aligarh": (27.8974, 78.0880),
        "Jalandhar": (31.3260, 75.5762),
        "Tiruchirappalli": (10.7905, 78.7047),
        "Bhubaneswar": (20.2961, 85.8245),
        "Salem": (11.6643, 78.1460),
        "Mira-Bhayandar": (19.2952, 72.8544),
        "Warangal": (17.9689, 79.5941),
        "Thiruvananthapuram": (8.5241, 76.9366),
        "Bhiwandi": (19.3002, 73.0635),
        "Saharanpur": (29.9640, 77.5452),
        "Guntur": (16.3067, 80.4365),
        "Amravati": (20.9320, 77.7523),
        "Bikaner": (28.0229, 73.3119),
        "Noida": (28.5355, 77.3910),
        "Jamshedpur": (22.8046, 86.2029),
        "Bhilai": (21.2144, 81.3800),
        "Cuttack": (20.4625, 85.8830),
        "Firozabad": (27.1593, 78.3957),
        "Kochi": (9.9312, 76.2673),
        "Nellore": (14.4426, 79.9865),
        "Bhavnagar": (21.7645, 72.1519),
        "Dehradun": (30.3165, 78.0322),
        "Durgapur": (23.5204, 87.3119),
        "Asansol": (23.6739, 86.9524),
        "Rourkela": (22.2604, 84.8536),
        "Nanded": (19.1383, 77.3210),
        "Kolhapur": (16.7050, 74.2433),
        "Ajmer": (26.4499, 74.6399),
        "Akola": (20.7002, 77.0082),
        "Gulbarga": (17.3297, 76.8343),
        "Jamnagar": (22.4707, 70.0577),
        "Ujjain": (23.1765, 75.7885),
        "Loni": (28.7501, 77.2889),
        "Siliguri": (26.7271, 88.3953),
        "Jhansi": (25.4484, 78.5685),
        "Ulhasnagar": (19.2215, 73.1645),
        "Jammu": (32.7266, 74.8570),
        "Sangli-Miraj & Kupwad": (16.8524, 74.5815),
        "Mangalore": (12.9141, 74.8560),
        "Erode": (11.3410, 77.7172),
        "Belgaum": (15.8497, 74.4977),
        "Ambattur": (13.1143, 80.1548),
        "Tirunelveli": (8.7139, 77.7567),
        "Malegaon": (20.5534, 74.5240),
        "Gaya": (24.7914, 85.0002),
        "Jalgaon": (21.0077, 75.5626),
        "Udaipur": (24.5854, 73.7125),
        "Maheshtala": (22.5085, 88.2532),
        "Davanagere": (14.4644, 75.9218),
        "Kozhikode": (11.2588, 75.7804),
        "Kurnool": (15.8281, 78.0373),
        "Rajpur Sonarpur": (22.4337, 88.4062),
        "Rajahmundry": (17.0005, 81.8040),
        "Bokaro": (23.6693, 86.1511),
        "South Dumdum": (22.6186, 88.3965),
        "Bellary": (15.1394, 76.9214),
        "Patiala": (30.3398, 76.3869),
        "Gopalpur": (22.5312, 88.3308),
        "Agartala": (23.8315, 91.2868),
        "Bhagalpur": (25.2425, 86.9842),
        "Muzaffarnagar": (29.4727, 77.7085),
        "Bhatpara": (22.8732, 88.4082),
        "Panihati": (22.6934, 88.3752),
        "Latur": (18.4088, 76.5604),
        "Dhule": (20.9042, 74.7749),
        "Rohtak": (28.8955, 76.6066),
        "Korba": (22.3595, 82.7501),
        "Bhilwara": (25.3407, 74.6313),
        "Brahmapur": (19.3150, 84.7941),
        "Muzaffarpur": (26.1209, 85.3647),
        "Ahmednagar": (19.0952, 74.7496),
        "Mathura": (27.4924, 77.6737),
        "Kollam": (8.8932, 76.6141),
        "Avadi": (13.1147, 80.1098),
        "Kadapa": (14.4673, 78.8242),
        "Kamarhati": (22.6710, 88.3748),
        "Sambalpur": (21.4669, 83.9812),
        "Bilaspur": (22.0797, 82.1409),
        "Shahjahanpur": (27.8805, 79.9142),
        "Satara": (17.6805, 73.9997),
        "Bijapur": (16.8302, 75.7100),
        "Rampur": (28.7997, 79.0257),
        "Shimoga": (13.9299, 75.5681),
        "Chandrapur": (19.9615, 79.2961),
        "Junagadh": (21.5222, 70.4579),
        "Thrissur": (10.5276, 76.2144),
        "Alwar": (27.5530, 76.6346),
        "Bardhaman": (23.2324, 87.8615),
        "Kulti": (23.7300, 86.8500),
        "Nizamabad": (18.6725, 78.0940),
        "Parbhani": (19.2612, 76.7766),
        "Tumkur": (13.3409, 77.1006),
        "Khammam": (17.2473, 80.1514),
        "Ozhukarai": (11.9539, 79.7770),
        "Bihar Sharif": (25.1982, 85.5149),
        "Panipat": (29.3909, 76.9635),
        "Darbhanga": (26.1542, 85.8918),
        "Bally": (22.6500, 88.3400),
        "Aizawl": (23.7271, 92.7176),
        "Dewas": (22.9676, 76.0534),
        "Ichalkaranji": (16.6923, 74.4594),
        "Karnal": (29.6857, 76.9905),
        "Bathinda": (30.2110, 74.9455),
        "Jalna": (19.8410, 75.8864),
        "Eluru": (16.7107, 81.0952),
        "Barasat": (22.7230, 88.4819),
        "Kirari Suleman Nagar": (28.7041, 77.0465),
        "Purnia": (25.7771, 87.4753),
        "Satna": (24.6005, 80.8322),
        "Mau": (25.9417, 83.5611),
        "Sonipat": (28.9931, 77.0151),
        "Farrukhabad": (27.3826, 79.5841),
        "Sagar": (23.8388, 78.7378),
        "Rourkela": (22.2604, 84.8536),
        "Durg": (21.1904, 81.2849),
        "Imphal": (24.8170, 93.9368),
        "Ratlam": (23.3315, 75.0367),
        "Hapur": (28.7306, 77.7759),
        "Arrah": (25.5560, 84.6603),
        "Karimnagar": (18.4386, 79.1288),
        "Anantapur": (14.6819, 77.6006),
        "Etawah": (26.7769, 79.0232),
        "Ambernath": (19.1825, 73.1926),
        "North Dumdum": (22.6528, 88.4078),
        "Bharatpur": (27.2152, 77.5030),
        "Begusarai": (25.4182, 86.1272),
        "New Delhi": (28.6139, 77.2090),
        "Gandhinagar": (23.2156, 72.6369),
        "Baranagar": (22.6433, 88.3653),
        "Tiruvottiyur": (13.1600, 80.3000),
        "Puducherry": (11.9416, 79.8083),
        "Sikar": (27.6094, 75.1398),
        "Thoothukudi": (8.7642, 78.1348),
        "Rewa": (24.5362, 81.3037),
        "Mirzapur": (25.1460, 82.5690),
        "Raichur": (16.2120, 77.3439),
        "Pali": (25.7711, 73.3234),
        "Ramagundam": (18.7551, 79.5134),
        "Haridwar": (29.9457, 78.1642),
        "Vijayanagaram": (18.1067, 83.3956),
        "Katihar": (25.5434, 87.5684),
        "Nagarcoil": (8.1833, 77.4119),
        "Sri Ganganagar": (29.9038, 73.8772),
        "Karawal Nagar": (28.7249, 77.2713),
        "Mango": (22.8256, 86.2081),
        "Thanjavur": (10.7870, 79.1378),
        "Bulandshahr": (28.4070, 77.8498),
        "Uluberia": (22.4744, 88.1097),
        "Murwara": (23.8343, 80.3992),
        "Sambhal": (28.5847, 78.5714),
        "Singrauli": (24.1997, 82.6645),
        "Nadiad": (22.6916, 72.8634),
        "Secunderabad": (17.4399, 78.4983),
        "Naihati": (22.8904, 88.4239),
        "Yamunanagar": (30.1290, 77.2674),
        "Bidhannagar": (22.5868, 88.4178),
        "Pallavaram": (12.9675, 80.1491),
        "Bidar": (17.9104, 77.5199),
        "Munger": (25.3757, 86.4744),
        "Panchkula": (30.6942, 76.8606),
        "Burhanpur": (21.3144, 76.2307),
        "Raurkela Industrial Township": (22.2223, 84.8718),
        "Kharagpur": (22.3460, 87.2320),
        "Dindigul": (10.3673, 77.9803),
        "Gandhidham": (23.0753, 70.1337),
        "Hospet": (15.2689, 76.3909),
        "Nangloi Jat": (28.6833, 77.0667),
        "Malda": (25.0108, 88.1411),
        "Ongole": (15.5057, 80.0499),
        "Deoghar": (24.4826, 86.6997),
        "Chapra": (25.7848, 84.7274),
        "Haldia": (22.0667, 88.0698),
        "Khandwa": (21.8314, 76.3498),
        "Nandyal": (15.4886, 78.4846),
        "Morena": (26.4947, 77.9940),
        "Amroha": (28.9044, 78.4682),
        "Anand": (22.5645, 72.9289),
        "Bhind": (26.5644, 78.7848),
        "Bhalswa Jahangir Pur": (28.7356, 77.1639),
        "Madhyamgram": (22.7000, 88.4500),
        "Bhiwani": (28.7932, 76.1390),
        "Navsari": (20.9500, 72.9300),
        "Bahraich": (27.5705, 81.5977),
        "Rishikesh": (30.0869, 78.2676),
        "Shimla": (31.1048, 77.1734),
        "Bathinda": (30.2110, 74.9455),
        "Unknown": (20.5937, 78.9629),
    }

    counts = db_queries.get_case_counts_by_city()

    if not counts:
        st.markdown(
            """
            <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 3rem 1.5rem; text-align: center;">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:40px; height:40px; border-radius:5px; background:#18191E; border:1px solid #27272A; margin-bottom:0.75rem;">
                    <span style="font-size: 16px;"></span>
                </div>
                <div style="font-size: 14px; font-weight: 600; color: #FFFFFF;">No Case Geodata Recorded Yet</div>
                <div style="font-size: 12px; color: #71717A; margin-top: 0.25rem;">
                    Register missing person files with city metadata to populate national cluster distribution.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
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

        for city, data in counts.items():
            total = data["found"] + data["not_found"]
            coords = CITY_COORDS.get(city)
            if coords is None:
                for key, val in CITY_COORDS.items():
                    if key.lower() == city.lower():
                        coords = val
                        break
            if coords is None:
                continue

            color = "#F43F5E" if data["not_found"] > 0 else "#10B981"
            tooltip = (
                f"<b>{city}</b><br>"
                f"Total: {total} &nbsp;|&nbsp; "
                f"Searching: {data['not_found']} &nbsp;|&nbsp; "
                f"Found: {data['found']}"
            )
            folium.CircleMarker(
                location=coords,
                radius=max(6, min(28, total * 5)),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.65,
                weight=1.5,
                tooltip=folium.Tooltip(tooltip),
            ).add_to(m)

        st_folium(m, width="100%", height=420, returned_objects=[])

        st.markdown(
            """
            <div style="display:flex; gap:16px; font-size: 11px; color: #71717A; margin-top: 0.5rem;">
                <span><span style="color:#F43F5E;">●</span> Unresolved (NF) Cases</span>
                <span><span style="color:#10B981;">●</span> All Cases Resolved (F)</span>
                <span>Radius denotes density</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

except ImportError:
    st.info("Install `folium` and `streamlit-folium` to enable the map.")
