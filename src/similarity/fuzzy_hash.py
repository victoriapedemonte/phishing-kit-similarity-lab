"""
fuzzy_hash.py

We use three independent fuzzy fingerprint methos for phishing kits,
which are combined in an ensemble: ssdeep, TLSH, and our own shingling method.
"""

import re

try:
    import ssdeep as _ssdeep
    HAS_SSDEEP = True
except ImportError:
    HAS_SSDEEP = False

try:
    import tlsh as _tlsh
    HAS_TLSH = True
except ImportError:
    HAS_TLSH = False


def _shingles(text, k=5):
    """
    Sliding windows of k characters, with whitespaces normalized first.
    """
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) < k:
        return {normalized} if normalized else set()
    return {normalized[i : i + k] for i in range(len(normalized) - k + 1)}


def kit_blob(files, exclude_logical_names=None):
    """
    Concatenates the content of all files in a kit into a single text blob.
    """
    from feature_extraction.features import logical_filename

    exclude = exclude_logical_names or set()
    parts = [
        content
        for name, content in sorted(files.items())
        if logical_filename(name) not in exclude
    ]
    return "\n".join(parts)


def compute_kit_fingerprint(text):
    """
    Calculates everything needed to compare kits later: the set of shingles,
    and the ssdeep/tlsh hashes.
    """
    fingerprint = {"shingles": _shingles(text)}
    fingerprint["ssdeep"] = _ssdeep.hash(text) if HAS_SSDEEP else None

    if HAS_TLSH:
        h = _tlsh.hash(text.encode("utf-8", errors="ignore"))
        fingerprint["tlsh"] = None if h in ("TNULL", "") else h
    else:
        fingerprint["tlsh"] = None

    return fingerprint


def compare_fingerprints(fp_a, fp_b):
    """
    Compares two fingerprints and returns each method and an ensemble score.
    """
    scores = {}

    sa, sb = fp_a["shingles"], fp_b["shingles"]
    if not sa and not sb:
        scores["shingle"] = 1.0
    elif not sa or not sb:
        scores["shingle"] = 0.0
    else:
        scores["shingle"] = len(sa & sb) / len(sa | sb)

    if HAS_SSDEEP and fp_a["ssdeep"] and fp_b["ssdeep"]:
        scores["ssdeep"] = _ssdeep.compare(fp_a["ssdeep"], fp_b["ssdeep"]) / 100.0
    else:
        scores["ssdeep"] = None

    if HAS_TLSH and fp_a["tlsh"] and fp_b["tlsh"]:
        distance = _tlsh.diff(fp_a["tlsh"], fp_b["tlsh"])
        #We turn the tlsh distance into a similarity score between 0 and 1.
        scores["tlsh"] = 1.0 / (1.0 + distance / 50.0)
    else:
        scores["tlsh"] = None

    available = [v for v in scores.values() if v is not None]
    scores["ensemble"] = sum(available) / len(available) if available else 0.0
    return scores