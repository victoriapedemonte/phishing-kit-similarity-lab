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

from feature_extraction.features import extract_all_features

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)
DATASETS_ROOT = os.path.join(ROOT_DIR, "datasets")
SKIP_SUBDIRS = {"seeds"}
IGNORED_FILENAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def discover_dataset_dirs():
    if not os.path.isdir(DATASETS_ROOT):
        return []
    return [
        os.path.join(DATASETS_ROOT, name)
        for name in sorted(os.listdir(DATASETS_ROOT))
        if os.path.isdir(os.path.join(DATASETS_ROOT, name))
    ]


def load_kit_files(kit_dir):
    files = {}
    for root, _dirs, filenames in os.walk(kit_dir):
        for fname in sorted(filenames):
            if fname in IGNORED_FILENAMES:
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, kit_dir).replace(os.sep, "/")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    files[rel_path] = f.read()
            except UnicodeDecodeError:
                print(f"  (omitido, no es texto UTF-8: {rel_path})")
    return files


def flatten(d, prefix=""):
    """
    It flattens a nested dictionary into a single level dict with dot-separated keys.
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


def extract_features_for_dataset(dataset_dir):
    all_features = {}
    for family in sorted(os.listdir(dataset_dir)):
        family_dir = os.path.join(dataset_dir, family)
        if not os.path.isdir(family_dir) or family in SKIP_SUBDIRS:
            continue
        for kit_id in sorted(os.listdir(family_dir)):
            kit_dir = os.path.join(family_dir, kit_id)
            if not os.path.isdir(kit_dir):
                continue
            files = load_kit_files(kit_dir)
            all_features[f"{family}/{kit_id}"] = extract_all_features(files)
    return all_features


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
        all_features = extract_features_for_dataset(dataset_dir)
        if not all_features:
            continue
        features_path, csv_path = write_output(dataset_dir, all_features)
        source_name = os.path.basename(dataset_dir)
        print(f"[{source_name}] Features extracted from {len(all_features)} kits.")
        print(f"  -> {features_path}")
        print(f"  -> {csv_path}")


if __name__ == "__main__":
    main()