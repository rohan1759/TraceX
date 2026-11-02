"""
Test script for InsightFace ArcFace embedding extraction and cosine distance comparison.
Usage:
    python scripts/test_embedding.py <image_path_1> <image_path_2>
"""

import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
from insightface.app import FaceAnalysis


def get_largest_face_embedding(app: FaceAnalysis, image_path: str):
    """Load image, detect faces, and return the embedding of the largest face."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Failed to read image with cv2: {image_path}")

    faces = app.get(img)
    if not faces:
        # Try lower detection threshold if default 0.5 missed it on high-res crops
        if hasattr(app, "det_model") and hasattr(app.det_model, "det_thresh"):
            original_thresh = app.det_model.det_thresh
            app.det_model.det_thresh = 0.1
            faces = app.get(img)
            app.det_model.det_thresh = original_thresh

    if not faces:
        raise ValueError(f"No face detected in image: {image_path}")

    # Pick the largest face by bounding box area (x2 - x1) * (y2 - y1)
    largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return largest_face.embedding


def cosine_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine distance between two embedding vectors: 1 - cosine_similarity."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 1.0
    similarity = float(np.dot(vec1, vec2) / (norm1 * norm2))
    return 1.0 - similarity


def main():
    parser = argparse.ArgumentParser(description="InsightFace embedding and cosine distance test.")
    parser.add_argument("img1", nargs="?", help="Path to first image")
    parser.add_argument("img2", nargs="?", help="Path to second image")
    args = parser.parse_args()

    # Initialize InsightFace FaceAnalysis
    print("Initializing InsightFace (buffalo_l)...")
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))

    if args.img1 and args.img2:
        pairs = [(args.img1, args.img2, "CLI Arguments")]
    else:
        # Default test pairs if no arguments given
        pairs = [
            ("scripts/bulk_data/reported/alia_bhatt_1.jpg", "scripts/bulk_data/reported/alia_bhatt_2.jpg", "Same Person (Alia Bhatt 1 vs 2)"),
            ("scripts/bulk_data/publicly_seen/shah_rukh_khan_1.jpg", "scripts/bulk_data/publicly_seen/shah_rukh_khan_2.jpg", "Same Person (Shah Rukh Khan 1 vs 2)"),
            ("scripts/bulk_data/reported/alia_bhatt_1.jpg", "scripts/bulk_data/reported/salman_khan_1.jpg", "Different People (Alia Bhatt 1 vs Salman Khan 1)"),
            ("scripts/bulk_data/publicly_seen/shah_rukh_khan_1.jpg", "scripts/bulk_data/reported/alia_bhatt_1.jpg", "Different People (Shah Rukh Khan 1 vs Alia Bhatt 1)"),
        ]

    for p1, p2, desc in pairs:
        print(f"\n--- Comparing: {desc} ---")
        print(f"Image 1: {p1}")
        print(f"Image 2: {p2}")
        try:
            emb1 = get_largest_face_embedding(app, p1)
            emb2 = get_largest_face_embedding(app, p2)
            dist = cosine_distance(emb1, emb2)
            similarity = 1.0 - dist
            print(f"Embedding 1 length: {len(emb1)}")
            print(f"Embedding 2 length: {len(emb2)}")
            print(f"Cosine Distance   : {dist:.6f}")
            print(f"Cosine Similarity : {similarity:.6f}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()

