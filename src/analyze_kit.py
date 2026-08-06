"""
analyze_kit.py

Analyzes a suspicious kit (any folder on disk) against the reference corpus
already built and labeled, and answers:
    - Which family does it most resemble?
    - Is it probably malicious, or more like the bening reference? 
        And which signals support that?
    - Who are its closest neighbors, and with what score?
    - If there's a trained classifier, what does it predict?

Use:
    cd src
    python3 analyze_kit.py /path/to/a/suspicous/kit
"""

import argparse
import os
import sys

import joblib

from corpus_utils import ROOT_DIR, collect_kits, discover_dataset_dirs, flatten_features, load_ground_truth, load_kit_files
from feature_extraction.features import extract_all_features
from similarity.feature_similarity import feature_similarity
from similarity.fuzzy_hash import compare_fingerprints, compute_kit_fingerprint, kit_blob

TOP_N = 5
NOISY_FEATURE_KEYS = {"exfil_indicators.config_placeholder_values"}
MODEL_PATH = os.path.join(ROOT_DIR, "models", "classifier.joblib")

SUSPICIOUS_INDICATORS = [
    ("exfil_indicators.is_external_action", True,
     "The form sends data to an external domain"),
    ("exfil_indicators.has_fixed_backdoor_pattern", True,
     "There's a second fixed exfil destination, besides the configurable one"),
    ("exfil_indicators.has_empty_or_blank_action", True,
     "The destination of the form is empty or 'about:blank'"),
    ("file_manifest.has_config_engine_split", True,
     "Separates 'config' and 'engine' in different files"),
    ("evasion_indicators.has_antibot_folder", True,
     "Has an antibot/ folder"),
    ("evasion_indicators.has_htaccess", True,
     "Has a .htaccess file"),
    ("link_indicators.has_navigation_links", False,
     "Has no navigation links, typical of a standalone page"),
    ("obfuscation_indicators.has_base64_blob", True,
     "Contains a base64 blob (possible obfuscation)"),
]


def explain(features):
    """For traceability, returns a list of human-readable lines explaining
    which suspicious indicators are present in the kit."""
    flat = flatten_features(features)
    lines = []
    for key, trigger_value, description in SUSPICIOUS_INDICATORS:
        present = flat.get(key) == trigger_value
        lines.append(f"  [{'x' if present else ' '}] {description}")
    return lines


def load_classifier():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


def build_reference_corpus():
    """
    Gathers kits under datasets/ that have ground_truth.csv.
    """
    corpus = {}
    for dataset_dir in discover_dataset_dirs():
        ground_truth = load_ground_truth(dataset_dir)
        if not ground_truth:
            continue
        for kit_id, files in collect_kits(dataset_dir).items():
            corpus[kit_id] = {"files": files, "meta": ground_truth.get(kit_id, {})}
    return corpus


def analyze(kit_path):
    query_files = load_kit_files(kit_path)
    if not query_files:
        print(f"No text files found in {kit_path}")
        sys.exit(1)

    corpus = build_reference_corpus()
    if not corpus:
        print("The reference corpus is empty. Run generate_dataset.py first.")
        sys.exit(1)

    query_features = extract_all_features(query_files)
    query_blob_engine = kit_blob(query_files, exclude_logical_names={"config.php"})
    query_fp_engine = compute_kit_fingerprint(query_blob_engine)

    results = []
    for kit_id, entry in corpus.items():
        ref_blob_engine = kit_blob(entry["files"], exclude_logical_names={"config.php"})
        if ref_blob_engine == query_blob_engine:
            continue

        engine_scores = compare_fingerprints(
            query_fp_engine, compute_kit_fingerprint(ref_blob_engine)
        )
        feat_sim = feature_similarity(
            query_features, extract_all_features(entry["files"]), ignore_keys=NOISY_FEATURE_KEYS
        )
        combined = 0.5 * engine_scores["ensemble"] + 0.5 * feat_sim

        results.append({
            "kit_id": kit_id,
            "family": entry["meta"].get("family", "?"),
            "is_malicious": entry["meta"].get("is_malicious", "?"),
            "combined_score": combined,
        })

    results.sort(key=lambda r: r["combined_score"], reverse=True)


    print(f"\n=== Analysis of: {kit_path} ===\n")
    print(f"Found files: {sorted(query_files.keys())}\n")
    print(f"Top {TOP_N} most similar in the reference corpus:")
    for r in results[:TOP_N]:
        print(f"  {r['combined_score']:.3f}  {r['kit_id']:30}  familia={r['family']:15}  malicioso={r['is_malicious']}")

    top_families = [r["family"] for r in results[:TOP_N]]
    predicted_family = max(set(top_families), key=top_families.count)
    votes = top_families.count(predicted_family)

    malicious_scores = [r["combined_score"] for r in results if r["is_malicious"] == "True"]
    benign_scores = [r["combined_score"] for r in results if r["is_malicious"] == "False"]

    if not malicious_scores or not benign_scores:
        verdict = "NOT ENOUGH DATA (corpus lacks references for one of the classes)"
        avg_malicious = sum(malicious_scores) / len(malicious_scores) if malicious_scores else None
        avg_benign = sum(benign_scores) / len(benign_scores) if benign_scores else None
    else:
        avg_malicious = sum(malicious_scores) / len(malicious_scores)
        avg_benign = sum(benign_scores) / len(benign_scores)
        verdict = "MALICIOUS" if avg_malicious > avg_benign else "BENIGN"

    print(f"\nMost probable family: {predicted_family}  ({votes}/{TOP_N} neighbours match)")
    print(f"Veredict: {verdict}")
    mal_str = f"{avg_malicious:.3f}" if avg_malicious is not None else "no data"
    ben_str = f"{avg_benign:.3f}" if avg_benign is not None else "no data"
    print(f"  average similarity to malicious references: {mal_str}")
    print(f"  average similarity to benign references:    {ben_str}")

    print(f"\nSignas detected in this kit:")
    for line in explain(query_features):
        print(line)

    classifier_bundle = load_classifier()
    if classifier_bundle:
        from train_classifier import to_vector
        vector = [to_vector(query_features)]
        model = classifier_bundle["model"]
        proba = model.predict_proba(vector)[0] #proba[1] = malicious probability
        print(f"\nTrained classifier says:")
        print(f"Malicious probability: {proba[1]:.2f}")
    else:
        print(f"\nNo trained classifier yet: run train_classifier.py for a second opinion.")

    print(f"\nReference corpus: {len(corpus)} kits.")
    print(" The veredict is as good as the reference (see README).")


def main():
    parser = argparse.ArgumentParser(description="Analyzes a suspicious kit against the reference corpus.")
    parser.add_argument("kit_path", help="Directory holding to-be-analyzed kit files.")
    args = parser.parse_args()
    analyze(args.kit_path)


if __name__ == "__main__":
    main()