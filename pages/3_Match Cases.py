import os
import streamlit as st
st.set_page_config(
    page_title="TraceX — AI Biometrics",
    page_icon="resources/tracex_icon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

from pages.helper.auth_manager import require_auth
if not require_auth():
    st.switch_page("Home.py")
    st.stop()

from pages.helper.ui_theme import apply_theme, render_sidebar_user_profile
apply_theme()
user_info = st.session_state.get("user_info", {})
role = st.session_state.get("role", "Officer")

if role == "Reporter":
    st.error("Use the sighting portal")
    st.stop()

render_sidebar_user_profile(user_info, role)

from sqlmodel import Session, select
from pages.helper import db_queries, match_algo, emailer
from pages.helper.db_queries import engine
from pages.helper.data_models import RegisteredCases, PublicSubmissions
from pages.helper.matching_config import MATCH_DISTANCE_THRESHOLD


def confidence_from_distance(distance: float) -> tuple:
    similarity = max(0.0, 1.0 - distance)
    confidence = max(0.0, min(100.0, (1.0 - (distance / MATCH_DISTANCE_THRESHOLD)) * 100))
    return confidence, similarity


def is_case_open(case_id: str) -> bool:
    with Session(engine) as session:
        case = session.exec(
            select(RegisteredCases).where(RegisteredCases.id == str(case_id))
        ).first()
        return case is not None and case.status == "NF"


def confirm_match_action(registered_case_id: str, public_case_id: str, case_details: tuple):
    if "confirmed_matches" not in st.session_state:
        st.session_state["confirmed_matches"] = set()
    pair_key = (registered_case_id, public_case_id)
    if pair_key in st.session_state["confirmed_matches"]:
        st.info("This match has already been confirmed in this session.")
        return
    if not is_case_open(registered_case_id):
        st.info("This case has already been resolved or marked as Found.")
        st.session_state["confirmed_matches"].add(pair_key)
        return
    actor_user = st.session_state.get("user", "officer")
    db_queries.update_found_status(registered_case_id, public_case_id, actor_username=actor_user)
    st.session_state["confirmed_matches"].add(pair_key)
    sent = emailer.send_match_notification(registered_case_id, case_details)
    complainant_email = case_details[2] if len(case_details) > 2 else None
    if sent:
        st.session_state[f"msg_{registered_case_id}"] = (
            "success",
            f"Match confirmed. Case marked as Found. Notification sent to {complainant_email}.",
        )
    else:
        st.session_state[f"msg_{registered_case_id}"] = (
            "warning",
            "Match confirmed and case updated. Email notification could not be sent — verify SMTP config.",
        )
    st.rerun()


def reject_candidate_action(registered_case_id: str, public_case_id: str):
    if "rejected_candidates" not in st.session_state:
        st.session_state["rejected_candidates"] = set()
    st.session_state["rejected_candidates"].add((registered_case_id, public_case_id))
    st.rerun()


# ── Page ──────────────────────────────────────────────────────────────────────
user = st.session_state.user
is_admin = st.session_state.get("role", "").lower() == "admin"

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom: 1.75rem;">
    <div style="font-size: 10px; color: #52525B; font-weight: 700; text-transform: uppercase;
                letter-spacing: 0.1em; margin-bottom: 6px;">TRACEX AI BIOMETRICS</div>
    <div style="font-size: 26px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em; line-height: 1.1;">
        Facial Match Intelligence
    </div>
    <div style="font-size: 12px; color: #71717A; margin-top: 6px; line-height: 1.6;">
        Vectorized cosine similarity search — matching unresolved registered cases against public citizen sightings.
    </div>
</div>
""", unsafe_allow_html=True)

if not is_admin:
    st.markdown("""
    <div style="background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25);
                border-radius: 6px; padding: 1rem 1.25rem; font-size: 13px; color: #FCD34D;">
        Restricted: Only Admins can trigger and confirm the matching process.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Stats Row ─────────────────────────────────────────────────────────────────
with Session(engine) as _s:
    total_reg = len(_s.exec(select(RegisteredCases)).all())
    open_cases = len(_s.exec(select(RegisteredCases).where(RegisteredCases.status == "NF")).all())
    closed_cases = len(_s.exec(select(RegisteredCases).where(RegisteredCases.status == "F")).all())
    total_sightings = len(_s.exec(select(PublicSubmissions)).all())

stat1, stat2, stat3, stat4 = st.columns(4)
for col, label, value, color in [
    (stat1, "TOTAL CASES", total_reg, "#71717A"),
    (stat2, "OPEN / ACTIVE", open_cases, "#F59E0B"),
    (stat3, "RESOLVED", closed_cases, "#10B981"),
    (stat4, "SIGHTINGS", total_sightings, "#06B6D4"),
]:
    col.markdown(f"""
    <div class="tx-kpi-card">
        <div class="tx-kpi-head">
            <span class="tx-kpi-title">{label}</span>
            <span style="width:6px;height:6px;border-radius:50%;background:{color};display:inline-block;"></span>
        </div>
        <div class="tx-kpi-value">{value}</div>
        <div class="tx-kpi-sub">Database record count</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

# ── Threshold Config + Run ────────────────────────────────────────────────────
ctrl_col, info_col = st.columns([1, 2])
with ctrl_col:
    st.markdown("""
    <div style="background:#121316;border:1px solid #1E2025;border-radius:6px;
                padding:16px 18px;margin-bottom:1rem;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
                    color:#52525B;margin-bottom:12px;">Match Engine</div>
    """, unsafe_allow_html=True)
    refresh_bt = st.button(
        "Run Biometric Matching",
        type="primary",
        use_container_width=True,
    )
    st.markdown(f"""
        <div style="margin-top:10px;font-size:11px;color:#52525B;line-height:1.6;">
            Threshold: <code style="color:#FAFAFA;background:#18191E;padding:1px 5px;
                                    border-radius:3px;">{MATCH_DISTANCE_THRESHOLD}</code> cosine distance<br>
            Algorithm: InsightFace ArcFace 512-d embeddings
        </div>
    </div>
    """, unsafe_allow_html=True)

with info_col:
    st.markdown("""
    <div style="background:#121316;border:1px solid #1E2025;border-radius:6px;
                padding:16px 18px;margin-bottom:1rem;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
                    color:#52525B;margin-bottom:10px;">How It Works</div>
        <div style="font-size:12px;color:#71717A;line-height:1.7;">
            Each registered case and citizen sighting has a 512-dimensional ArcFace facial embedding.
            The engine computes cosine distance between all open case embeddings and all unresolved sightings.
            Pairs below the distance threshold are surfaced as candidate matches for officer review.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state
if "rejected_candidates" not in st.session_state:
    st.session_state["rejected_candidates"] = set()
if "confirmed_matches" not in st.session_state:
    st.session_state["confirmed_matches"] = set()

if refresh_bt:
    with st.spinner("Running vectorized cosine similarity search across open cases..."):
        matched_ids = match_algo.match()
        st.session_state["match_results"] = matched_ids

matched_ids = st.session_state.get("match_results")

if matched_ids is None:
    # Not yet run — show prompt state
    st.markdown("""
    <div style="background:#0D0E11;border:1px dashed #22242A;border-radius:6px;
                padding:3rem 1.5rem;text-align:center;margin-top:0.5rem;">
        <div style="display:inline-flex;align-items:center;justify-content:center;width:48px;height:48px;
                    border-radius:6px;background:#121316;border:1px solid #1E2025;margin-bottom:14px;">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3F3F46"
                 stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
        </div>
        <div style="font-size:14px;font-weight:600;color:#71717A;">No scan run yet</div>
        <div style="font-size:12px;color:#52525B;margin-top:6px;">
            Click "Run Biometric Matching" to search for facial matches across all open cases.
        </div>
    </div>
    """, unsafe_allow_html=True)

elif matched_ids:
    skipped_reg = matched_ids.get("skipped_registered", 0)
    skipped_pub = matched_ids.get("skipped_public", 0)
    if skipped_reg > 0 or skipped_pub > 0:
        st.markdown(f"""
        <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);
                    border-radius:5px;padding:10px 14px;font-size:12px;color:#FCD34D;margin-bottom:1rem;">
            Skipped {skipped_reg} registered case(s) and {skipped_pub} sighting(s) with outdated feature vectors (not 512-d).
        </div>
        """, unsafe_allow_html=True)

    if not matched_ids.get("status") or not matched_ids.get("result"):
        st.markdown("""
        <div style="background:#121316;border:1px solid #1E2025;border-radius:6px;
                    padding:2rem 1.5rem;text-align:center;margin-top:0.5rem;">
            <div style="font-size:14px;font-weight:600;color:#10B981;margin-bottom:6px;">
                No Matches Found
            </div>
            <div style="font-size:12px;color:#71717A;">
                No open cases match any public sighting within the distance threshold of
                <code style="color:#FAFAFA;background:#18191E;padding:1px 5px;border-radius:3px;">
                {MATCH_DISTANCE_THRESHOLD}</code>.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        matches_dict = matched_ids["result"]
        active_match_count = 0

        st.markdown("""
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
                    color:#52525B;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
            Match Results
            <span style="flex:1;height:1px;background:#1E2025;"></span>
        </div>
        """, unsafe_allow_html=True)

        for reg_id, candidates in matches_dict.items():
            filtered_candidates = [
                (c_id, dist)
                for c_id, dist in candidates
                if (reg_id, c_id) not in st.session_state["rejected_candidates"]
            ]
            top_candidates = filtered_candidates[:3]
            if not top_candidates:
                continue

            active_match_count += 1

            reg_rows = db_queries.get_registered_case_detail(reg_id)
            if not reg_rows:
                continue
            case_details = reg_rows[0]

            # Status feedback
            if f"msg_{reg_id}" in st.session_state:
                m_type, m_text = st.session_state[f"msg_{reg_id}"]
                if m_type == "success":
                    st.markdown(f"""
                    <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);
                                border-radius:5px;padding:10px 14px;font-size:12px;color:#34D399;margin-bottom:8px;">
                        {m_text}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);
                                border-radius:5px;padding:10px 14px;font-size:12px;color:#FCD34D;margin-bottom:8px;">
                        {m_text}
                    </div>
                    """, unsafe_allow_html=True)

            # Case card
            with st.container():
                st.markdown(f"""
                <div style="background:#121316;border:1px solid #1E2025;border-radius:6px;
                            padding:16px 20px;margin-bottom:4px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                        <div>
                            <div style="font-size:14px;font-weight:700;color:#FFFFFF;">
                                {case_details[0]} &mdash; Age {case_details[3]}
                            </div>
                            <div style="font-size:11px;color:#71717A;margin-top:2px;font-family:monospace;">
                                Case #{reg_id[:8]}
                            </div>
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span class="tx-chip">{len(top_candidates)} candidate match{'es' if len(top_candidates)>1 else ''}</span>
                            {'<span class="tx-chip tx-chip-emerald">Resolved</span>' if not is_case_open(reg_id) else '<span class="tx-chip tx-chip-amber">Open</span>'}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                reg_col, cand_col = st.columns([1, 1.8])

                with reg_col:
                    st.markdown("""
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
                                color:#52525B;margin-bottom:8px;">Missing Person</div>
                    """, unsafe_allow_html=True)
                    reg_img_path = f"./resources/{reg_id}.jpg"
                    if os.path.exists(reg_img_path):
                        st.image(reg_img_path, width=160)
                    else:
                        st.markdown("""
                        <div style="width:160px;height:160px;background:#0D0E11;border:1px solid #1E2025;
                                    border-radius:5px;display:flex;align-items:center;justify-content:center;
                                    font-size:11px;color:#52525B;">No image</div>
                        """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="font-size:11px;color:#A1A1AA;margin-top:8px;line-height:1.7;">
                        <div><span style="color:#52525B;">Last Seen:</span> {case_details[4]}</div>
                        <div><span style="color:#52525B;">Contact:</span> {case_details[1]}</div>
                        {'<div><span style="color:#52525B;">Email:</span> '+case_details[2]+'</div>' if case_details[2] else ''}
                        {'<div><span style="color:#52525B;">Marks:</span> '+case_details[5]+'</div>' if case_details[5] else ''}
                    </div>
                    """, unsafe_allow_html=True)
                    if not is_case_open(reg_id):
                        st.markdown("""
                        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);
                                    border-radius:4px;padding:6px 10px;font-size:11px;color:#34D399;margin-top:8px;
                                    font-weight:600;">Case Resolved / Found</div>
                        """, unsafe_allow_html=True)

                with cand_col:
                    st.markdown("""
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
                                color:#52525B;margin-bottom:8px;">Candidate Sightings</div>
                    """, unsafe_allow_html=True)

                    for rank, (cand_id, distance) in enumerate(top_candidates, start=1):
                        conf, sim = confidence_from_distance(distance)
                        cand_rows = db_queries.get_public_case_detail(cand_id)
                        cand_details = cand_rows[0] if cand_rows else ("Unknown", "Anonymous", "N/A", None)
                        is_already_confirmed = (
                            (reg_id, cand_id) in st.session_state["confirmed_matches"]
                            or not is_case_open(reg_id)
                        )

                        conf_color = "#34D399" if conf >= 70 else "#FCD34D" if conf >= 40 else "#FDA4AF"

                        with st.expander(
                            f"#{rank} — {cand_details[0]} ({conf:.0f}% conf · {sim*100:.1f}% sim)",
                            expanded=True,
                        ):
                            c_img_col, c_info_col = st.columns([1, 2])
                            with c_img_col:
                                cand_img_path = f"./resources/{cand_id}.jpg"
                                if os.path.exists(cand_img_path):
                                    st.image(cand_img_path, width=120)
                                else:
                                    st.markdown("""
                                    <div style="width:120px;height:120px;background:#0D0E11;border:1px solid #1E2025;
                                                border-radius:5px;display:flex;align-items:center;
                                                justify-content:center;font-size:10px;color:#52525B;">No image</div>
                                    """, unsafe_allow_html=True)
                            with c_info_col:
                                st.markdown(f"""
                                <div style="font-size:12px;color:#A1A1AA;line-height:1.8;">
                                    <div><span style="color:#52525B;">Location:</span> {cand_details[0]}</div>
                                    <div><span style="color:#52525B;">Reported by:</span> {cand_details[1]} ({cand_details[2]})</div>
                                    {"<div><span style='color:#52525B;'>Features:</span> "+cand_details[3]+"</div>" if cand_details[3] else ""}
                                </div>
                                <div style="margin-top:10px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                                    <span style="font-size:11px;color:#52525B;">Distance:
                                        <code style="color:#FAFAFA;background:#18191E;padding:1px 5px;
                                                     border-radius:3px;">{distance:.4f}</code>
                                    </span>
                                    <span style="font-size:11px;color:{conf_color};font-weight:700;">
                                        {conf:.0f}% confidence
                                    </span>
                                </div>
                                """, unsafe_allow_html=True)
                                st.progress(conf / 100)
                                if not is_already_confirmed:
                                    btn_col1, btn_col2 = st.columns(2)
                                    if btn_col1.button(
                                        "Confirm Match",
                                        key=f"confirm_{reg_id}_{cand_id}",
                                        type="primary",
                                    ):
                                        confirm_match_action(reg_id, cand_id, case_details)
                                    if btn_col2.button(
                                        "Reject",
                                        key=f"reject_{reg_id}_{cand_id}",
                                    ):
                                        reject_candidate_action(reg_id, cand_id)
                                else:
                                    st.markdown("""
                                    <div style="font-size:11px;color:#34D399;padding:6px 0;">
                                        Match resolved for this case.
                                    </div>
                                    """, unsafe_allow_html=True)

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if active_match_count == 0:
            st.markdown("""
            <div style="background:#121316;border:1px solid #1E2025;border-radius:6px;
                        padding:2rem 1.5rem;text-align:center;">
                <div style="font-size:13px;font-weight:600;color:#71717A;">
                    All matches reviewed or rejected in this session.
                </div>
            </div>
            """, unsafe_allow_html=True)
