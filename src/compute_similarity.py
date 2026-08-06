"""
compute_similarity.py

For each data source under datasets/, computes the similarity between
all pairs of kits, combining code similarity and feature similarity.

It writes <source>/similarity_matrix.csv and, if ground_truth.csv exists,
prints the validation check.

Use:
    cd src
    python3 compute_similarity.py
"""

import csv
import itertools
import os

from corpus_utils import DATASETS_ROOT, collect_kits, discover_dataset_dirs, load_ground_truth
from feature_extraction.features import extract_all_features
from similarity.feature_similarity import feature_similarity
from similarity.fuzzy_hash import (
    HAS_SSDEEP, HAS_TLSH, compare_fingerprints, compute_kit_fingerprint, kit_blob,
)
NOISY_FEATURE_KEYS = {"exfil_indicators.config_placeholder_values"}


def process_dataset(dataset_dir):
    kits = collect_kits(dataset_dir)
    if len(kits) < 2:
        return None

    ground_truth = load_ground_truth(dataset_dir)
    features, fp_whole, fp_engine = {}, {}, {}

    for kit_id, files in kits.items():
        features[kit_id] = extract_all_features(files)
        fp_whole[kit_id] = compute_kit_fingerprint(kit_blob(files))
        fp_engine[kit_id] = compute_kit_fingerprint(
            kit_blob(files, exclude_logical_names={"config.php"})
        )

    rows = []
    for kit_a, kit_b in itertools.combinations(sorted(kits), 2):
        whole = compare_fingerprints(fp_whole[kit_a], fp_whole[kit_b])
        engine = compare_fingerprints(fp_engine[kit_a], fp_engine[kit_b])
        feat_sim = feature_similarity(features[kit_a], features[kit_b], ignore_keys=NOISY_FEATURE_KEYS)
        combined = round(0.5 * engine["ensemble"] + 0.5 * feat_sim, 4)

        row = {
            "kit_a": kit_a,
            "kit_b": kit_b,
            "shingle_whole": round(whole["shingle"], 4),
            "shingle_engine": round(engine["shingle"], 4),
            "ssdeep_whole": whole["ssdeep"] if whole["ssdeep"] is not None else "",
            "ssdeep_engine": engine["ssdeep"] if engine["ssdeep"] is not None else "",
            "tlsh_whole": round(whole["tlsh"], 4) if whole["tlsh"] is not None else "",
            "tlsh_engine": round(engine["tlsh"], 4) if engine["tlsh"] is not None else "",
            "code_similarity_whole": round(whole["ensemble"], 4),
            "code_similarity_engine": round(engine["ensemble"], 4),
            "feature_similarity": round(feat_sim, 4),
            "combined_score": combined,
        }
        if ground_truth:
            gt_a, gt_b = ground_truth.get(kit_a, {}), ground_truth.get(kit_b, {})
            row["same_family"] = gt_a.get("family") == gt_b.get("family")
            row["same_origin_seed"] = gt_a.get("origin_seed") == gt_b.get("origin_seed")
        rows.append(row)

    return rows


def write_and_report(dataset_dir, rows):
    fieldnames = list(rows[0].keys())
    out_path = os.path.join(dataset_dir, "similarity_matrix.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    source_name = os.path.basename(dataset_dir)
    print(f"[{source_name}] {len(rows)} pairs compared -> {out_path}")

    if "same_family" not in rows[0]:
        return

    def avg(xs):
        return sum(xs) / len(xs) if xs else None

    same_family = [r["combined_score"] for r in rows if r["same_family"]]
    same_lineage = [r["combined_score"] for r in rows if not r["same_family"] and r["same_origin_seed"]]
    unrelated = [r["combined_score"] for r in rows if not r["same_family"] and not r["same_origin_seed"]]

    print(f"  Same family: {avg(same_family):.3f}  (n={len(same_family)})")
    if same_lineage:
        print(f"  Different family, same origin: {avg(same_lineage):.3f}  (n={len(same_lineage)})")
    if unrelated:
        print(f"  Unrelated (different family and origin): {avg(unrelated):.3f}  (n={len(unrelated)})")


def main():
    methods = ["shingles"]
    if HAS_SSDEEP:
        methods.append("ssdeep")
    if HAS_TLSH:
        methods.append("TLSH")
    print(f"Active fuzzy hashing methods: {', '.join(methods)}")

    found_any = False
    for dataset_dir in discover_dataset_dirs():
        rows = process_dataset(dataset_dir)
        if not rows:
            continue
        found_any = True
        write_and_report(dataset_dir, rows)
    if not found_any:
        print(f"No kits to compare found under {DATASETS_ROOT}")


if __name__ == "__main__":
    main()