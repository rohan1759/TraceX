"""
Script to reprocess existing database records and upgrade face vectors to 512-d ArcFace embeddings.

Usage:
    python scripts/reprocess_embeddings.py --dry-run   # Simulate without modifying database
    python scripts/reprocess_embeddings.py             # Apply updates to database
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Allow imports from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import cv2
import PIL.Image
import numpy as np
from sqlmodel import Session, select

from pages.helper.db_queries import engine
from pages.helper.data_models import RegisteredCases, PublicSubmissions
from pages.helper.utils import (
    _ensure_model_silent,
    detect_all_faces,
    extract_face_embedding,
    _normalize_image,
)


def reprocess_table(session: Session, model_class, table_name: str, resources_dir: Path, dry_run: bool = False):
    print(f"\n=======================================================")
    print(f" Processing Table: {table_name} {'[DRY RUN]' if dry_run else '[LIVE UPDATE]'}")
    print(f"=======================================================")

    records = session.exec(select(model_class)).all()
    total = len(records)
    print(f"Found {total} total record(s) in {table_name}.")

    success_count = 0
    missing_img_count = 0
    no_face_count = 0
    failed_emb_count = 0
    already_512_count = 0

    for idx, record in enumerate(records, start=1):
        rec_id = str(record.id)
        img_path = resources_dir / f"{rec_id}.jpg"

        print(f"[{idx}/{total}] ID: {rec_id} ... ", end="", flush=True)

        if not img_path.exists():
            print("MISSING IMAGE FILE")
            missing_img_count += 1
            continue

        try:
            pil_img = PIL.Image.open(img_path).convert("RGB")
            img_rgb = np.array(pil_img)
        except Exception as e:
            print(f"ERROR READING IMAGE ({e})")
            missing_img_count += 1
            continue

        # Detect face via MediaPipe
        try:
            faces = detect_all_faces(img_rgb, max_faces=1)
        except Exception as e:
            faces = []

        if not faces:
            print("NO FACE DETECTED BY MEDIAPIPE")
            no_face_count += 1
            continue

        # Extract 512-d ArcFace embedding
        bbox = faces[0]["bbox"]
        try:
            embedding = extract_face_embedding(img_rgb, bbox)
        except Exception as e:
            embedding = None

        if embedding is None or len(embedding) != 512:
            print("FAILED TO EXTRACT 512-D EMBEDDING")
            failed_emb_count += 1
            continue

        # Check existing vector
        try:
            existing_vec = json.loads(record.face_mesh) if record.face_mesh else []
            if isinstance(existing_vec, list) and len(existing_vec) == 512:
                already_512_count += 1
        except Exception:
            pass

        success_count += 1
        print("OK (512-d embedding extracted)")

        if not dry_run:
            record.face_mesh = json.dumps(embedding)
            session.add(record)

    if not dry_run and success_count > 0:
        session.commit()
        print(f"\n[COMMITTED] Successfully updated {success_count} record(s) in {table_name}.")
    elif dry_run:
        print(f"\n[DRY RUN] No changes were written to database.")

    summary = {
        "table": table_name,
        "total": total,
        "success": success_count,
        "missing_image": missing_img_count,
        "no_face_detected": no_face_count,
        "failed_embedding": failed_emb_count,
        "already_512": already_512_count,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Reprocess face vectors in database to 512-d embeddings.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the reprocessing run without updating database records.",
    )
    args = parser.parse_args()

    # Ensure working directory is project root
    os.chdir(ROOT)
    _ensure_model_silent()

    resources_dir = ROOT / "resources"

    print("=======================================================")
    print("        DATABASE EMBEDDINGS REPROCESSING TOOL          ")
    print(f" Mode: {'DRY RUN (Read-Only Simulation)' if args.dry_run else 'LIVE RUN (Modifies Database)'}")
    print("=======================================================")

    with Session(engine) as session:
        rc_summary = reprocess_table(session, RegisteredCases, "registeredcases", resources_dir, dry_run=args.dry_run)
        ps_summary = reprocess_table(session, PublicSubmissions, "publicsubmissions", resources_dir, dry_run=args.dry_run)

    print("\n" + "=" * 65)
    print("                   FINAL SUMMARY REPORT                   ")
    print("=" * 65)
    print(f"{'Metric':<30} | {'Registered Cases':<15} | {'Public Submissions':<15}")
    print("-" * 65)
    print(f"{'Total Records':<30} | {rc_summary['total']:<15} | {ps_summary['total']:<15}")
    print(f"{'Successfully Computed (512-d)':<30} | {rc_summary['success']:<15} | {ps_summary['success']:<15}")
    print(f"{'Missing Image Files':<30} | {rc_summary['missing_image']:<15} | {ps_summary['missing_image']:<15}")
    print(f"{'No Face Detected':<30} | {rc_summary['no_face_detected']:<15} | {ps_summary['no_face_detected']:<15}")
    print(f"{'Failed Extraction':<30} | {rc_summary['failed_embedding']:<15} | {ps_summary['failed_embedding']:<15}")
    print(f"{'Database Changes Applied?':<30} | {'NO (Dry Run)' if args.dry_run else 'YES':<15} | {'NO (Dry Run)' if args.dry_run else 'YES':<15}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

