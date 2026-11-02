from pages.helper.ui_theme import apply_theme, render_sidebar_user_profile
from pages.helper.auth_manager import require_auth
import os
import uuid
import json

import streamlit as st

from pages.helper.data_models import RegisteredCases
from pages.helper import db_queries, utils
from pages.helper.utils import (
    image_obj_to_numpy,
    detect_all_faces,
    draw_face_boxes,
    extract_face_embedding,
)

st.set_page_config(
    page_title="TraceX — Register New Case",
    page_icon="resources/tracex_icon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not require_auth():
    st.switch_page("Home.py")

apply_theme()

user_info = st.session_state.get("user_info", {})
role = st.session_state.get("role", "Officer")
render_sidebar_user_profile(user_info, role)

user = st.session_state.get("user", "officer")

# ── Extra page-specific styles ─────────────────────────────────────────────
st.html("""
<style>
.tx-section-card {
    background: #121316;
    border: 1px solid #1E2025;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 1rem;
}
.tx-section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #52525B;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.tx-section-label::after {
    content: "";
    flex: 1;
    height: 1px;
    background: #1E2025;
}
.tx-upload-zone {
    background: #0D0E11;
    border: 1px dashed #2A2D35;
    border-radius: 6px;
    padding: 1.5rem;
    text-align: center;
    transition: border-color 0.15s ease;
}
.tx-upload-zone:hover {
    border-color: #3F3F46;
}
.tx-face-status-ok {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 5px;
    padding: 10px 14px;
    font-size: 12px;
    color: #34D399;
    font-weight: 600;
    margin-top: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.tx-face-status-err {
    background: rgba(244, 63, 94, 0.08);
    border: 1px solid rgba(244, 63, 94, 0.25);
    border-radius: 5px;
    padding: 10px 14px;
    font-size: 12px;
    color: #FDA4AF;
    font-weight: 600;
    margin-top: 10px;
}
</style>
""")

# ── Page Header ────────────────────────────────────────────────────────────
st.html("""
<div style="margin-bottom: 1.75rem;">
    <div style="font-size: 10px; color: #52525B; font-weight: 700; text-transform: uppercase;
                letter-spacing: 0.1em; margin-bottom: 6px;">TRACEX INVESTIGATION MODULE</div>
    <div style="font-size: 26px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;
                line-height: 1.1;">Register New Missing Person Case</div>
    <div style="font-size: 12px; color: #71717A; margin-top: 6px; max-width: 540px; line-height: 1.6;">
        Extract 512-dimensional ArcFace facial signatures and index case records into the central search database.
    </div>
</div>
""")

# ── Success & Next Action State (Shown after a case is registered) ────────────
if st.session_state.get("registered_case_id"):
    succ_id = st.session_state.get("registered_case_id")
    succ_name = st.session_state.get("registered_case_name", "Missing Person")
    
    st.html(f"""
    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 6px; padding: 1.5rem 1.75rem; margin-bottom: 1.5rem;">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
            <div style="display:inline-flex;align-items:center;justify-content:center;width:32px;
                        height:32px;border-radius:4px;background:rgba(16,185,129,0.15);
                        border:1px solid rgba(16,185,129,0.3);">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#34D399"
                     stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </div>
            <div>
                <div style="font-size: 16px; font-weight: 700; color: #34D399;">
                    Case File #{succ_id[:8].upper()} Successfully Created &amp; Indexed
                </div>
                <div style="font-size: 12px; color: #A1A1AA; margin-top: 2px;">
                    Biometric profile for <b>{succ_name}</b> is active in the 512-dimensional vector database.
                </div>
            </div>
        </div>
        <div style="font-size: 12px; color: #71717A; line-height: 1.6; margin-bottom: 12px;">
            The vector database will automatically match public citizen sightings against this profile whenever cosine distance &le; 0.48.
        </div>
        <div style="font-size: 11px; color: #71717A; font-family: monospace;">
            Case Reference UUID: <code style="color: #FAFAFA; background: #18191E; padding: 3px 8px; border-radius: 4px;">{succ_id}</code>
        </div>
    </div>
    """)

    btn_col1, btn_col2, _ = st.columns([1.2, 1.2, 2])
    with btn_col1:
        if st.button("＋ Register Another Case", key="btn_register_another", type="primary", use_container_width=True):
            st.session_state["nc_uploader_idx"] = st.session_state.get("nc_uploader_idx", 0) + 1
            for k in [
                "nc_file_key", "nc_faces", "nc_image_numpy", "nc_unique_id",
                "nc_uploaded_path", "nc_face_choice", "registered_case_id",
                "registered_case_name"
            ]:
                st.session_state.pop(k, None)
            st.rerun()

    with btn_col2:
        if st.button("View in All Cases →", key="btn_view_all_cases", use_container_width=True):
            st.session_state["nc_uploader_idx"] = st.session_state.get("nc_uploader_idx", 0) + 1
            for k in [
                "nc_file_key", "nc_faces", "nc_image_numpy", "nc_unique_id",
                "nc_uploaded_path", "nc_face_choice", "registered_case_id",
                "registered_case_name"
            ]:
                st.session_state.pop(k, None)
            st.switch_page("pages/2_All Cases.py")

    st.stop()


# ── Active Registration Workflow ──────────────────────────────────────────────
image_col, form_col = st.columns([1, 1.4], gap="large")

# ── LEFT: Photo Upload & Face Detection ───────────────────────────────────
with image_col:
    st.html("""
    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
                color: #52525B; margin-bottom: 12px; display:flex; align-items:center; gap:8px;">
        <span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;
                     border-radius:3px;background:#1E2025;border:1px solid #27272A;font-size:9px;
                     font-weight:800;color:#A1A1AA;">1</span>
        Reference Photograph
        <span style="flex:1;height:1px;background:#1E2025;"></span>
    </div>
    """)

    uploader_idx = st.session_state.get("nc_uploader_idx", 0)
    image_obj = st.file_uploader(
        "Upload photo",
        type=["jpg", "jpeg", "png"],
        key=f"new_case_upload_{uploader_idx}",
        help="High-resolution, front-facing photograph recommended. Max 200 MB.",
        label_visibility="collapsed",
    )

    if image_obj:
        file_key = f"{image_obj.name}_{image_obj.size}"

        if st.session_state.get("nc_file_key") != file_key:
            unique_id = str(uuid.uuid4())
            os.makedirs("./resources", exist_ok=True)
            uploaded_file_path = f"./resources/{unique_id}.jpg"

            with open(uploaded_file_path, "wb") as f:
                f.write(image_obj.read())
            image_obj.seek(0)

            with st.spinner("AI analyzing facial biometrics..."):
                image_numpy = image_obj_to_numpy(image_obj)
                faces = detect_all_faces(image_numpy, max_faces=5)

            if not faces:
                if os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)
                st.session_state["nc_file_key"] = file_key
                st.session_state["nc_faces"] = []
                st.session_state["nc_image_numpy"] = None
                st.session_state["nc_unique_id"] = None
                st.session_state["nc_uploaded_path"] = None
            else:
                st.session_state["nc_file_key"] = file_key
                st.session_state["nc_faces"] = faces
                st.session_state["nc_image_numpy"] = image_numpy
                st.session_state["nc_unique_id"] = unique_id
                st.session_state["nc_uploaded_path"] = uploaded_file_path

        faces = st.session_state.get("nc_faces", [])
        image_numpy = st.session_state.get("nc_image_numpy")
        unique_id = st.session_state.get("nc_unique_id")

        if not faces:
            st.html("""
            <div class="tx-face-status-err">
                No face detected. Upload a clear, front-facing photograph in good lighting.
            </div>
            """)
            selected_face_idx = None
        elif len(faces) == 1:
            annotated = draw_face_boxes(image_numpy, faces, selected_idx=0)
            st.image(annotated, use_container_width=True)
            st.html("""
            <div class="tx-face-status-ok">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                1 face detected &mdash; Ready for biometric registration
            </div>
            """)
            selected_face_idx = 0
        else:
            st.warning(f"**{len(faces)} faces detected.** Select the missing person:")
            options = [f"Face {i + 1}" for i in range(len(faces))]
            choice = st.radio("Select target face", options, horizontal=True, key="nc_face_choice")
            selected_face_idx = options.index(choice)
            annotated = draw_face_boxes(image_numpy, faces, selected_idx=selected_face_idx)
            st.image(annotated, use_container_width=True)
            st.html(f"""
            <div class="tx-face-status-ok">
                Target selected: Face {selected_face_idx + 1}
            </div>
            """)
    else:
        for k in ["nc_file_key", "nc_faces", "nc_image_numpy", "nc_unique_id", "nc_uploaded_path"]:
            st.session_state.pop(k, None)
        selected_face_idx = None
        unique_id = None
        faces = []

        # Placeholder zone
        st.html("""
        <div class="tx-upload-zone">
            <div style="display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;
                        border-radius:5px;background:#18191E;border:1px solid #27272A;margin-bottom:12px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#52525B"
                     stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
            </div>
            <div style="font-size:13px;font-weight:600;color:#71717A;">Drop a reference photo here</div>
            <div style="font-size:11px;color:#52525B;margin-top:4px;">JPG, PNG &bull; Up to 200 MB</div>
        </div>
        """)

face_ready = image_obj and faces and selected_face_idx is not None

# ── RIGHT: Case Form ───────────────────────────────────────────────────────
with form_col:
    st.html("""
    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
                color: #52525B; margin-bottom: 12px; display:flex; align-items:center; gap:8px;">
        <span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;
                     border-radius:3px;background:#1E2025;border:1px solid #27272A;font-size:9px;
                     font-weight:800;color:#A1A1AA;">2</span>
        Case Information
        <span style="flex:1;height:1px;background:#1E2025;"></span>
    </div>
    """)

    if not face_ready:
        st.html("""
        <div style="background:#0D0E11; border:1px dashed #22242A; border-radius:6px;
                    padding:3rem 1.5rem; text-align:center; color:#52525B;">
            <div style="display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;
                        border-radius:5px;background:#121316;border:1px solid #1E2025;margin-bottom:14px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3F3F46"
                     stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                    <circle cx="12" cy="13" r="4"></circle>
                </svg>
            </div>
            <div style="font-size:13px;font-weight:600;color:#A1A1AA;margin-bottom:4px;">Upload Reference Photo First</div>
            <div style="font-size:11px;color:#52525B;line-height:1.5;">
                The official case entry form unlocks once a face<br>is detected and biometrically verified.
            </div>
        </div>
        """)
    else:
        with st.form(key=f"new_case_form_{uploader_idx}"):
            # Section A: Person Identity
            st.html('<div class="tx-section-label">Person Identity</div>')
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Full Name *", placeholder="e.g. Ramesh Kumar")
                father_name = st.text_input("Father's / Guardian's Name", placeholder="e.g. Suresh Kumar")
                age = st.number_input("Age", min_value=1, max_value=120, value=25, step=1)
            with c2:
                adhaar_card = st.text_input("Aadhaar Number (12 digits)", placeholder="12-digit Aadhaar")
                mobile_number = st.text_input("Missing Person Mobile (if any)", placeholder="10 digits")
                birthmarks = st.text_input("Identifying Marks", placeholder="e.g. Mole on neck, scar on chin")

            st.html("<div style='height:8px'></div>")

            # Section B: Last Known Location
            st.html('<div class="tx-section-label">Last Known Location</div>')
            lc1, lc2 = st.columns(2)
            with lc1:
                city = st.text_input("City *", placeholder="e.g. Jamshedpur")
            with lc2:
                last_seen = st.text_input("Last Seen Location *", placeholder="e.g. Near Tatanagar Railway Station")
            address = st.text_input("Residential Address", placeholder="Permanent home address")

            st.html("<div style='height:8px'></div>")

            # Section C: Complainant
            st.html('<div class="tx-section-label">Complainant / Contact</div>')
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                complainant_name = st.text_input("Complainant Name *", placeholder="e.g. Sunita Devi")
            with cc2:
                complainant_phone = st.text_input("Phone * (10 digits)", placeholder="10 digits")
            with cc3:
                complainant_email = st.text_input("Email (Optional)", placeholder="e.g. sunita@email.com")

            st.html("<div style='height:8px'></div>")

            # Section D: Notes
            st.html('<div class="tx-section-label">Case Notes</div>')
            description = st.text_area(
                "Case Description & Additional Notes (Optional)",
                placeholder="Any additional context, clothing description, medical conditions, etc.",
                height=90,
            )

            submit_bt = st.form_submit_button(
                "Index Case & Register Facial Profile",
                use_container_width=True,
            )

            if submit_bt:
                errors = []
                if not name.strip():
                    errors.append("Full Name is required.")
                if not city.strip():
                    errors.append("City is required.")
                if not last_seen.strip():
                    errors.append("Last Seen Location is required.")
                if not complainant_name.strip():
                    errors.append("Complainant Name is required.")
                if not complainant_phone.strip():
                    errors.append("Complainant Phone is required.")
                elif not complainant_phone.strip().isdigit() or len(complainant_phone.strip()) != 10:
                    errors.append("Complainant Phone must be exactly 10 digits.")
                if mobile_number.strip() and (
                    not mobile_number.strip().isdigit() or len(mobile_number.strip()) != 10
                ):
                    errors.append("Missing Person Mobile must be exactly 10 digits.")
                if adhaar_card.strip() and (
                    not adhaar_card.strip().isdigit() or len(adhaar_card.strip()) != 12
                ):
                    errors.append("Aadhaar Card must be exactly 12 digits.")

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    selected_bbox = faces[selected_face_idx]["bbox"]
                    with st.spinner("Extracting 512-d ArcFace facial signature..."):
                        embedding = extract_face_embedding(image_numpy, selected_bbox)

                    if embedding is None:
                        st.error(
                            "Could not extract facial signature. "
                            "Please upload a clearer, front-facing photograph."
                        )
                    else:
                        new_case_details = RegisteredCases(
                            id=unique_id,
                            submitted_by=user,
                            name=name.strip(),
                            father_name=father_name.strip(),
                            age=str(age),
                            complainant_mobile=complainant_phone.strip(),
                            complainant_name=complainant_name.strip(),
                            complainant_email=complainant_email.strip() or None,
                            face_mesh=json.dumps(embedding),
                            adhaar_card=adhaar_card.strip(),
                            birth_marks=birthmarks.strip(),
                            address=address.strip(),
                            city=city.strip() or None,
                            last_seen=last_seen.strip(),
                            description=description.strip() or None,
                            status="NF",
                            matched_with="",
                        )
                        db_queries.register_new_case(new_case_details)
                        st.session_state["registered_case_id"] = unique_id
                        st.session_state["registered_case_name"] = name.strip()
                        st.rerun()
