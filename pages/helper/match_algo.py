import json
import warnings
from collections import defaultdict

import numpy as np
from sklearn.neighbors import NearestNeighbors

from pages.helper import db_queries
from pages.helper.matching_config import MATCH_DISTANCE_THRESHOLD

warnings.filterwarnings(action="ignore")


def _load_and_validate_vectors(raw_rows):
    """
    Parse (id, face_mesh_json) rows from database queries.

    Returns:
        labels: list of str IDs
        vectors: list of 512-d float vectors
        skipped: int count of records whose vector length != 512
    """
    labels = []
    vectors = []
    skipped = 0

    for row in raw_rows:
        case_id = row[0]
        mesh_raw = row[1]
        try:
            vec = json.loads(mesh_raw) if isinstance(mesh_raw, str) else mesh_raw
            if isinstance(vec, list) and len(vec) == 512:
                labels.append(str(case_id))
                vectors.append(vec)
            else:
                skipped += 1
        except Exception:
            skipped += 1

    return labels, vectors, skipped


def get_public_cases_data(status="NF"):
    """Fetch public sighting cases and return valid 512-d vectors."""
    try:
        raw = db_queries.fetch_public_cases(train_data=True, status=status)
        return _load_and_validate_vectors(raw)
    except Exception as e:
        return [], [], 0


def get_registered_cases_data(status="NF"):
    """Fetch registered missing cases and return valid 512-d vectors."""
    try:
        raw = db_queries.get_training_data()
        return _load_and_validate_vectors(raw)
    except Exception as e:
        return [], [], 0


def match(distance_threshold: float = MATCH_DISTANCE_THRESHOLD):
    """
    Vectorized facial matching using scikit-learn NearestNeighbors with cosine distance.

    Returns top 3 closest registered cases per public sighting within the distance threshold.
    Skips records whose vector length does not match 512 and reports counts.
    """
    pub_labels, pub_vectors, skipped_pub = get_public_cases_data(status="NF")
    reg_labels, reg_vectors, skipped_reg = get_registered_cases_data(status="NF")

    if not pub_labels or not reg_labels:
        msg = "No eligible cases found for matching."
        if skipped_pub > 0 or skipped_reg > 0:
            msg += (
                f" (Skipped {skipped_reg} registered case(s) and {skipped_pub} public sighting(s) "
                f"with feature vectors != 512)."
            )
        return {
            "status": False,
            "message": msg,
            "result": {},
            "sighting_matches": {},
            "skipped_registered": skipped_reg,
            "skipped_public": skipped_pub,
        }

    reg_features = np.array(reg_vectors, dtype=np.float32)
    pub_features = np.array(pub_vectors, dtype=np.float32)

    # Normalize vectors to ensure exact cosine distance calculations
    reg_norms = np.linalg.norm(reg_features, axis=1, keepdims=True)
    pub_norms = np.linalg.norm(pub_features, axis=1, keepdims=True)
    reg_features = np.divide(reg_features, reg_norms, out=reg_features, where=reg_norms > 0)
    pub_features = np.divide(pub_features, pub_norms, out=pub_features, where=pub_norms > 0)

    # Query top 3 closest registered cases per sighting
    k = min(3, len(reg_labels))
    nn = NearestNeighbors(n_neighbors=k, metric="cosine", algorithm="brute")
    nn.fit(reg_features)

    # Vectorized kneighbors computation: distances and indices shape (n_queries, k)
    distances, indices = nn.kneighbors(pub_features)

    sighting_matches = defaultdict(list)
    matched_images = defaultdict(list)

    for i, pub_id in enumerate(pub_labels):
        for dist, idx in zip(distances[i], indices[i]):
            dist_val = float(dist)
            if dist_val <= distance_threshold:
                reg_id = reg_labels[idx]
                sighting_matches[pub_id].append((reg_id, dist_val))
                matched_images[reg_id].append((pub_id, dist_val))

    # Sort candidate sightings for each registered case by closest distance
    for reg_id in matched_images:
        matched_images[reg_id].sort(key=lambda x: x[1])

    return {
        "status": True,
        "result": matched_images,
        "sighting_matches": sighting_matches,
        "skipped_registered": skipped_reg,
        "skipped_public": skipped_pub,
        "distance_threshold": distance_threshold,
    }


if __name__ == "__main__":
    result = match()
    print(result)
