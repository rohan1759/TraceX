import argparse
import os
import sys
import tempfile
import warnings
import numpy as np
from PIL import Image

warnings.filterwarnings("ignore")

# Ensure repository root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pages.helper import utils
from pages.helper.matching_config import MATCH_DISTANCE_THRESHOLD


def evaluate_folder(folder_path: str, max_side: int = 1600, quality: int = 90):
    if not os.path.isdir(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    image_paths = []
    for root, _, files in os.walk(folder_path):
        for f in sorted(files):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                image_paths.append(os.path.join(root, f))

    if not image_paths:
        print(f"No image files (.jpg, .jpeg, .png) found in '{folder_path}'.")
        return

    print(f"Found {len(image_paths)} images in '{folder_path}'.")
    print(f"Configured MATCH_DISTANCE_THRESHOLD: {MATCH_DISTANCE_THRESHOLD}")
    limit_25pct = 0.25 * MATCH_DISTANCE_THRESHOLD
    print(f"25% of Match Threshold: {limit_25pct:.4f}")
    print("-" * 80)
    print(f"{'Image Filename':<45} | {'Cosine Distance':<18} | {'Status'}")
    print("-" * 80)

    results = []
    skipped = []

    for img_path in image_paths:
        rel_name = os.path.relpath(img_path, folder_path)
        try:
            with Image.open(img_path) as pil_img:
                img_rgb = pil_img.convert("RGB")
                img_np = np.array(img_rgb)

            # 1. Compute embedding of original
            faces_orig = utils.detect_all_faces(img_np, max_faces=1)
            if not faces_orig:
                print(f"{rel_name:<45} | {'NO FACE DETECTED':<18} | SKIPPED")
                skipped.append((rel_name, "No face detected in original"))
                continue

            emb_orig = utils.extract_face_embedding(img_np, faces_orig[0]["bbox"])
            if emb_orig is None:
                print(f"{rel_name:<45} | {'EMB EXTRACTION FAILED':<18} | SKIPPED")
                skipped.append((rel_name, "Failed to extract embedding from original"))
                continue

            # 2. Run save_display_image to a temp file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                utils.save_display_image(img_np, tmp_path, max_side=max_side, quality=quality)

                # 3. Compute embedding of saved copy
                with Image.open(tmp_path) as saved_pil:
                    saved_np = np.array(saved_pil.convert("RGB"))

                faces_saved = utils.detect_all_faces(saved_np, max_faces=1)
                bbox_saved = faces_saved[0]["bbox"] if faces_saved else faces_orig[0]["bbox"]
                emb_saved = utils.extract_face_embedding(saved_np, bbox_saved)

                if emb_saved is None:
                    print(f"{rel_name:<45} | {'SAVED EMB FAILED':<18} | SKIPPED")
                    skipped.append((rel_name, "Failed to extract embedding from saved copy"))
                    continue

                # 4. Compute cosine distance
                dist = utils._cosine_distance(emb_orig, emb_saved)
                results.append((rel_name, dist))

                status = "EXCEEDS 25%" if dist > limit_25pct else "PASS"
                print(f"{rel_name:<45} | {dist:<18.6f} | {status}")

            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

        except Exception as e:
            print(f"{rel_name:<45} | ERROR: {e}")
            skipped.append((rel_name, str(e)))

    print("=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)
    print(f"Total images evaluated: {len(results)} / {len(image_paths)}")
    if skipped:
        print(f"Skipped / Failed images: {len(skipped)}")

    if results:
        distances = [d for _, d in results]
        mean_dist = float(np.mean(distances))
        max_dist = float(np.max(distances))
        min_dist = float(np.min(distances))
        exceeding = [r for r in results if r[1] > limit_25pct]

        print(f"Mean Cosine Distance:   {mean_dist:.6f}")
        print(f"Min Cosine Distance:    {min_dist:.6f}")
        print(f"Max Cosine Distance:    {max_dist:.6f}")
        print(f"Configured Threshold:   {MATCH_DISTANCE_THRESHOLD}")
        print(f"25% of Threshold:       {limit_25pct:.4f}")
        print(f"Images exceeding 25%:   {len(exceeding)} ({len(exceeding) / len(results) * 100:.2f}%)")

        if exceeding:
            print("\nImages that exceeded 25% threshold:")
            for name, dist in exceeding:
                print(f"  - {name}: {dist:.6f}")
        else:
            print("\nResult: All evaluated images remained well within 25% of the match threshold.")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Verify compression effect on facial embeddings")
    parser.add_argument(
        "folder",
        nargs="?",
        default="scripts/bulk_data",
        help="Folder containing images to evaluate (default: scripts/bulk_data)",
    )
    parser.add_argument("--max-side", type=int, default=1600, help="Max long side dimension (default: 1600)")
    parser.add_argument("--quality", type=int, default=90, help="JPEG compression quality (default: 90)")
    args = parser.parse_args()

    evaluate_folder(args.folder, max_side=args.max_side, quality=args.quality)


if __name__ == "__main__":
    main()

