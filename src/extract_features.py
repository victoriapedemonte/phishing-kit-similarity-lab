"""
extract_features.py

It iterates over each kit in datasets/synthetic, extracts
features using features.py and saves:

  - datasets/synthetic/features.json -> complete dict kit_id -> features
  - datasets/synthetic/features_summary.csv -> flattened summary suitable for pandas, excel, etc.

Use:
    cd src
    python3 extract_features.py
"""

import csv
import json
import os

from corpus_utils import DATASETS_ROOT, collect_kits, discover_dataset_dirs
from feature_extraction.features import extract_all_features


def flatten(d, prefix=""):
    """
    Flattens a nested dict into a single-level dict with dotted keys.
    """
    flat = {}
    for key, value in d.items():
        full_key = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, prefix=f"{full_key}."))
        elif isinstance(value, list):
            flat[full_key] = ";".join(str(v) for v in value)
        else:
            flat[full_key] = value
    return flat


def write_output(dataset_dir, all_features):
    features_path = os.path.join(dataset_dir, "features.json")
    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(all_features, f, indent=2, ensure_ascii=False)

    rows, columns = [], set()
    for kit_id, feats in all_features.items():
        row = {"kit_id": kit_id}
        row.update(flatten(feats))
        rows.append(row)
        columns.update(row.keys())

    csv_path = os.path.join(dataset_dir, "features_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["kit_id"] + sorted(columns - {"kit_id"}))
        writer.writeheader()
        writer.writerows(rows)

    return features_path, csv_path


def main():
    dataset_dirs = discover_dataset_dirs()
    if not dataset_dirs:
        print(f"No directory found in {DATASETS_ROOT}")
        return

    for dataset_dir in dataset_dirs:
        kits = collect_kits(dataset_dir)
        if not kits:
            continue
        all_features = {kid: extract_all_features(files) for kid, files in kits.items()}
        features_path, csv_path = write_output(dataset_dir, all_features)
        source_name = os.path.basename(dataset_dir)
        print(f"[{source_name}] Features extracted from {len(all_features)} kits.")
        print(f"  -> {features_path}")
        print(f"  -> {csv_path}")


if __name__ == "__main__":
    main()