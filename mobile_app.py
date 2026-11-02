import os
import uuid
import json
import tempfile
import importlib

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
)

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

# ── Header Bar ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="background: #121316; border: 1px solid #1E2025; border-radius: 6px; padding: 22px 26px; margin-bottom: 1.5rem;">
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
            help="Supported formats: JPG, JPEG, PNG. Good lighting and clear front-facing angle works best.",
        )

        if image_obj:
            file_key = f"{image_obj.name}_{image_obj.size}"
            if st.session_state.get("pub_file_key") != file_key:
                unique_id = str(uuid.uuid4())
                os.makedirs("./resources", exist_ok=True)
                uploaded_file_path = f"./resources/{unique_id}.jpg"

                with open(uploaded_file_path, "wb") as f:
                    f.write(image_obj.read())
                image_obj.seek(0)

                with st.spinner("AI analyzing facial features..."):
                    image_numpy = image_obj_to_numpy(image_obj)
                    detected_faces = detect_all_faces(image_numpy, max_faces=5)

                if not detected_faces:
                    if os.path.exists(uploaded_file_path):
                        os.remove(uploaded_file_path)
                    st.session_state["pub_file_key"] = file_key
                    st.session_state["pub_faces"] = []
                    st.session_state["pub_image_numpy"] = None
                    st.session_state["pub_unique_id"] = None
                    st.session_state["pub_uploaded_path"] = None
                else:
                    st.session_state["pub_file_key"] = file_key
                    st.session_state["pub_faces"] = detected_faces
                    st.session_state["pub_image_numpy"] = image_numpy
                    st.session_state["pub_unique_id"] = unique_id
                    st.session_state["pub_uploaded_path"] = uploaded_file_path

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
                "pub_faces",
                "pub_image_numpy",
                "pub_unique_id",
                "pub_uploaded_path",
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
                sub_name = st.text_input("Your Full Name *", placeholder="e.g. Rahul Verma")
                mobile_number = st.text_input(
                    "Your Mobile Number * (10 digits)", placeholder="e.g. 9876543210"
                )
                email = st.text_input("Your Email (Optional)", placeholder="e.g. rahul@example.com")
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
                        selected_bbox = faces[selected_face_idx]["bbox"]
                        with st.spinner("Extracting facial signature..."):
                            embedding = extract_face_embedding(image_numpy, selected_bbox)

                        if embedding is None:
                            st.error(
                                "Could not extract high-confidence facial features for the selected face. "
                                "Please upload a clearer, front-facing photograph."
                            )
                        else:
                            details = PublicSubmissions(
                                submitted_by=sub_name.strip(),
                                location=f"{address.strip()} [{sighting_city.strip()}]",
                                email=email.strip() or None,
                                face_mesh=json.dumps(embedding),
                                id=unique_id,
                                mobile=mobile_number.strip(),
                                birth_marks=birth_marks.strip() or None,
                                status="NF",
                            )
                            db_queries.new_public_case(details)
                            save_flag = 1

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
            help="Supported formats: MP4, MOV, AVI. Clips with clear front-facing glimpses work best.",
        )

        if video_obj:
            with st.spinner("Analyzing video frames and extracting unique faces..."):
                suffix = "." + video_obj.name.rsplit(".", 1)[-1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(video_obj.read())
                    tmp_path = tmp.name

                extracted_faces = extract_unique_faces_from_video(tmp_path)
                os.unlink(tmp_path)

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
                sub_name = st.text_input("Your Full Name *", placeholder="e.g. Priya Sharma")
                mobile_number = st.text_input(
                    "Your Mobile Number * (10 digits)", placeholder="e.g. 9876543210"
                )
                email = st.text_input("Your Email (Optional)", placeholder="e.g. priya@example.com")
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
                        count = 0
                        os.makedirs("./resources", exist_ok=True)
                        for embedding, frame_rgb in extracted_faces:
                            sub_id = str(uuid.uuid4())
                            try:
                                import PIL.Image
                                PIL.Image.fromarray(frame_rgb).save(f"./resources/{sub_id}.jpg")
                            except Exception:
                                pass
                            details = PublicSubmissions(
                                submitted_by=sub_name.strip(),
                                location=f"{address.strip()} [{sighting_city.strip()}]",
                                email=email.strip() or None,
                                face_mesh=json.dumps(embedding),
                                id=sub_id,
                                mobile=mobile_number.strip(),
                                birth_marks=birth_marks.strip() or None,
                                status="NF",
                            )
                            db_queries.new_public_case(details)
                            count += 1
                        save_flag = count

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
