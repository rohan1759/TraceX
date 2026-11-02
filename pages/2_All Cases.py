import os
import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="TraceX — Case Records",
    page_icon="resources/tracex_icon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

from pages.helper import db_queries, emailer
from pages.helper.ui_theme import apply_theme, render_sidebar_user_profile

from pages.helper.auth_manager import require_auth
if not require_auth():
    st.switch_page("Home.py")

apply_theme()
user_info = st.session_state.get("user_info", {})
role = st.session_state.get("role", "Officer")
render_sidebar_user_profile(user_info, role)

PAGE_SIZE = 8

# ── Card & Records Styling ───────────────────────────────────────────────────
st.html(
    """
    <style>
    /* ── High-Precision Record Cards ───────────────────────────────────────── */
    .tx-card-wrapper {
        background: #121316;
        border: 1px solid #1E2025;
        border-radius: 6px;
        margin-bottom: 1.25rem;
        overflow: hidden;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .tx-card-wrapper:hover {
        border-color: #2E323B;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .tx-card-topbar {
        background: #0E0F12;
        border-bottom: 1px solid #191B20;
        padding: 10px 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }
    .tx-card-body {
        padding: 16px 20px 14px 20px;
    }

    /* Reference & Identifier Chips */
    .tx-code-badge {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 11px;
        font-weight: 600;
        color: #A1A1AA;
        background: #18191E;
        border: 1px solid #27272A;
        padding: 2px 7px;
        border-radius: 4px;
        letter-spacing: 0.04em;
    }

    /* Person Name & Headers */
    .tx-person-name {
        font-size: 18px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.01em;
        line-height: 1.2;
    }
    .tx-person-sub {
        font-size: 12px;
        color: #71717A;
        margin-top: 3px;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    /* Attribute Grid */
    .tx-attribute-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px 18px;
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px solid #18191E;
    }
    .tx-attr-item {
        display: flex;
        flex-direction: column;
    }
    .tx-attr-label {
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #52525B;
        margin-bottom: 2px;
    }
    .tx-attr-val {
        font-size: 12.5px;
        color: #D4D4D8;
        line-height: 1.35;
        font-weight: 450;
        word-break: break-word;
    }
    .tx-attr-val strong {
        color: #FAFAFA;
    }

    /* Photo Frame */
    .tx-photo-frame {
        width: 100%;
        max-width: 130px;
        aspect-ratio: 1 / 1.15;
        background: #0B0C0E;
        border: 1px solid #27272A;
        border-radius: 6px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    .tx-photo-frame img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .tx-photo-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #52525B;
        padding: 12px;
        text-align: center;
    }

    /* Intel Box: Sighting Match (Cyan) */
    .tx-intel-box {
        background: rgba(6, 182, 212, 0.03);
        border: 1px solid rgba(6, 182, 212, 0.2);
        border-radius: 6px;
        padding: 14px 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .tx-intel-box-idle {
        background: #0E0F12;
        border: 1px dashed #22242A;
        border-radius: 6px;
        padding: 14px 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        text-align: center;
        color: #52525B;
    }

    /* Empty state */
    .tx-empty-card {
        background: #121316;
        border: 1px solid #1E2025;
        border-radius: 6px;
        padding: 3.5rem 1.5rem;
        text-align: center;
    }

    /* Action buttons inside cards */
    div.tx-action-row button {
        background: #181920 !important;
        color: #FAFAFA !important;
        border: 1px solid #27272A !important;
        border-radius: 4px !important;
        font-size: 11px !important;
        padding: 6px 12px !important;
        transition: all 0.15s ease !important;
    }
    div.tx-action-row button:hover {
        background: #27272A !important;
        border-color: #3F3F46 !important;
    }
    </style>
    """
)


def _reset_page(key: str):
    st.session_state[key] = 0


# ── Registered Case Renderer ─────────────────────────────────────────────────
def render_registered_case_card(case_row, is_admin: bool = False):
    """
    case_row indices:
    0: id, 1: name, 2: age, 3: status, 4: last_seen, 5: matched_with,
    6: city, 7: birth_marks, 8: complainant_name, 9: complainant_mobile,
    10: submitted_on, 11: adhaar_card, 12: father_name, 13: address, 14: description
    """
    case_id = str(case_row[0])
    name = str(case_row[1] or "Unknown Person")
    age = str(case_row[2] or "N/A")
    status = str(case_row[3] or "NF")
    last_seen = str(case_row[4] or "Unspecified location")
    matched_with_id = str(case_row[5] or "").replace("{", "").replace("}", "").strip()
    city = str(case_row[6] or "")
    birth_marks = str(case_row[7] or "")
    complainant_name = str(case_row[8] or "Official Dispatch")
    complainant_mobile = str(case_row[9] or "")
    submitted_on = case_row[10]
    adhaar_card = str(case_row[11] or "")
    father_name = str(case_row[12] or "")
    address = str(case_row[13] or "")
    description = str(case_row[14] or "")

    is_found = status.upper() == "F"
    date_str = (
        submitted_on.strftime("%d %b %Y, %H:%M")
        if isinstance(submitted_on, datetime.datetime)
        else (str(submitted_on)[:16] if submitted_on else "Recent")
    )

    # Check for matched sighting details
    matched_details = None
    if matched_with_id:
        sighting_rows = db_queries.get_public_case_detail(matched_with_id)
        if sighting_rows:
            matched_details = sighting_rows[0]
            # (location, submitted_by, mobile, birth_marks)

    # Status badges
    status_chip = (
        '<span class="tx-chip tx-chip-emerald"><span style="width:5px;height:5px;border-radius:50%;background:#10B981;display:inline-block;"></span> SOLVED & FOUND</span>'
        if is_found
        else '<span class="tx-chip tx-chip-amber"><span style="width:5px;height:5px;border-radius:50%;background:#F59E0B;display:inline-block;"></span> ACTIVE INVESTIGATION</span>'
    )

    sighting_chip = (
        '<span class="tx-chip" style="background: rgba(6,182,212,0.08); color: #22D3EE; border: 1px solid rgba(6,182,212,0.25);"><span style="width:5px;height:5px;border-radius:50%;background:#06B6D4;display:inline-block;"></span> SIGHTING VERIFIED</span>'
        if matched_details
        else ""
    )

    masked_adhaar = (
        f"•••• •••• {adhaar_card[-4:]}"
        if adhaar_card and len(adhaar_card) == 12
        else (adhaar_card or "Not recorded")
    )

    # ── Render Card Wrapper (Pure HTML via st.html to prevent markdown code block glitches) ──
    chips_html = f"{status_chip} {sighting_chip}".strip()
    st.html(
        f'<div class="tx-card-wrapper">'
        f'<div class="tx-card-topbar">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span class="tx-code-badge">CASE #{case_id[:8].upper()}</span>'
        f'<span style="font-size:11px;color:#71717A;">Indexed {date_str}</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:8px;">{chips_html}</div>'
        f'</div>'
        f'</div>'
    )

    # 3-Column Layout inside the card
    col_photo, col_info, col_intel = st.columns([1.1, 2.3, 1.8], gap="medium")

    # ── Left Column: Reference Image ──────────────────────────────────────────
    with col_photo:
        image_path = f"./resources/{case_id}.jpg"
        if os.path.exists(image_path):
            st.image(image_path, width=128)
        else:
            st.html(
                '<div class="tx-photo-frame" style="width:128px; height:140px;">'
                '<div class="tx-photo-placeholder">'
                '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#52525B" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'
                '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>'
                '<circle cx="8.5" cy="8.5" r="1.5"></circle>'
                '<polyline points="21 15 16 10 5 21"></polyline>'
                '</svg>'
                '<span style="font-size: 10px; color: #52525B; margin-top: 6px;">No Image</span>'
                '</div></div>'
            )

        st.html(
            f'<div style="margin-top:6px;display:flex;flex-direction:column;gap:3px;">'
            f'<span class="tx-chip" style="font-size:9.5px;padding:2px 6px;width:fit-content;">● ArcFace 512-d</span>'
            f'<span style="font-size:10px;color:#52525B;font-family:monospace;">UUID: {case_id[:8]}</span>'
            f'</div>'
        )

    # ── Center Column: Missing Person Data ────────────────────────────────────
    with col_info:
        father_str = f"&bull; Guardian: {father_name}" if father_name else ""
        city_str = f"&bull; City: {city}" if city else ""
        address_html = (
            f'<div style="margin-top:8px;font-size:11px;color:#71717A;">'
            f'<span style="color:#52525B;text-transform:uppercase;font-size:9.5px;font-weight:600;">Residential Address:</span> {address}'
            f'</div>'
            if address
            else ""
        )
        desc_html = (
            f'<div style="margin-top:4px;font-size:11px;color:#71717A;font-style:italic;">'
            f'&ldquo;{description}&rdquo;'
            f'</div>'
            if description
            else ""
        )

        st.html(
            f'<div>'
            f'<div class="tx-person-name">{name}</div>'
            f'<div class="tx-person-sub">'
            f'<span>Age {age} yrs</span>'
            f'{father_str}'
            f'{city_str}'
            f'</div>'
            f'</div>'
            f'<div class="tx-attribute-grid">'
            f'<div class="tx-attr-item">'
            f'<span class="tx-attr-label">Last Seen Location</span>'
            f'<span class="tx-attr-val"><strong>{last_seen}</strong></span>'
            f'</div>'
            f'<div class="tx-attr-item">'
            f'<span class="tx-attr-label">Identifying Marks</span>'
            f'<span class="tx-attr-val">{birth_marks or "None documented"}</span>'
            f'</div>'
            f'<div class="tx-attr-item">'
            f'<span class="tx-attr-label">Complainant / Contact</span>'
            f'<span class="tx-attr-val">{complainant_name} {f"({complainant_mobile})" if complainant_mobile else ""}</span>'
            f'</div>'
            f'<div class="tx-attr-item">'
            f'<span class="tx-attr-label">Aadhaar Reference</span>'
            f'<span class="tx-attr-val" style="font-family: monospace;">{masked_adhaar}</span>'
            f'</div>'
            f'</div>'
            f'{address_html}'
            f'{desc_html}'
        )

    # ── Right Column: Sighting Intelligence & Match Alerts ────────────────────
    with col_intel:
        if matched_details:
            s_loc, s_sub, s_mob, s_marks = matched_details
            marks_html = f'<div><span style="color:#52525B;">Observed:</span> {s_marks}</div>' if s_marks else ""
            st.html(
                f'<div class="tx-intel-box">'
                f'<div>'
                f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#22D3EE;display:flex;align-items:center;gap:6px;margin-bottom:8px;">'
                f'<span style="width:6px;height:6px;border-radius:50%;background:#06B6D4;"></span> VERIFIED CITIZEN SIGHTING'
                f'</div>'
                f'<div style="font-size:12px;color:#E4E4E7;margin-bottom:4px;">'
                f'<span style="color:#71717A;font-size:11px;">Spotted at:</span> <strong>{s_loc or "Unspecified"}</strong>'
                f'</div>'
                f'<div style="font-size:11px;color:#A1A1AA;line-height:1.5;">'
                f'<div><span style="color:#52525B;">Reporter:</span> {s_sub or "Anonymous"} {f"({s_mob})" if s_mob else ""}</div>'
                f'{marks_html}'
                f'</div>'
                f'</div>'
                f'</div>'
            )

            # Send Email Action for Found cases
            if is_admin and is_found:
                st.html("<div style='height: 6px;'></div>")
                if st.button("Send Alert Email", key=f"email_btn_{case_id}", use_container_width=True):
                    case_detail_rows = db_queries.get_registered_case_detail(case_id)
                    if case_detail_rows:
                        sent = emailer.send_match_notification(case_id, case_detail_rows[0])
                        comp_email = case_detail_rows[0][2] if len(case_detail_rows[0]) > 2 else None
                        if sent:
                            st.success(f"Notification email dispatched to {comp_email or 'complainant'}.")
                        else:
                            st.warning("Email could not be delivered. Please verify SMTP host credentials.")
        else:
            st.html(
                '<div class="tx-intel-box-idle">'
                '<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#71717A;margin-bottom:4px;">'
                'FACIAL RECOGNITION GRID'
                '</div>'
                '<div style="font-size:11.5px;color:#A1A1AA;">'
                'Active indexing in 512-d vector space'
                '</div>'
                '<div style="font-size:10.5px;color:#52525B;margin-top:4px;">'
                'Cosine cutoff &le; 0.48 &bull; Awaiting match'
                '</div>'
                '</div>'
            )

    # ── Admin Drawer: Case Management (Edit & Delete) ─────────────────────────
    if is_admin:
        with st.expander("Record Management (Edit / Delete Record)", expanded=False):
            with st.form(key=f"edit_form_{case_id}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_name = st.text_input("Person Name", value=name)
                    new_city = st.text_input("City", value=city)
                with ec2:
                    new_last_seen = st.text_input("Last Seen Location", value=last_seen)
                    new_marks = st.text_input("Identifying Marks", value=birth_marks)

                save_btn = st.form_submit_button("Save Record Changes")
                if save_btn:
                    db_queries.update_registered_case(
                        case_id,
                        {
                            "name": new_name.strip(),
                            "city": new_city.strip() or None,
                            "last_seen": new_last_seen.strip(),
                            "birth_marks": new_marks.strip(),
                        },
                    )
                    st.success("Case file updated successfully.")
                    st.rerun()

            dc1, dc2 = st.columns([3, 1])
            with dc1:
                confirm_del = st.checkbox(
                    "I confirm permanent deletion of this case file and biometric features.",
                    key=f"confirm_del_{case_id}",
                )
            with dc2:
                if st.button("Delete Case", key=f"del_btn_{case_id}", type="primary", use_container_width=True):
                    if confirm_del:
                        db_queries.delete_registered_case(case_id)
                        st.success("Case record permanently deleted.")
                        st.rerun()
                    else:
                        st.warning("Check confirmation box first.")

    st.html("<div style='height: 12px;'></div>")


# ── Public Sighting Case Renderer ────────────────────────────────────────────
def render_public_case_card(case_row):
    """
    case_row indices:
    0: id, 1: status, 2: location, 3: mobile, 4: birth_marks,
    5: submitted_on, 6: submitted_by, 7: email
    """
    case_id = str(case_row[0])
    status = str(case_row[1] or "NF")
    location = str(case_row[2] or "Unspecified location")
    mobile = str(case_row[3] or "Confidential")
    birth_marks = str(case_row[4] or "")
    submitted_on = case_row[5]
    submitted_by = str(case_row[6] or "Anonymous Citizen")
    email = str(case_row[7] if len(case_row) > 7 and case_row[7] else "")

    is_found = status.upper() == "F"
    date_str = (
        submitted_on.strftime("%d %b %Y, %H:%M")
        if isinstance(submitted_on, datetime.datetime)
        else (str(submitted_on)[:16] if submitted_on else "Recent")
    )

    status_chip = (
        '<span class="tx-chip tx-chip-emerald"><span style="width:5px;height:5px;border-radius:50%;background:#10B981;display:inline-block;"></span> MATCH RESOLVED</span>'
        if is_found
        else '<span class="tx-chip" style="background:rgba(6,182,212,0.08);color:#22D3EE;border:1px solid rgba(6,182,212,0.25);"><span style="width:5px;height:5px;border-radius:50%;background:#06B6D4;display:inline-block;"></span> ACTIVE CITIZEN LEAD</span>'
    )

    st.html(
        f'<div class="tx-card-wrapper">'
        f'<div class="tx-card-topbar">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span class="tx-code-badge" style="color:#22D3EE;border-color:rgba(6,182,212,0.3);">LEAD #{case_id[:8].upper()}</span>'
        f'<span style="font-size:11px;color:#71717A;">Received {date_str}</span>'
        f'</div>'
        f'<div>{status_chip}</div>'
        f'</div>'
        f'</div>'
    )

    col_photo, col_info, col_dispatch = st.columns([1.1, 2.3, 1.8], gap="medium")

    with col_photo:
        image_path = f"./resources/{case_id}.jpg"
        if os.path.exists(image_path):
            st.image(image_path, width=128)
        else:
            st.html(
                '<div class="tx-photo-frame" style="width:128px; height:140px;">'
                '<div class="tx-photo-placeholder">'
                '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#52525B" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'
                '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>'
                '<circle cx="8.5" cy="8.5" r="1.5"></circle>'
                '<polyline points="21 15 16 10 5 21"></polyline>'
                '</svg>'
                '<span style="font-size:10px;color:#52525B;margin-top:6px;">No Sighting Photo</span>'
                '</div></div>'
            )

        st.html(
            '<div style="margin-top:6px;font-size:10px;color:#52525B;font-family:monospace;">'
            'CITIZEN DISPATCH'
            '</div>'
        )

    with col_info:
        st.html(
            f'<div>'
            f'<div class="tx-person-name" style="font-size:16px;">Spotted: {location}</div>'
            f'<div class="tx-person-sub">Reported by {submitted_by} &bull; {date_str}</div>'
            f'</div>'
            f'<div class="tx-attribute-grid">'
            f'<div class="tx-attr-item">'
            f'<span class="tx-attr-label">Eyewitness Contact</span>'
            f'<span class="tx-attr-val"><strong>{mobile}</strong></span>'
            f'</div>'
            f'<div class="tx-attr-item">'
            f'<span class="tx-attr-label">Eyewitness Email</span>'
            f'<span class="tx-attr-val">{email or "Not provided"}</span>'
            f'</div>'
            f'<div class="tx-attr-item" style="grid-column: span 2;">'
            f'<span class="tx-attr-label">Observed Features &amp; Clothing</span>'
            f'<span class="tx-attr-val">{birth_marks or "No clothing or distinct markings reported"}</span>'
            f'</div>'
            f'</div>'
        )

    with col_dispatch:
        st.html(
            '<div class="tx-intel-box-idle" style="background:rgba(6,182,212,0.03);border-color:rgba(6,182,212,0.18);">'
            '<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#22D3EE;margin-bottom:4px;">'
            'CONFIDENTIAL SIGHTING LEAD'
            '</div>'
            '<div style="font-size:11px;color:#A1A1AA;line-height:1.4;">'
            'Available for bi-directional cosine similarity matching against all open missing person files.'
            '</div>'
            '</div>'
        )

    st.html("<div style='height: 12px;'></div>")


# ── Pagination Helper ────────────────────────────────────────────────────────
def paginate(items: list, page_key: str, page_size: int = PAGE_SIZE):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.session_state.get(page_key, 0)
    page = max(0, min(page, total_pages - 1))
    st.session_state[page_key] = page

    paginated = items[page * page_size : (page + 1) * page_size]

    def render_controls():
        col_prev, col_info, col_next = st.columns([1, 4, 1])
        if col_prev.button(
            "← Previous",
            disabled=page == 0,
            key=f"{page_key}_prev",
            use_container_width=True,
        ):
            st.session_state[page_key] = page - 1
            st.rerun()

        col_info.html(
            f"<div style='text-align:center; padding-top:6px; font-size:12px; color:#71717A; font-family: monospace;'>"
            f"Page <b>{page + 1}</b> of <b>{total_pages}</b> &nbsp;&bull;&nbsp; {total} record(s) indexed</div>"
        )

        if col_next.button(
            "Next →",
            disabled=page >= total_pages - 1,
            key=f"{page_key}_next",
            use_container_width=True,
        ):
            st.session_state[page_key] = page + 1
            st.rerun()

    return paginated, render_controls


# ── Main Page Execution ──────────────────────────────────────────────────────
user = st.session_state.user
is_admin = st.session_state.get("role", "").lower() == "admin"

# Header section
st.html(
    """
    <div style="margin-bottom: 1.25rem;">
        <div style="font-size: 10px; color: #71717A; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">
            TRACEX RECORDS MANAGEMENT
        </div>
        <div style="font-size: 24px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;">
            Case Files &amp; Sighting Database
        </div>
        <div style="font-size: 12px; color: #8A8F98; margin-top: 4px;">
            Search, filter, inspect, and manage registered missing person files and verified citizen sightings.
        </div>
    </div>
    """
)

# ── Summary Telemetry KPI Bar ────────────────────────────────────────────────
with st.container():
    all_reg_cases = db_queries.fetch_registered_cases(user, "All", is_admin=is_admin)
    total_reg = len(all_reg_cases)
    total_nf = sum(1 for c in all_reg_cases if c[3] == "NF")
    total_f = sum(1 for c in all_reg_cases if c[3] == "F")
    total_pub = db_queries.get_public_cases_count()

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.html(
            f"""
            <div class="tx-kpi-card" style="height: 94px; min-height: 94px; padding: 12px 16px;">
                <div class="tx-kpi-head">
                    <span class="tx-kpi-title">TOTAL CASES</span>
                    <span style="width: 5px; height: 5px; border-radius: 50%; background: #71717A;"></span>
                </div>
                <div class="tx-kpi-value" style="font-size: 24px;">{total_reg}</div>
                <div class="tx-kpi-sub">Indexed missing records</div>
            </div>
            """
        )
    with kpi2:
        st.html(
            f"""
            <div class="tx-kpi-card" style="height: 94px; min-height: 94px; padding: 12px 16px;">
                <div class="tx-kpi-head">
                    <span class="tx-kpi-title">ACTIVE SEARCH</span>
                    <span style="width: 5px; height: 5px; border-radius: 50%; background: #F59E0B;"></span>
                </div>
                <div class="tx-kpi-value" style="font-size: 24px;">{total_nf}</div>
                <div class="tx-kpi-sub">Unresolved missing cases</div>
            </div>
            """
        )
    with kpi3:
        st.html(
            f"""
            <div class="tx-kpi-card" style="height: 94px; min-height: 94px; padding: 12px 16px;">
                <div class="tx-kpi-head">
                    <span class="tx-kpi-title">RESOLVED / FOUND</span>
                    <span style="width: 5px; height: 5px; border-radius: 50%; background: #10B981;"></span>
                </div>
                <div class="tx-kpi-value" style="font-size: 24px;">{total_f}</div>
                <div class="tx-kpi-sub">Confirmed matches closed</div>
            </div>
            """
        )
    with kpi4:
        st.html(
            f"""
            <div class="tx-kpi-card" style="height: 94px; min-height: 94px; padding: 12px 16px;">
                <div class="tx-kpi-head">
                    <span class="tx-kpi-title">CITIZEN SIGHTINGS</span>
                    <span style="width: 5px; height: 5px; border-radius: 50%; background: #06B6D4;"></span>
                </div>
                <div class="tx-kpi-value" style="font-size: 24px;">{total_pub}</div>
                <div class="tx-kpi-sub">Public leads registered</div>
            </div>
            """
        )

st.html("<div style='height: 1.25rem;'></div>")

# ── Filters & Search Row ─────────────────────────────────────────────────────
fc1, fc2, fc3 = st.columns([1.5, 3.2, 1.8], gap="medium")

with fc1:
    status_filter = st.selectbox(
        "Filter by Status",
        options=["All", "Not Found", "Found", "Public Cases"],
        on_change=_reset_page,
        args=("page_cases",),
    )

with fc2:
    search_query = st.text_input(
        "Search Cases",
        placeholder="Search by name, location, city, complainant or ID...",
        on_change=_reset_page,
        args=("page_cases",),
    )

with fc3:
    date_filter = st.date_input("Filter by Date (on or after)", value=None)

st.html("<div style='height: 0.75rem;'></div>")

# ── Branch: Public Cases View ─────────────────────────────────────────────────
if status_filter == "Public Cases":
    raw_public_data = list(
        db_queries.fetch_public_cases(False, status_filter, date_filter=date_filter)
    )

    if search_query:
        sq = search_query.lower()
        raw_public_data = [
            c
            for c in raw_public_data
            if sq in str(c[0]).lower()
            or sq in str(c[2]).lower()
            or sq in str(c[3]).lower()
            or sq in str(c[4]).lower()
            or sq in str(c[6]).lower()
        ]

    # Action strip: Count & Export
    ac1, ac2 = st.columns([3, 1])
    with ac1:
        st.html(
            f"""
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #52525B; padding-top: 8px;">
                Showing {len(raw_public_data)} Citizen Sighting Lead(s)
            </div>
            """
        )
    with ac2:
        if raw_public_data:
            df_pub = pd.DataFrame(
                raw_public_data,
                columns=[
                    "ID",
                    "Status",
                    "Location",
                    "Mobile",
                    "Birth Marks",
                    "Submitted On",
                    "Submitted By",
                    "Email",
                ],
            )
            df_pub["Status"] = df_pub["Status"].map({"F": "Found", "NF": "Active"}).fillna(df_pub["Status"])
            st.download_button(
                "Export CSV",
                data=df_pub.to_csv(index=False),
                file_name="tracex_citizen_sightings.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.html("<div style='height: 10px;'></div>")

    if not raw_public_data:
        st.html(
            """
            <div class="tx-empty-card">
                <div style="font-size: 14px; font-weight: 600; color: #FFFFFF;">No Citizen Sightings Found</div>
                <div style="font-size: 12px; color: #71717A; margin-top: 4px;">
                    Public leads submitted via the citizen portal will appear here once verified.
                </div>
            </div>
            """
        )
    else:
        paginated_public, render_public_controls = paginate(raw_public_data, "page_cases")
        for pub_case in paginated_public:
            render_public_case_card(pub_case)
        render_public_controls()

# ── Branch: Registered Missing Person Cases View ──────────────────────────────
else:
    raw_cases_data = list(
        db_queries.fetch_registered_cases(
            user, status_filter, is_admin=is_admin, date_filter=date_filter
        )
    )

    if search_query:
        sq = search_query.lower()
        raw_cases_data = [
            c
            for c in raw_cases_data
            if sq in str(c[0]).lower()
            or sq in str(c[1]).lower()
            or sq in str(c[4]).lower()
            or sq in str(c[6]).lower()
            or sq in str(c[7]).lower()
            or sq in str(c[8]).lower()
            or sq in str(c[9]).lower()
        ]

    # Action strip: Count & Export
    ac1, ac2 = st.columns([3, 1])
    with ac1:
        st.html(
            f"""
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #52525B; padding-top: 8px;">
                Showing {len(raw_cases_data)} Registered Case File(s)
            </div>
            """
        )
    with ac2:
        if raw_cases_data:
            df_reg = pd.DataFrame(
                [
                    {
                        "ID": c[0],
                        "Name": c[1],
                        "Age": c[2],
                        "Status": "Found" if c[3] == "F" else "Not Found",
                        "Last Seen": c[4],
                        "City": c[6],
                        "Marks": c[7],
                        "Complainant": c[8],
                        "Contact": c[9],
                        "Registered On": c[10],
                        "Matched With": c[5],
                    }
                    for c in raw_cases_data
                ]
            )
            st.download_button(
                "Export Records (CSV)",
                data=df_reg.to_csv(index=False),
                file_name="tracex_registered_cases.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.html("<div style='height: 10px;'></div>")

    if not raw_cases_data:
        st.html(
            """
            <div class="tx-empty-card">
                <div style="font-size: 14px; font-weight: 600; color: #FFFFFF;">No Matching Case Records Found</div>
                <div style="font-size: 12px; color: #71717A; margin-top: 4px;">
                    Try clearing search criteria or registering a new case file in the portal.
                </div>
            </div>
            """
        )
    else:
        paginated_cases, render_reg_controls = paginate(raw_cases_data, "page_cases")
        for reg_case in paginated_cases:
            render_registered_case_card(reg_case, is_admin=is_admin)
        render_reg_controls()
