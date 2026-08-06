"""
corpus_utils.py

Shared utilities for traversing datasets/. Used by both the scripts that
process the whole corpus and analyze_kit.py, which queries the corupus for 
a single new kit.
"""

import csv
import os

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


def load_ground_truth(dataset_dir):
    gt_path = os.path.join(dataset_dir, "ground_truth.csv")
    if not os.path.exists(gt_path):
        return {}
    with open(gt_path, encoding="utf-8") as f:
        return {row["kit_id"]: row for row in csv.DictReader(f)}


def collect_kits(dataset_dir):
    kits = {}
    for family in sorted(os.listdir(dataset_dir)):
        family_dir = os.path.join(dataset_dir, family)
        if not os.path.isdir(family_dir) or family in SKIP_SUBDIRS:
            continue
        for kit_id in sorted(os.listdir(family_dir)):
            kit_dir = os.path.join(family_dir, kit_id)
            if not os.path.isdir(kit_dir):
                continue
            files = load_kit_files(kit_dir)
            if files:
                kits[f"{family}/{kit_id}"] = files
    return kits


def flatten_features(d, prefix=""):
    """
    Flattens a nested dict into a single-level dict with dotted keys.
    """
    flat = {}
    for key, value in d.items():
        full_key = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten_features(value, prefix=f"{full_key}."))
        else:
            flat[full_key] = value
    return flat