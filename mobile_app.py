import os
import uuid
import json
import tempfile
import base64
import importlib

import numpy as np
import streamlit as st

from pages.helper import db_queries, utils
importlib.reload(utils)
from pages.helper.data_models import PublicSubmissions
from pages.helper.utils import (
    image_obj_to_numpy,
    detect_all_faces,
    draw_face_boxes,
    extract_face_embedding,
    extract_unique_faces_from_video,
    validate_image_upload,
    validate_video_upload,
    save_display_image,
    MAX_IMAGE_UPLOAD_MB,
    MAX_VIDEO_UPLOAD_MB,
)
from pages.helper.auth_manager import is_authenticated, login_user, logout_user
from pages.helper.ui_theme import apply_login_theme

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TraceX — Citizen Sighting Portal",
    page_icon="resources/tracex_icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Precision Minimal Styling & Total Sidebar Suppression ─────────────────────
st.markdown(
    """
    <style>
    /* Completely hide Streamlit sidebar navigation and toggle controls for public citizens */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    button[data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Core Canvas Tokens */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        background-color: #090A0C !important;
        color: #E4E4E7 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif !important;
    }

    /* Transparent header, hidden footer */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    footer {
        visibility: hidden !important;
    }

    /* Page container spacing */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1050px !important;
    }

    /* Precision Card Container (6px radius) */
    .tx-card {
        background: #121316 !important;
        border: 1px solid #1E2025 !important;
        border-radius: 6px !important;
        padding: 20px 24px !important;
        margin-bottom: 1.25rem !important;
    }

    /* Micro Badges (4px radius) */
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
    }
    .tx-chip-emerald {
        background: rgba(16, 185, 129, 0.08);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }

    /* Form inputs (5px radius) */
    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="base-input"],
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        border-radius: 5px !important;
        background: #0E0F12 !important;
        border: 1px solid #22242A !important;
        color: #FAFAFA !important;
        padding: 9px 12px !important;
        font-size: 13px !important;
    }
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stTextArea"] textarea:focus,
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="textarea"]:focus-within {
        border-color: #52525B !important;
        box-shadow: 0 0 0 1px #52525B !important;
    }

    /* Completely Suppress "Press Enter to submit form" Everywhere */
    [data-testid="InputInstructions"],
    div[data-testid="InputInstructions"],
    span[data-testid="InputInstructions"],
    .stChatInputInstructions,
    div:has(> [data-testid="InputInstructions"]) > [data-testid="InputInstructions"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        max-height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 0 !important;
        font-size: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
        overflow: hidden !important;
    }

    /* Sleek form button (5px radius, monochrome) */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button[type="submit"],
    div.stButton > button {
        background: #FAFAFA !important;
        color: #090A0C !important;
        border-radius: 5px !important;
        width: 100% !important;
        padding: 10px 16px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        border: 1px solid #FAFAFA !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
    div[data-testid="stForm"] button[type="submit"]:hover,
    div.stButton > button:hover {
        background: #E4E4E7 !important;
        border-color: #E4E4E7 !important;
    }

    /* Style file uploader dropzone */
    div[data-testid="stFileUploader"] section {
        background: #0E0F12 !important;
        border: 1px dashed #27272A !important;
        border-radius: 6px !important;
        padding: 1.5rem !important;
    }
    div[data-testid="stFileUploader"] section:hover {
        border-color: #52525B !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Authentication Gate (Reporter & Admin Only) ──────────────────────────────
if not is_authenticated():
    apply_login_theme()

    try:
        with open("resources/tracex_logo.png", "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 38px; width: auto; margin-bottom: 0.6rem;" />'
    except Exception:
        logo_html = '<div style="font-size: 24px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;">TraceX</div>'

    with st.form("tracex_reporter_auth_form", clear_on_submit=False):
        st.markdown(
            f'''
            <div style="text-align: center; margin-bottom: 1.75rem;">
                {logo_html}
                <div style="font-size: 14px; font-weight: 600; color: #FAFAFA; margin-bottom: 2px;">
                    Citizen Sighting Portal
                </div>
                <div style="font-size: 12px; color: #71717A;">
                    Sign in with your Reporter credentials to submit sightings
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        username_input = st.text_input("Username", placeholder="Enter your username")
        password_input = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In to Portal", use_container_width=True)

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

# ── Role Authorization Check ──────────────────────────────────────────────────
user_info = st.session_state.get("user_info", {})
role = st.session_state.get("role", "")
if role not in ("Reporter", "Admin"):
    st.error("Access denied. Only Reporters and Administrators can access the Sighting Portal. Officers should use the Officer Portal.")
    if st.button("Sign Out", key="portal_denied_signout"):
        logout_user()
    st.stop()

reporter_username = st.session_state.get("username", "reporter")
reporter_name = user_info.get("name", st.session_state.get("name", reporter_username))
reporter_city = user_info.get("city", "")
reporter_area = user_info.get("area", "")
reporter_email = user_info.get("email", "")
locality_parts = [p for p in (reporter_city, reporter_area) if p]
locality_str = ", ".join(locality_parts) if locality_parts else "Not Specified"
daily_submissions = db_queries.get_daily_submissions_count(reporter_username)

# ── Header Bar ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 22px 26px; margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background: #18191E; border: 1px solid #27272A; width: 36px; height: 36px; border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; color: #FFFFFF;">
                    TX
                </div>
                <div>
                    <div style="font-size: 16px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.01em;">TraceX Citizen Sighting Portal</div>
                    <div style="font-size: 11px; color: #71717A;">Direct Citizen-to-Officer Lead Dispatch</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="tx-chip tx-chip-emerald">
                    <span style="width: 5px; height: 5px; border-radius: 50%; background: #10B981; display: inline-block;"></span> Active Dispatch Network
                </span>
                <span class="tx-chip">
                    Confidential Submission
                </span>
            </div>
        </div>
        <div style="margin-top: 12px; font-size: 12px; color: #A1A1AA; line-height: 1.5; border-top: 1px solid #18191E; padding-top: 10px;">
            Have you spotted someone who matches a missing person? Upload a photo or video to alert investigating officers immediately. Your contact details remain confidential.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Reporter Profile & Logout Bar ─────────────────────────────────────────────
profile_col1, profile_col2 = st.columns([4.2, 1.2])
with profile_col1:
    st.markdown(
        f"""
        <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 10px 16px; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <div style="font-size: 13px; font-weight: 600; color: #FAFAFA; display: flex; align-items: center; gap: 8px;">
                    <span>Reporter: <strong>{reporter_name}</strong></span>
                    <span class="tx-chip tx-chip-emerald">{role}</span>
                </div>
                <span style="color: #3F3F46;">|</span>
                <div style="font-size: 12px; color: #71717A;">
                    Locality: <span style="color: #D4D4D8; font-weight: 500;">{locality_str}</span>
                </div>
                <span style="color: #3F3F46;">|</span>
                <div style="font-size: 12px; color: #71717A;">
                    Daily Submissions: <span style="color: #34D399; font-weight: 600;">{daily_submissions} / {db_queries.DAILY_REPORTER_SUBMISSION_CAP}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with profile_col2:
    if st.button("Sign Out", key="reporter_signout_btn", use_container_width=True):
        logout_user()

# ── Upload Type Selector ──────────────────────────────────────────────────────
upload_col, _ = st.columns([1, 2])
with upload_col:
    upload_mode = st.radio(
        "Upload Media Type",
        options=["Single Photo", "Video Clip"],
        horizontal=True,
    )

media_col, form_col = st.columns([1.1, 1.2], gap="large")
save_flag = 0
extracted_faces = []
selected_face_idx = None
unique_id = None
faces = []

# ── Photo Upload Workflow ─────────────────────────────────────────────────────
if upload_mode == "Single Photo":
    with media_col:
        st.markdown(
            """
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #71717A; margin-bottom: 0.5rem;">
                Step 1: Upload Photograph
            </div>
            """,
            unsafe_allow_html=True,
        )
        image_obj = st.file_uploader(
            "Upload sighting photograph",
            type=["jpg", "jpeg", "png"],
            key="user_submission_img",
            help=f"Supported formats: JPG, JPEG, PNG. Max {MAX_IMAGE_UPLOAD_MB} MB. Good lighting and clear front-facing angle works best.",
        )

        if image_obj:
            file_key = f"{image_obj.name}_{image_obj.size}"
            if st.session_state.get("pub_file_key") != file_key:
                val_res = validate_image_upload(image_obj, max_mb=MAX_IMAGE_UPLOAD_MB)
                if isinstance(val_res, str):
                    st.session_state["pub_file_key"] = file_key
                    st.session_state["pub_val_error"] = val_res
                    st.session_state["pub_faces"] = []
                    st.session_state["pub_image_numpy"] = None
                    st.session_state["pub_unique_id"] = None
                else:
                    image_numpy = np.array(val_res)
                    unique_id = str(uuid.uuid4())
                    with st.spinner("AI analyzing facial features..."):
                        detected_faces = detect_all_faces(image_numpy, max_faces=5)

                    st.session_state["pub_file_key"] = file_key
                    st.session_state["pub_val_error"] = None
                    st.session_state["pub_faces"] = detected_faces
                    st.session_state["pub_image_numpy"] = image_numpy
                    st.session_state["pub_unique_id"] = unique_id

            val_error = st.session_state.get("pub_val_error")
            if val_error:
                st.error(val_error)
                selected_face_idx = None
                unique_id = None
                faces = []
            else:
                faces = st.session_state.get("pub_faces", [])
                image_numpy = st.session_state.get("pub_image_numpy")
                unique_id = st.session_state.get("pub_unique_id")

                if not faces:
                    st.error(
                        "**No face detected.**\n\n"
                        "Please ensure the individual's face is clearly visible, well-lit, and not obstructed."
                    )
                    selected_face_idx = None
                elif len(faces) == 1:
                    annotated = draw_face_boxes(image_numpy, faces, selected_idx=0)
                    st.image(annotated, use_container_width=True)
                    st.success("**1 face detected and verified.** Ready to submit.")
                    selected_face_idx = 0
                else:
                    st.warning(
                        f"**{len(faces)} faces detected.** Please select the person to report:"
                    )
                    options = [f"Face {i + 1}" for i in range(len(faces))]
                    choice = st.radio(
                        "Select target face", options, horizontal=True, key="pub_face_choice"
                    )
                    selected_face_idx = options.index(choice)
                    annotated = draw_face_boxes(
                        image_numpy, faces, selected_idx=selected_face_idx
                    )
                    st.image(annotated, use_container_width=True)
                    st.info(f"Target selected: **Face {selected_face_idx + 1}**")
        else:
            for k in [
                "pub_file_key",
                "pub_val_error",
                "pub_faces",
                "pub_image_numpy",
                "pub_unique_id",
                "pub_face_choice",
            ]:
                st.session_state.pop(k, None)
            selected_face_idx = None
            unique_id = None
            faces = []

    face_ready = image_obj and faces and selected_face_idx is not None

    with form_col:
        st.markdown(
            """
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #71717A; margin-bottom: 0.5rem;">
                Step 2: Sighting Details
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not face_ready:
            st.markdown(
                """
                <div style="background: #121316; border: 1px dashed #27272A; border-radius: 6px; padding: 2.5rem 1.5rem; text-align: center; color: #71717A;">
                    <div style="font-size: 14px; font-weight: 600; color: #E4E4E7; margin-bottom: 4px;">Upload Media First</div>
                    <div style="font-size: 12px;">The sighting report form will activate as soon as a face is detected and verified.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            with st.form(key="image_submission_form"):
                sub_name = st.text_input("Your Full Name *", value=reporter_name, placeholder="e.g. Rahul Verma")
                mobile_number = st.text_input(
                    "Your Mobile Number * (10 digits)", placeholder="e.g. 9876543210"
                )
                email = st.text_input("Your Email (Optional)", value=reporter_email, placeholder="e.g. rahul@example.com")
                address = st.text_input(
                    "Where was this person spotted? *",
                    placeholder="e.g. Near Metro Station Gate 2, Rajiv Chowk, New Delhi",
                )
                sighting_city = st.text_input(
                    "City of Sighting *",
                    placeholder="e.g. New Delhi, Mumbai, Jamshedpur",
                )
                birth_marks = st.text_input(
                    "Identifying marks or clothing noted",
                    placeholder="e.g. Blue denim jacket, mole on left cheek, scar on forehead",
                )

                submit_bt = st.form_submit_button("Submit Sighting Report")

                if submit_bt:
                    errors = []
                    if not sub_name.strip():
                        errors.append("Your Name is required.")
                    if not mobile_number.strip():
                        errors.append("Mobile Number is required.")
                    elif (
                        not mobile_number.strip().isdigit()
                        or len(mobile_number.strip()) != 10
                    ):
                        errors.append("Mobile Number must be exactly 10 digits.")
                    if not address.strip():
                        errors.append("Sighting location is required.")
                    if not sighting_city.strip():
                        errors.append("City of sighting is required.")

                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        current_count = db_queries.get_daily_submissions_count(reporter_username)
                        if current_count >= db_queries.DAILY_REPORTER_SUBMISSION_CAP:
                            st.error(
                                f"Daily submission limit reached ({db_queries.DAILY_REPORTER_SUBMISSION_CAP} reports/day). "
                                "You cannot submit any more sightings today. Please try again tomorrow."
                            )
                        else:
                            selected_bbox = faces[selected_face_idx]["bbox"]
                            with st.spinner("Extracting facial signature..."):
                                embedding = extract_face_embedding(image_numpy, selected_bbox)

                            if embedding is None:
                                st.error(
                                    "Could not extract high-confidence facial features for the selected face. "
                                    "Please upload a clearer, front-facing photograph."
                                )
                            else:
                                # Order: validate -> detect face -> compute embedding from original -> save_display_image -> insert DB
                                os.makedirs("./resources", exist_ok=True)
                                dest_path = f"./resources/{unique_id}.jpg"
                                try:
                                    save_display_image(image_numpy, dest_path, max_side=1600, quality=90)
                                except Exception as e:
                                    if os.path.exists(dest_path):
                                        try:
                                            os.remove(dest_path)
                                        except OSError:
                                            pass
                                    st.error(f"Failed to save image: {e}")
                                    st.stop()

                                details = PublicSubmissions(
                                    submitted_by=reporter_username,
                                    location=f"{address.strip()} [{sighting_city.strip()}]",
                                    email=email.strip() or None,
                                    face_mesh=json.dumps(embedding),
                                    id=unique_id,
                                    mobile=mobile_number.strip(),
                                    birth_marks=birth_marks.strip() or None,
                                    status="NF",
                                )
                                try:
                                    db_queries.new_public_case(details)
                                    db_queries.record_audit_log(
                                        reporter_username=reporter_username,
                                        sighting_id=unique_id,
                                        action="SUBMIT",
                                        city=reporter_city,
                                        area=reporter_area,
                                    )
                                    save_flag = 1
                                except Exception as e:
                                    if os.path.exists(dest_path):
                                        try:
                                            os.remove(dest_path)
                                        except OSError:
                                            pass
                                    st.error(f"Database submission failed: {e}")

            if save_flag == 1:
                st.markdown(
                    f"""
                    <div style="background: #121316; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 1.25rem; margin-top: 1rem;">
                        <div style="font-size: 13px; font-weight: 700; color: #34D399; margin-bottom: 2px;">
                            Sighting Report Dispatched!
                        </div>
                        <div style="font-size: 12px; color: #A1A1AA; line-height: 1.4;">
                            Thank you for your report. Your lead has been encrypted and immediately routed to investigative officers.
                        </div>
                        <div style="margin-top: 6px; font-size: 11px; color: #71717A; font-family: ui-monospace, monospace;">
                            Reference ID: <code style="color: #FAFAFA;">{unique_id}</code>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ── Video Upload Workflow ─────────────────────────────────────────────────────
else:
    with media_col:
        st.markdown(
            """
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #71717A; margin-bottom: 0.5rem;">
                Step 1: Upload Video Clip
            </div>
            """,
            unsafe_allow_html=True,
        )
        video_obj = st.file_uploader(
            "Upload sighting video clip",
            type=["mp4", "mov", "avi"],
            key="user_submission_video",
            help=f"Supported formats: MP4, MOV, AVI. Max {MAX_VIDEO_UPLOAD_MB} MB. Clips with clear front-facing glimpses work best.",
        )

        if video_obj:
            video_file_key = f"{video_obj.name}_{video_obj.size}"
            if st.session_state.get("pub_video_file_key") != video_file_key:
                val_err = validate_video_upload(video_obj, max_mb=MAX_VIDEO_UPLOAD_MB)
                if val_err:
                    st.session_state["pub_video_file_key"] = video_file_key
                    st.session_state["pub_video_error"] = val_err
                    st.session_state["pub_video_faces"] = []
                else:
                    with st.spinner("Analyzing video frames and extracting unique faces..."):
                        suffix = "." + video_obj.name.rsplit(".", 1)[-1]
                        tmp_path = None
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(video_obj.read())
                                tmp_path = tmp.name

                            extracted_faces = extract_unique_faces_from_video(tmp_path)
                        finally:
                            if tmp_path and os.path.exists(tmp_path):
                                try:
                                    os.unlink(tmp_path)
                                except OSError:
                                    pass

                        st.session_state["pub_video_file_key"] = video_file_key
                        st.session_state["pub_video_error"] = None
                        st.session_state["pub_video_faces"] = extracted_faces

            video_err = st.session_state.get("pub_video_error")
            if video_err:
                st.error(video_err)
                extracted_faces = []
            else:
                extracted_faces = st.session_state.get("pub_video_faces", [])
                if not extracted_faces:
                    st.error(
                        "**No faces detected in the video.**\n\n"
                        "Please ensure the video shows a clear front-facing glimpse of the individual in good lighting."
                    )
                else:
                    st.success(f"Found **{len(extracted_faces)}** unique face(s) in video.")
                    thumb_cols = st.columns(min(len(extracted_faces), 4))
                    for idx, (_, frame_rgb) in enumerate(extracted_faces):
                        thumb_cols[idx % 4].image(frame_rgb, width=100)
        else:
            for k in ["pub_video_file_key", "pub_video_error", "pub_video_faces"]:
                st.session_state.pop(k, None)
            extracted_faces = []

    with form_col:
        st.markdown(
            """
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #71717A; margin-bottom: 0.5rem;">
                Step 2: Sighting Details
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not extracted_faces:
            st.markdown(
                """
                <div style="background: #121316; border: 1px dashed #27272A; border-radius: 6px; padding: 2.5rem 1.5rem; text-align: center; color: #71717A;">
                    <div style="font-size: 14px; font-weight: 600; color: #E4E4E7; margin-bottom: 4px;">Upload Media First</div>
                    <div style="font-size: 12px;">The sighting report form will activate as soon as unique faces are detected in the clip.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            with st.form(key="video_submission_form"):
                sub_name = st.text_input("Your Full Name *", value=reporter_name, placeholder="e.g. Priya Sharma")
                mobile_number = st.text_input(
                    "Your Mobile Number * (10 digits)", placeholder="e.g. 9876543210"
                )
                email = st.text_input("Your Email (Optional)", value=reporter_email, placeholder="e.g. priya@example.com")
                address = st.text_input(
                    "Where was this video recorded? *",
                    placeholder="e.g. Bus Terminal Platform 4, Anand Vihar, Delhi",
                )
                sighting_city = st.text_input(
                    "City of Sighting *",
                    placeholder="e.g. New Delhi, Mumbai, Jamshedpur",
                )
                birth_marks = st.text_input(
                    "Identifying marks or clothing noted",
                    placeholder="e.g. Black backpack, red cap, limping walk",
                )

                submit_bt = st.form_submit_button(
                    f"Submit {len(extracted_faces)} Sighting(s)"
                )

                if submit_bt:
                    errors = []
                    if not sub_name.strip():
                        errors.append("Your Name is required.")
                    if not mobile_number.strip():
                        errors.append("Mobile Number is required.")
                    elif (
                        not mobile_number.strip().isdigit()
                        or len(mobile_number.strip()) != 10
                    ):
                        errors.append("Mobile Number must be exactly 10 digits.")
                    if not address.strip():
                        errors.append("Location is required.")
                    if not sighting_city.strip():
                        errors.append("City of sighting is required.")

                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        current_count = db_queries.get_daily_submissions_count(reporter_username)
                        remaining = max(0, db_queries.DAILY_REPORTER_SUBMISSION_CAP - current_count)
                        if current_count >= db_queries.DAILY_REPORTER_SUBMISSION_CAP:
                            st.error(
                                f"Daily submission limit reached ({db_queries.DAILY_REPORTER_SUBMISSION_CAP} reports/day). "
                                "You cannot submit any more sightings today. Please try again tomorrow."
                            )
                        elif len(extracted_faces) > remaining:
                            st.error(
                                f"Daily submission limit exceeded. You have {remaining} report(s) remaining today, "
                                f"but this clip contains {len(extracted_faces)} unique face(s)."
                            )
                        else:
                            count = 0
                            os.makedirs("./resources", exist_ok=True)
                            created_files = []
                            all_saved_successfully = True

                            for embedding, frame_rgb in extracted_faces:
                                sub_id = str(uuid.uuid4())
                                dest_path = f"./resources/{sub_id}.jpg"
                                try:
                                    # Keep thumbnails at original frame size (max_side=None) at quality 90 (no further shrinking)
                                    save_display_image(
                                        frame_rgb,
                                        dest_path,
                                        max_side=None,
                                        quality=90,
                                    )
                                    created_files.append((sub_id, dest_path, embedding))
                                except Exception as e:
                                    all_saved_successfully = False
                                    st.error(f"Failed to save video thumbnail: {e}")
                                    break

                            if not all_saved_successfully:
                                # Clean up any created files to prevent orphans
                                for _, path, _ in created_files:
                                    if os.path.exists(path):
                                        try:
                                            os.remove(path)
                                        except OSError:
                                            pass
                            else:
                                inserted_files = []
                                try:
                                    for sub_id, dest_path, embedding in created_files:
                                        details = PublicSubmissions(
                                            submitted_by=reporter_username,
                                            location=f"{address.strip()} [{sighting_city.strip()}]",
                                            email=email.strip() or None,
                                            face_mesh=json.dumps(embedding),
                                            id=sub_id,
                                            mobile=mobile_number.strip(),
                                            birth_marks=birth_marks.strip() or None,
                                            status="NF",
                                        )
                                        db_queries.new_public_case(details)
                                        db_queries.record_audit_log(
                                            reporter_username=reporter_username,
                                            sighting_id=sub_id,
                                            action="SUBMIT",
                                            city=reporter_city,
                                            area=reporter_area,
                                        )
                                        inserted_files.append(dest_path)
                                        count += 1
                                    save_flag = count
                                except Exception as e:
                                    st.error(f"Database submission failed: {e}")
                                    for _, path, _ in created_files:
                                        if path not in inserted_files and os.path.exists(path):
                                            try:
                                                os.remove(path)
                                            except OSError:
                                                pass

            if save_flag > 0:
                st.markdown(
                    f"""
                    <div style="background: #121316; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 1.25rem; margin-top: 1rem;">
                        <div style="font-size: 13px; font-weight: 700; color: #34D399; margin-bottom: 2px;">
                            {save_flag} Sighting Report(s) Dispatched!
                        </div>
                        <div style="font-size: 12px; color: #A1A1AA; line-height: 1.4;">
                            Thank you for your report. The extracted face profiles have been encrypted and submitted to the investigative team.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
