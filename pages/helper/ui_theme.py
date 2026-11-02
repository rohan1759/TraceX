import streamlit as st


def apply_theme():
    """Apply the unified TraceX theme, logo, responsive sidebar and full-width layout."""
    st.logo(
        "resources/tracex_logo.png",
        size="large",
        icon_image="resources/tracex_icon.png",
    )

    st.markdown(
        """
        <style>
        /* ── Canvas & Surface Tokens ────────────────────────────────────────── */
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background-color: #090A0C !important;
            color: #E4E4E7 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif !important;
        }

        /* Prevent double window scrollbar; establish layout viewport */
        html, body, .stApp {
            height: 100vh !important;
            overflow: hidden !important;
        }

        /* ── Main Viewport Container ────────────────────────────────────────── */
        [data-testid="stAppViewContainer"] {
            display: flex !important;
            flex-direction: row !important;
            width: 100% !important;
            height: 100vh !important;
            max-height: 100vh !important;
            overflow: hidden !important;
        }

        /* ── Right Panel (Main Content): Dedicated Smooth Scrolling ─────────── */
        [data-testid="stMain"],
        .main {
            flex: 1 1 auto !important;
            width: 100% !important;
            min-width: 0 !important;
            height: 100% !important;
            max-height: 100vh !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scroll-behavior: smooth !important;
            -webkit-overflow-scrolling: touch !important;
            /* No transition — prevents flash on tab switch */
        }

        /* Sleek Obsidian Scrollbar for Right Panel */
        [data-testid="stMain"]::-webkit-scrollbar,
        .main::-webkit-scrollbar {
            width: 7px !important;
            height: 7px !important;
        }
        [data-testid="stMain"]::-webkit-scrollbar-track,
        .main::-webkit-scrollbar-track {
            background: #090A0C !important;
        }
        [data-testid="stMain"]::-webkit-scrollbar-thumb,
        .main::-webkit-scrollbar-thumb {
            background: #27272A !important;
            border-radius: 4px !important;
        }
        [data-testid="stMain"]::-webkit-scrollbar-thumb:hover,
        .main::-webkit-scrollbar-thumb:hover {
            background: #3F3F46 !important;
        }

        /* ── Sidebar: Dark Obsidian Surface - PERMANENTLY LOCKED OPEN ───────── */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"][aria-expanded="true"],
        section[data-testid="stSidebar"][aria-expanded="false"] {
            display: block !important;
            visibility: visible !important;
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
            transform: none !important;
            margin-left: 0 !important;
            background-color: #0D0E11 !important;
            border-right: 1px solid #18191E !important;
            overflow: visible !important;
            transition: none !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
        section[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarContent"],
        section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarContent"] {
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
            background-color: #0D0E11 !important;
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
            padding-top: 0.5rem !important;
            visibility: visible !important;
            opacity: 1 !important;
            overflow-y: auto !important;
        }

        /* ── Permanently remove sidebar collapse and expand controls ───────── */
        [data-testid="stSidebarCollapseButton"],
        button[data-testid="stSidebarCollapseButton"],
        button[aria-label="Close sidebar"],
        button[aria-label="Collapse sidebar"],
        [data-testid="stExpandSidebarButton"],
        button[data-testid="stExpandSidebarButton"],
        button[aria-label="Open sidebar"],
        button[aria-label="Expand sidebar"],
        [data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapsedControl"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            position: absolute !important;
            clip: rect(0, 0, 0, 0) !important;
        }

        /* Logo at top of sidebar */
        [data-testid="stSidebarHeader"] {
            padding: 1.4rem 1.25rem 0.85rem 1.25rem !important;
            border-bottom: 1px solid #18191E !important;
            margin-bottom: 0.25rem !important;
        }
        [data-testid="stLogo"] {
            height: auto !important;
        }
        [data-testid="stLogo"] img {
            height: 40px !important;
            max-height: 44px !important;
            width: auto !important;
        }

        /* Gap from top for navigation items */
        [data-testid="stSidebarNav"] {
            padding-top: 1.5rem !important;
            margin-top: 0.5rem !important;
        }
        [data-testid="stSidebarNav"] ul {
            padding: 0 10px !important;
            gap: 4px !important;
        }
        [data-testid="stSidebarNav"] li a {
            border-radius: 5px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            color: #8A8F98 !important;
            padding: 8px 12px !important;
            transition: all 0.15s ease !important;
        }
        [data-testid="stSidebarNav"] li a:hover {
            background-color: #15161B !important;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebarNav"] li [aria-current="page"] {
            background-color: #181920 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: 1px solid #27272A !important;
        }

        /* Themed Ghost Sign Out button in sidebar */
        section[data-testid="stSidebar"] div.stButton > button {
            background: #14151A !important;
            color: #A1A1AA !important;
            border: 1px solid #27272A !important;
            border-radius: 5px !important;
            padding: 8px 14px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            width: 100% !important;
            letter-spacing: 0.02em !important;
            transition: all 0.15s ease !important;
        }
        section[data-testid="stSidebar"] div.stButton > button:hover {
            background: #1C1E26 !important;
            color: #FFFFFF !important;
            border-color: #3F3F46 !important;
        }

        /* ── Header: ALWAYS hidden — we handle branding ourselves ─────────── */
        /* We completely kill the Streamlit header bar in all states.          */
        /* The expand button is re-exposed via the sidebar logo area.          */
        header[data-testid="stHeader"] {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }

        /* Compensate: remove top padding Streamlit adds for the header */
        [data-testid="stMain"] > div:first-child {
            padding-top: 0 !important;
        }

        /* ── Fluid Full-Width Content Container ────────────────────────────── */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 3.5rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
            max-width: 100% !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }

        /* ── Equal Dimension KPI Grid Alignment ────────────────────────────── */
        div[data-testid="column"] {
            display: flex !important;
            flex-direction: column !important;
        }
        div[data-testid="column"] > div {
            flex: 1 !important;
            display: flex !important;
            flex-direction: column !important;
        }

        .tx-kpi-card {
            background: #121316 !important;
            border: 1px solid #1E2025 !important;
            border-radius: 6px !important;
            padding: 16px 18px !important;
            height: 114px !important;
            min-height: 114px !important;
            max-height: 114px !important;
            box-sizing: border-box !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            transition: border-color 0.15s ease, background-color 0.15s ease !important;
        }
        .tx-kpi-card:hover {
            border-color: #2E323B !important;
            background-color: #14161A !important;
        }
        .tx-kpi-head {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
        }
        .tx-kpi-title {
            font-size: 11px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            color: #71717A !important;
        }
        .tx-kpi-value {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
            line-height: 1 !important;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
            letter-spacing: -0.02em !important;
        }
        .tx-kpi-sub {
            font-size: 11px !important;
            color: #52525B !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        /* ── Micro Badges (Sharp 4px Radius) ───────────────────────────────── */
        .tx-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #18181B;
            color: #A1A1AA;
            border: 1px solid #27272A;
            padding: 3px 9px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.02em;
        }
        .tx-chip-emerald {
            background: rgba(16, 185, 129, 0.08);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.25);
        }
        .tx-chip-amber {
            background: rgba(245, 158, 11, 0.08);
            color: #FCD34D;
            border: 1px solid rgba(245, 158, 11, 0.25);
        }
        .tx-chip-rose {
            background: rgba(244, 63, 94, 0.08);
            color: #FDA4AF;
            border: 1px solid rgba(244, 63, 94, 0.25);
        }

        /* ── Form Inputs ───────────────────────────────────────────────────── */
        div[data-baseweb="input"],
        div[data-baseweb="textarea"],
        div[data-baseweb="base-input"] {
            border-radius: 5px !important;
            background: #0E0F12 !important;
            border: 1px solid #22242A !important;
        }
        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea,
        div[data-baseweb="base-input"] input {
            color: #FAFAFA !important;
            font-size: 13px !important;
        }

        /* ── NUCLEAR: Completely Suppress "Press Enter to submit" everywhere ─ */
        [data-testid="InputInstructions"],
        div[data-testid="InputInstructions"],
        span[data-testid="InputInstructions"],
        small[data-testid="InputInstructions"],
        p[data-testid="InputInstructions"],
        .stChatInputInstructions,
        [class*="InputInstructions"],
        [id*="InputInstructions"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            max-height: 0 !important;
            min-height: 0 !important;
            width: 0 !important;
            max-width: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 0 !important;
            font-size: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
            overflow: hidden !important;
            position: absolute !important;
            clip: rect(0,0,0,0) !important;
        }

        /* ── Primary Action Buttons in Forms / Main Body ───────────────────── */
        div[data-testid="stForm"] button[kind="primaryFormSubmit"],
        div[data-testid="stForm"] button[type="submit"],
        div.block-container div.stButton > button {
            background: #FAFAFA !important;
            color: #090A0C !important;
            border-radius: 5px !important;
            padding: 7px 16px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            border: 1px solid #FAFAFA !important;
            transition: all 0.15s ease !important;
        }
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
        div[data-testid="stForm"] button[type="submit"]:hover,
        div.block-container div.stButton > button:hover {
            background: #E4E4E7 !important;
            border-color: #E4E4E7 !important;
        }

        /* ── Streamlit native elements: dark theme overrides ───────────────── */
        div[data-testid="stDataFrame"] {
            border: 1px solid #1E2025 !important;
            border-radius: 6px !important;
            overflow: hidden !important;
        }
        div[data-testid="stExpander"] {
            background: #121316 !important;
            border: 1px solid #1E2025 !important;
            border-radius: 6px !important;
        }
        div[data-testid="stProgress"] > div > div {
            background: #34D399 !important;
        }

        /* ── Prevent flicker on page transitions ────────────────────────────── */
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .block-container {
            will-change: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_login_theme():
    """Apply precision commercial login styling: Dead-center alignment, refined width, hairline borders, sleek toggle & button."""
    st.markdown(
        """
        <style>
        /* ── Completely suppress sidebar and controls on login ──────────────── */
        [data-testid="stSidebar"],
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarNav"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            max-width: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Canvas tokens */
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background-color: #08090A !important;
            color: #E4E4E7 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif !important;
        }

        /* Clean transparent header, hidden footer */
        header[data-testid="stHeader"] {
            display: none !important;
        }
        footer {
            display: none !important;
        }

        /* ── Hide 'Press Enter to submit form' instructions completely ─────── */
        [data-testid="InputInstructions"],
        div[data-testid="InputInstructions"],
        span[data-testid="InputInstructions"],
        small[data-testid="InputInstructions"],
        [class*="InputInstructions"],
        [id*="InputInstructions"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* ── Perfect Viewport Dead-Center Alignment ────────────────────────── */
        [data-testid="stAppViewContainer"] {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            min-height: 100vh !important;
        }

        [data-testid="stMain"] {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            padding: 0 !important;
            margin: auto 0 !important;
        }

        /* Refined Card Container Width (Balanced 430px) */
        .block-container {
            max-width: 430px !important;
            width: 100% !important;
            margin: auto !important;
            padding: 0 1.25rem !important;
        }

        /* Minimalist Designer Card */
        div[data-testid="stForm"] {
            background: #0E1013 !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px !important;
            padding: 34px 32px !important;
            box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.7), 0 0 1px 1px rgba(255, 255, 255, 0.04) inset !important;
        }

        /* Form Labels */
        div[data-testid="stForm"] label,
        div[data-testid="stTextInput"] label,
        div[data-testid="stTextInput"] label p {
            font-size: 12.5px !important;
            font-weight: 500 !important;
            color: #9CA3AF !important;
            margin-bottom: 6px !important;
            letter-spacing: -0.01em !important;
        }

        /* ── Precision Input Containers with Very Thin Hairline Border ───────── */
        div[data-testid="stTextInput"] {
            width: 100% !important;
            margin-bottom: 0.6rem !important;
        }

        div[data-testid="stTextInput"] > div {
            width: 100% !important;
        }

        div[data-baseweb="input"] {
            width: 100% !important;
            height: 42px !important;
            background: #08090A !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 6px !important;
            padding: 0 !important;
            box-sizing: border-box !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease !important;
            display: flex !important;
            align-items: center !important;
        }

        div[data-baseweb="input"]:focus-within {
            border-color: rgba(255, 255, 255, 0.35) !important;
            box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.18) !important;
            background: #0B0D0F !important;
        }

        /* Inner text input element */
        div[data-baseweb="input"] input {
            background: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            color: #F4F4F5 !important;
            padding: 0 14px !important;
            font-size: 13.5px !important;
            width: 100% !important;
            height: 100% !important;
            flex: 1 1 auto !important;
        }
        div[data-baseweb="input"] input:focus {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        div[data-baseweb="input"] input::placeholder {
            color: #52525B !important;
            font-size: 13px !important;
        }

        /* ── Password Eye Icon Toggle: Completely transparent ghost button ──── */
        div[data-testid="stTextInput"] button,
        div[data-baseweb="input"] button,
        button[aria-label="Show password"],
        button[aria-label="Hide password"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            color: #71717A !important;
            padding: 0 12px !important;
            margin: 0 !important;
            width: auto !important;
            min-width: unset !important;
            max-width: unset !important;
            height: 100% !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: color 0.15s ease !important;
        }

        div[data-testid="stTextInput"] button:hover,
        div[data-baseweb="input"] button:hover,
        button[aria-label="Show password"]:hover,
        button[aria-label="Hide password"]:hover {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            color: #FAFAFA !important;
        }

        div[data-testid="stTextInput"] button svg,
        button[aria-label="Show password"] svg,
        button[aria-label="Hide password"] svg {
            fill: currentColor !important;
            stroke: currentColor !important;
            width: 16px !important;
            height: 16px !important;
        }

        /* ── Sign In Action Button (Subtle, Refined, Clean Hover) ──────────── */
        div[data-testid="stFormSubmitButton"] {
            width: 100% !important;
            margin-top: 14px !important;
        }

        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            height: 40px !important;
            background: #FAFAFA !important;
            color: #090A0C !important;
            border-radius: 6px !important;
            padding: 0 16px !important;
            font-size: 13.5px !important;
            font-weight: 550 !important;
            letter-spacing: -0.01em !important;
            border: 1px solid rgba(255, 255, 255, 0.9) !important;
            cursor: pointer !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4) !important;
            transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease !important;
        }

        div[data-testid="stFormSubmitButton"] > button:hover {
            background: #EAEAEA !important;
            border-color: #EAEAEA !important;
            color: #090A0C !important;
            box-shadow: 0 4px 12px rgba(255, 255, 255, 0.08) !important;
            transform: translateY(-0.5px) !important;
        }

        div[data-testid="stFormSubmitButton"] > button:active {
            transform: translateY(0) !important;
            background: #DFDFDF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_user_profile(user_info: dict, role: str):
    """Render the officer profile badge and sign out button at the bottom of the sidebar."""
    with st.sidebar:
        st.markdown(
            f"""
            <div style="margin-top: auto; padding: 12px 14px; background: #121316; border: 1px solid #1E2025; border-radius: 6px; margin-bottom: 10px;">
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <div style="font-size: 12px; font-weight: 600; color: #FFFFFF;">{user_info.get("name", "Officer")}</div>
                    <span style="font-size: 10px; background: #1C1917; border: 1px solid #292524; color: #D6D3D1; padding: 2px 6px; border-radius: 4px;">{role}</span>
                </div>
                <div style="font-size: 11px; color: #71717A; margin-top: 4px; display:flex; align-items:center; gap:5px;">
                    <span style="width: 5px; height: 5px; border-radius: 50%; background: #10B981; display: inline-block;"></span> {user_info.get("city", "Station")} &bull; Active
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", key="tracex_signout_action_btn", use_container_width=True):
            from pages.helper.auth_manager import logout_user
            logout_user()
