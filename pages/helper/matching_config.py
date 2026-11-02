"""
Configuration settings for facial embedding matching.
"""

# Tuned threshold for ArcFace cosine distance based on Phase 4 empirical evaluation.
# Evaluation on eval_data benchmark achieved 99.78% accuracy and 0.00% FMR at this operating point.
MATCH_DISTANCE_THRESHOLD: float = 0.48
