"""
Evaluation script to benchmark ArcFace cosine distance thresholds.

Usage:
    python scripts/evaluate_matching.py
    python scripts/evaluate_matching.py --data-dir eval_data --csv eval_data/evaluation_results.csv --plot eval_data/evaluation_plot.png
"""

import os
import sys
import argparse
import itertools
from pathlib import Path

# Allow imports from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import cv2
import PIL.Image
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Headless backend for command-line execution
import matplotlib.pyplot as plt

from pages.helper.utils import (
    _ensure_model_silent,
    detect_all_faces,
    extract_face_embedding,
)


def load_dataset_embeddings(data_dir: Path):
    """
    Traverse subdirectories in data_dir, extract 512-d embeddings for each image.
    Returns:
        embeddings: list of np.ndarray (shape 512)
        identities: list of str (person identity folder name)
        image_paths: list of Path
    """
    embeddings = []
    identities = []
    image_paths = []

    subdirs = sorted([d for d in data_dir.iterdir() if d.is_dir()])
    if not subdirs:
        raise ValueError(f"No identity subdirectories found in {data_dir}")

    print(f"Loading evaluation images from {len(subdirs)} identity directories in '{data_dir}'...")

    valid_exts = {".jpg", ".jpeg", ".png"}

    for person_dir in subdirs:
        person_name = person_dir.name
        img_files = sorted([f for f in person_dir.iterdir() if f.suffix.lower() in valid_exts])

        for img_path in img_files:
            try:
                pil_img = PIL.Image.open(img_path).convert("RGB")
                img_rgb = np.array(pil_img)
            except Exception as e:
                print(f"  [ERROR] Could not read {img_path.name}: {e}")
                continue

            # Detect face
            faces = detect_all_faces(img_rgb, max_faces=1)
            if not faces:
                print(f"  [SKIP] No face detected by MediaPipe in {person_name}/{img_path.name}")
                continue

            bbox = faces[0]["bbox"]
            emb = extract_face_embedding(img_rgb, bbox)
            if emb is None or len(emb) != 512:
                print(f"  [SKIP] Failed to extract 512-d embedding for {person_name}/{img_path.name}")
                continue

            emb_arr = np.array(emb, dtype=np.float32)
            # Ensure exact L2 unit normalization
            norm = np.linalg.norm(emb_arr)
            if norm > 0:
                emb_arr = emb_arr / norm

            embeddings.append(emb_arr)
            identities.append(person_name)
            image_paths.append(img_path)

    print(f"Successfully loaded and computed embeddings for {len(embeddings)} face photos.")
    return embeddings, identities, image_paths


def build_pairs_and_distances(embeddings, identities):
    """
    Construct all pairwise comparisons:
      positive_pairs: same person (person_i == person_j)
      negative_pairs: different people (person_i != person_j)
    Returns:
      pos_distances: np.ndarray of cosine distances
      neg_distances: np.ndarray of cosine distances
    """
    n = len(embeddings)
    pos_distances = []
    neg_distances = []

    for i, j in itertools.combinations(range(n), 2):
        # Cosine distance between unit vectors: 1.0 - dot(u, v)
        dot_prod = float(np.dot(embeddings[i], embeddings[j]))
        dist = max(0.0, 1.0 - dot_prod)

        if identities[i] == identities[j]:
            pos_distances.append(dist)
        else:
            neg_distances.append(dist)

    pos_distances = np.array(pos_distances, dtype=np.float32)
    neg_distances = np.array(neg_distances, dtype=np.float32)

    print(f"\nConstructed Evaluation Pairs:")
    print(f"  - Positive Pairs (same individual)    : {len(pos_distances)}")
    print(f"  - Negative Pairs (distinct individuals): {len(neg_distances)}")
    print(f"  - Total Pairwise Comparisons          : {len(pos_distances) + len(neg_distances)}")

    return pos_distances, neg_distances


def evaluate_thresholds(pos_distances, neg_distances, thresholds):
    """
    Sweep across thresholds and compute metrics.
    """
    n_pos = len(pos_distances)
    n_neg = len(neg_distances)
    total_pairs = n_pos + n_neg

    records = []

    for thresh in thresholds:
        tp = int(np.sum(pos_distances <= thresh))
        fn = n_pos - tp
        fp = int(np.sum(neg_distances <= thresh))
        tn = n_neg - fp

        tmr = tp / n_pos if n_pos > 0 else 0.0  # Recall / True Match Rate
        fmr = fp / n_neg if n_neg > 0 else 0.0  # Fall-out / False Match Rate
        accuracy = (tp + tn) / total_pairs if total_pairs > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = (2 * precision * tmr) / (precision + tmr) if (precision + tmr) > 0 else 0.0

        records.append({
            "Threshold": round(thresh, 3),
            "True_Match_Rate": round(tmr, 4),
            "False_Match_Rate": round(fmr, 4),
            "Accuracy": round(accuracy, 4),
            "Precision": round(precision, 4),
            "F1_Score": round(f1, 4),
            "TP": tp,
            "FP": fp,
            "TN": tn,
            "FN": fn,
        })

    df = pd.DataFrame(records)
    return df


def plot_metrics(df: pd.DataFrame, best_acc_row: pd.Series, output_path: Path):
    """Generate and save metric curves."""
    fig, ax = plt.subplots(figsize=(9, 6), dpi=150)

    ax.plot(df["Threshold"], df["True_Match_Rate"], label="True Match Rate (TMR / Recall)", color="#2ecc71", lw=2)
    ax.plot(df["Threshold"], df["False_Match_Rate"], label="False Match Rate (FMR / FPR)", color="#e74c3c", lw=2)
    ax.plot(df["Threshold"], df["Accuracy"], label="Overall Accuracy", color="#3498db", lw=2.2, linestyle="--")
    ax.plot(df["Threshold"], df["F1_Score"], label="F1-Score", color="#9b59b6", lw=1.8, linestyle=":")

    best_thresh = best_acc_row["Threshold"]
    best_acc = best_acc_row["Accuracy"]

    ax.axvline(
        x=best_thresh,
        color="#2c3e50",
        linestyle="-.",
        lw=1.5,
        label=f"Best Acc Threshold ({best_thresh:.2f} @ {best_acc*100:.1f}%)",
    )

    ax.set_title("ArcFace Cosine Distance Threshold Evaluation", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Cosine Distance Threshold (Match if distance ≤ Threshold)", fontsize=11)
    ax.set_ylabel("Rate / Score (0.0 – 1.0)", fontsize=11)
    ax.set_xlim(min(df["Threshold"]), max(df["Threshold"]))
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="center right", fontsize=10, frameon=True)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"Evaluation plot saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate ArcFace cosine distance matching thresholds.")
    parser.add_argument("--data-dir", default="eval_data", help="Directory containing identity subfolders")
    parser.add_argument("--csv", default="eval_data/evaluation_results.csv", help="Output path for results CSV")
    parser.add_argument("--plot", default="eval_data/evaluation_plot.png", help="Output path for evaluation plot")
    args = parser.parse_args()

    os.chdir(ROOT)
    _ensure_model_silent()

    data_dir = ROOT / args.data_dir
    csv_path = ROOT / args.csv
    plot_path = ROOT / args.plot

    if not data_dir.exists():
        print(f"Error: Data directory '{data_dir}' does not exist.")
        sys.exit(1)

    embeddings, identities, image_paths = load_dataset_embeddings(data_dir)
    if len(embeddings) < 2:
        print("Error: Need at least 2 valid face images to perform evaluation.")
        sys.exit(1)

    pos_distances, neg_distances = build_pairs_and_distances(embeddings, identities)
    if len(pos_distances) == 0:
        print("Error: No positive (same person) pairs found. Make sure at least one person has >= 2 photos.")
        sys.exit(1)

    # Threshold sweep from 0.10 to 0.85 in steps of 0.025
    thresholds = np.arange(0.10, 0.86, 0.025)
    df = evaluate_thresholds(pos_distances, neg_distances, thresholds)

    # Find best accuracy threshold
    best_acc_row = df.loc[df["Accuracy"].idxmax()]
    best_f1_row = df.loc[df["F1_Score"].idxmax()]

    # Print summary table
    print("\n" + "=" * 80)
    print("                     THRESHOLD BENCHMARK RESULTS                        ")
    print("=" * 80)
    print(f"{'Threshold':<11} | {'TMR (Recall)':<14} | {'FMR (FPR)':<12} | {'Accuracy':<10} | {'Precision':<10} | {'F1-Score':<10}")
    print("-" * 80)
    for _, r in df.iloc[::2].iterrows():  # Print every 2nd row for concise readable table
        marker = " <== BEST ACC" if r["Threshold"] == best_acc_row["Threshold"] else ""
        print(f"{r['Threshold']:<11.3f} | {r['True_Match_Rate']:<14.2%} | {r['False_Match_Rate']:<12.2%} | {r['Accuracy']:<10.2%} | {r['Precision']:<10.2%} | {r['F1_Score']:<10.4f}{marker}")
    print("=" * 80)

    print(f"\nOPTIMAL THRESHOLD RECOMMENDATIONS:")
    print(f"  * Best Accuracy Threshold: {best_acc_row['Threshold']:.3f} (Accuracy: {best_acc_row['Accuracy']:.2%}, TMR: {best_acc_row['True_Match_Rate']:.2%}, FMR: {best_acc_row['False_Match_Rate']:.2%})")
    print(f"  * Best F1-Score Threshold: {best_f1_row['Threshold']:.3f} (F1: {best_f1_row['F1_Score']:.4f}, Precision: {best_f1_row['Precision']:.2%}, TMR: {best_f1_row['True_Match_Rate']:.2%})")

    # Save CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"\nEvaluation metrics CSV saved to: {csv_path}")

    # Save Plot
    plot_metrics(df, best_acc_row, plot_path)


if __name__ == "__main__":
    main()

