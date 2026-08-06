"""
feature_similarity.py

Compares the features.json of two kits. In contrast to fuzzy_hash.py,
which compares bytes/text, this compares meaning.
Two kits may be rewritten letter by letter, and still have
almost identical features (e.g. same backdoor, same antibot).
compute_similarity.py combines both signals.
"""

from corpus_utils import flatten_features


def _compare_value(a, b):
    """
    Compares two values of a single feature.
    Uses Jaccard similarity for lists and exact equality for the rest.
    """
    if isinstance(a, list) and isinstance(b, list):
        set_a, set_b = set(a), set(b)
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)
    return 1.0 if a == b else 0.0


def feature_similarity(features_a, features_b, ignore_keys=None):
    """
    Returns a score 0.0-1.0, the average of how many features match
    between two kits over the total number of features compared.

    ignore_keys allows excluding fields that we know vary for
    legitimate copies of the same kit, such as exfil destination.
    """
    ignore_keys = ignore_keys or set()
    flat_a = flatten_features(features_a)
    flat_b = flatten_features(features_b)
    keys = (set(flat_a) | set(flat_b)) - ignore_keys
    if not keys:
        return 0.0
    scores = [_compare_value(flat_a.get(k), flat_b.get(k)) for k in keys]
    return sum(scores) / len(scores)