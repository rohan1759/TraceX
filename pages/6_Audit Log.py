import datetime
import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from pages.helper.auth_manager import require_auth
from pages.helper.ui_theme import apply_theme, render_sidebar_user_profile
from pages.helper import db_queries
from pages.helper.data_models import UploadAudit

st.set_page_config(
    page_title="TraceX — Audit Log",
    page_icon="resources/tracex_icon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Authentication & Strict Admin-Only Gate ────────────────────────────────────
if not require_auth():
    st.switch_page("Home.py")
    st.stop()

user_info = st.session_state.get("user_info", {})
role = st.session_state.get("role", "Officer")

# Officers and Reporters must be strictly blocked
if role.lower() != "admin":
    if role == "Reporter":
        st.error("Access denied. Use the sighting portal.")
    else:
        st.error("Access denied. Administrator privileges required to access the Audit Log.")
    st.stop()

apply_theme()
render_sidebar_user_profile(user_info, role)

# Ensure database tables exist
db_queries.create_db()

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <div style="font-size: 10px; color: #71717A; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">
            TRACEX ACCOUNTABILITY & GOVERNANCE
        </div>
        <div style="font-size: 24px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em; line-height: 1.1;">
            Sighting Upload Audit Trail
        </div>
        <div style="font-size: 12px; color: #71717A; margin-top: 6px; line-height: 1.6;">
            Comprehensive audit record tracking all citizen sighting submissions, match approvals, and record deletions.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Retrieve Distinct Reporters for Filter ────────────────────────────────────
with Session(db_queries.engine) as session:
    all_reporters = session.exec(select(UploadAudit.reporter_username)).all()
unique_reporters = sorted(list({r for r in all_reporters if r}))

# ── Filter Controls ───────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #71717A; margin-bottom: 10px;">
        Filter Audit Records
    </div>
    """,
    unsafe_allow_html=True,
)

f_col1, f_col2, f_col3 = st.columns([1.5, 1.2, 1.8], gap="medium")

with f_col1:
    reporter_options = ["All Reporters"] + unique_reporters
    selected_reporter = st.selectbox(
        "Reporter Username",
        options=reporter_options,
        index=0,
    )

with f_col2:
    selected_action = st.selectbox(
        "Action Type",
        options=["All Actions", "SUBMIT", "APPROVE", "DELETE"],
        index=0,
    )

with f_col3:
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=30)
    date_range = st.date_input(
        "Date Range",
        value=(default_start, today),
        help="Filter audit logs between start and end dates.",
    )

start_date = None
end_date = None
if isinstance(date_range, (tuple, list)):
    if len(date_range) >= 1:
        start_date = date_range[0]
    if len(date_range) >= 2:
        end_date = date_range[1]
elif isinstance(date_range, datetime.date):
    start_date = date_range
    end_date = date_range

# ── Query Records ─────────────────────────────────────────────────────────────
audit_rows = db_queries.fetch_audit_logs(
    reporter=selected_reporter,
    start_date=start_date,
    end_date=end_date,
    action=selected_action,
)

# ── Summary KPI Tiles ─────────────────────────────────────────────────────────
total_events = len(audit_rows)
submits_count = sum(1 for r in audit_rows if r.action == "SUBMIT")
approves_count = sum(1 for r in audit_rows if r.action == "APPROVE")
deletes_count = sum(1 for r in audit_rows if r.action == "DELETE")

kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
with kpi_c1:
    st.markdown(
        f"""
        <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 14px 18px; margin-bottom: 1.25rem;">
            <div style="font-size: 10px; color: #71717A; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Total Events</div>
            <div style="font-size: 22px; font-weight: 800; color: #FAFAFA; margin-top: 4px;">{total_events}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with kpi_c2:
    st.markdown(
        f"""
        <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 14px 18px; margin-bottom: 1.25rem;">
            <div style="font-size: 10px; color: #22D3EE; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Submissions</div>
            <div style="font-size: 22px; font-weight: 800; color: #22D3EE; margin-top: 4px;">{submits_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with kpi_c3:
    st.markdown(
        f"""
        <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 14px 18px; margin-bottom: 1.25rem;">
            <div style="font-size: 10px; color: #34D399; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Approvals</div>
            <div style="font-size: 22px; font-weight: 800; color: #34D399; margin-top: 4px;">{approves_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with kpi_c4:
    st.markdown(
        f"""
        <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 14px 18px; margin-bottom: 1.25rem;">
            <div style="font-size: 10px; color: #FB7185; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Deletions</div>
            <div style="font-size: 22px; font-weight: 800; color: #FB7185; margin-top: 4px;">{deletes_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Render Audit Table & CSV Export ───────────────────────────────────────────
if not audit_rows:
    st.markdown(
        """
        <div style="background: #121316; border: 1px dashed #27272A; border-radius: 6px; padding: 3rem 1.5rem; text-align: center; color: #71717A;">
            <div style="font-size: 14px; font-weight: 600; color: #E4E4E7; margin-bottom: 4px;">No Audit Events Found</div>
            <div style="font-size: 12px;">No matching accountability log entries found for the selected reporter and date filter.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    table_data = []
    for r in audit_rows:
        locality_str = ", ".join([p for p in (r.city, r.area) if p]) or "—"
        ts_str = r.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if r.timestamp else "—"
        table_data.append(
            {
                "ID": r.id,
                "Reporter": r.reporter_username,
                "City": r.city or "—",
                "Area": r.area or "—",
                "Sighting ID": r.sighting_id,
                "Action": r.action,
                "Timestamp (UTC)": ts_str,
            }
        )

    df = pd.DataFrame(table_data)

    action_col1, action_col2 = st.columns([4, 1.2])
    with action_col1:
        st.caption(f"Showing {len(df)} audit event(s)")
    with action_col2:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Export as CSV",
            data=csv_bytes,
            file_name=f"tracex_upload_audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Reporter": st.column_config.TextColumn("Reporter Username", width="medium"),
            "City": st.column_config.TextColumn("City", width="small"),
            "Area": st.column_config.TextColumn("Area", width="medium"),
            "Sighting ID": st.column_config.TextColumn("Sighting ID", width="large"),
            "Action": st.column_config.TextColumn("Action", width="small"),
            "Timestamp (UTC)": st.column_config.TextColumn("Timestamp (UTC)", width="medium"),
        },
    )

