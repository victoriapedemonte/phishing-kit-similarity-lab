"""
generate_dataset.py

Reads seed kits from datasets/synthetic/seeds/, generates N variants
per family with MutationEngine, writes them on datasets/synthetic/<family>/
and saves two ground truth files:

  - ground_truth.csv: summary human readable table.
  - detailed_manifest.json: full details per kit (what renaming mapping was used, what text was changed, if the signature was re-marked...).

Use:
    cd src
    python3 generate_dataset.py
    python3 generate_dataset.py --num-variants 12
"""

import argparse
import csv
import hashlib
import json
import os

from mutation_engine.engine import MutationEngine

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)
SEEDS_DIR = os.path.join(ROOT_DIR, "datasets", "synthetic", "seeds")
OUTPUT_DIR = os.path.join(ROOT_DIR, "datasets", "synthetic")

FAMILY_CONTEXT = {
    "family_alpha": {
        "identifiers": [
            "loginForm", "userEmail", "userPassword", "otpField", "submitBtn",
            "login-card", "brand-title", "notice-banner", "help-text",
        ],
        "brand_name": "NimbusBox",
        "alt_brands": ["Zephyr Mail", "Skylark Cloud", "Meridian Inbox"],
    },
    "family_beta": {
        "identifiers": [
            "loginForm", "userEmail", "userPassword", "cardNumber", "submitBtn",
            "auth-panel", "bank-title", "security-notice", "support-line",
        ],
        "brand_name": "Northwind Bank",
        "alt_brands": ["Meridian Trust", "Havenwell Bank", "Union Ridge Bank"],
    },
}

# family_gamma won't have its own seed, it will consist of mutated family_alpha kits with "heavy" intensity. 
GAMMA_SOURCE_FAMILY = "family_alpha"

def deterministic_seed(*parts):
    """
    We use hashlib to generate a deterministic seed based on the family name, source family, and kit index.
    This ensures reproducibility of the generated variants.
    """
    key = "-".join(str(p) for p in parts).encode("utf-8")
    return int(hashlib.sha256(key).hexdigest(), 16) % (2**32)


def load_seed(family):
    """Recursively reads the files of a seed (and its subfolders) and returns them as a dict ({relative_path: content})."""
    base = os.path.join(SEEDS_DIR, family)
    files = {}
    for root, _dirs, filenames in os.walk(base):
        for fname in sorted(filenames):
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, base).replace(os.sep, "/")
            with open(full_path, "r", encoding="utf-8") as f:
                files[rel_path] = f.read()
    return files


def write_kit(family, kit_id, files):
    kit_dir = os.path.join(OUTPUT_DIR, family, kit_id)
    for rel_path, content in files.items():
        full_path = os.path.join(kit_dir, *rel_path.split("/"))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)


def generate_family(family, context, num_variants, ground_truth, detailed,
                     source_family=None, intensity_plan=None):
    seed_family = source_family or family
    seed_files = load_seed(seed_family)
    engine = MutationEngine(context)

    # kit_000 = non-mutated seed, serves as a reference (distance 0).
    write_kit(family, "kit_000", seed_files)
    ground_truth.append({
        "kit_id": f"{family}/kit_000",
        "family": family,
        "origin_seed": seed_family,
        "rng_seed": "",
        "intensity": "none",
        "num_operators_applied": 0,
        "operators_applied": "",
    })
    detailed[f"{family}/kit_000"] = {"intensity": "none", "operators": []}

    if intensity_plan is None:
        pattern = ["light", "medium", "medium", "heavy"]
        intensity_plan = [pattern[i % len(pattern)] for i in range(num_variants)]

    for i in range(1, num_variants + 1):
        kit_id = f"kit_{i:03d}"
        rng_seed = deterministic_seed(family, seed_family, i)
        intensity = intensity_plan[i - 1]

        new_files, manifest = engine.generate_variant(
            seed_files, rng_seed=rng_seed, intensity=intensity
        )
        write_kit(family, kit_id, new_files)

        ground_truth.append({
            "kit_id": f"{family}/{kit_id}",
            "family": family,
            "origin_seed": seed_family,
            "rng_seed": rng_seed,
            "intensity": intensity,
            "num_operators_applied": manifest["num_operators_applied"],
            "operators_applied": ";".join(op["operator"] for op in manifest["operators"]),
        })
        detailed[f"{family}/{kit_id}"] = manifest


def main():
    parser = argparse.ArgumentParser(description="Genera el dataset sintético de la Fase 1.")
    parser.add_argument("--num-variants", type=int, default=6,
                         help="Variantes mutadas por familia (además de kit_000).")
    args = parser.parse_args()

    ground_truth = []
    detailed = {}

    generate_family("family_alpha", FAMILY_CONTEXT["family_alpha"],
                     args.num_variants, ground_truth, detailed)
    generate_family("family_beta", FAMILY_CONTEXT["family_beta"],
                     args.num_variants, ground_truth, detailed)
    generate_family("family_gamma", FAMILY_CONTEXT["family_alpha"],
                     args.num_variants, ground_truth, detailed,
                     source_family=GAMMA_SOURCE_FAMILY,
                     intensity_plan=["heavy"] * args.num_variants)

    gt_path = os.path.join(OUTPUT_DIR, "ground_truth.csv")
    with open(gt_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "kit_id", "family", "origin_seed", "rng_seed",
            "intensity", "num_operators_applied", "operators_applied",
        ])
        writer.writeheader()
        writer.writerows(ground_truth)

    manifest_path = os.path.join(OUTPUT_DIR, "detailed_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(detailed, f, indent=2, ensure_ascii=False)

    print(f"Generados {len(ground_truth)} kits en total.")
    print(f"  -> {gt_path}")
    print(f"  -> {manifest_path}")


if __name__ == "__main__":
    main()