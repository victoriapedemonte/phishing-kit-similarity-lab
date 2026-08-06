"""
cluster_kits.py

Uses DBSCAN on a batch of kits to discover clusters of similar kits.

Use:
    cd src
    python3 cluster_kits.py
    python3 cluster_kits.py --eps 0.35 --min-samples 2
"""

import argparse
import csv
import os

from sklearn.cluster import DBSCAN
from sklearn.metrics import adjusted_rand_score

from corpus_utils import collect_kits, discover_dataset_dirs, load_ground_truth
from feature_extraction.features import extract_all_features
from similarity.feature_similarity import feature_similarity
from similarity.fuzzy_hash import compare_fingerprints, compute_kit_fingerprint, kit_blob

NOISY_FEATURE_KEYS = {"exfil_indicators.config_placeholder_values"}


def build_distance_matrix(kits):
    kit_ids = sorted(kits)
    features = {kid: extract_all_features(kits[kid]) for kid in kit_ids}
    fingerprints = {
        kid: compute_kit_fingerprint(kit_blob(kits[kid], exclude_logical_names={"config.php"}))
        for kid in kit_ids
    }

    n = len(kit_ids)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            engine_sim = compare_fingerprints(fingerprints[kit_ids[i]], fingerprints[kit_ids[j]])["ensemble"]
            feat_sim = feature_similarity(
                features[kit_ids[i]], features[kit_ids[j]], ignore_keys=NOISY_FEATURE_KEYS
            )
            distance = 1.0 - (0.5 * engine_sim + 0.5 * feat_sim)
            matrix[i][j] = matrix[j][i] = distance
    return kit_ids, matrix


def main():
    parser = argparse.ArgumentParser(description="Agrupa kits con DBSCAN, sin usar etiquetas.")
    parser.add_argument("--eps", type=float, default=0.35,
                         help="Distancia máxima para considerar dos kits 'vecinos' (0-1).")
    parser.add_argument("--min-samples", type=int, default=2,
                         help="Mínimo de kits para formar un cluster.")
    args = parser.parse_args()

    for dataset_dir in discover_dataset_dirs():
        kits = collect_kits(dataset_dir)
        if len(kits) < 2:
            continue

        kit_ids, matrix = build_distance_matrix(kits)
        labels = DBSCAN(eps=args.eps, min_samples=args.min_samples, metric="precomputed").fit_predict(matrix)

        source_name = os.path.basename(dataset_dir)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        print(f"\n[{source_name}] {len(kit_ids)} kits -> {n_clusters} clusters, {n_noise} sin agrupar (ruido)")

        for cluster_id in sorted(set(labels)):
            members = [kit_ids[i] for i, l in enumerate(labels) if l == cluster_id]
            label_name = "RUIDO (sin grupo)" if cluster_id == -1 else f"Cluster {cluster_id}"
            print(f"  {label_name}: {members}")

        out_path = os.path.join(dataset_dir, "clusters.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["kit_id", "cluster"])
            writer.writerows(zip(kit_ids, labels))
        print(f"  -> {out_path}")

        ground_truth = load_ground_truth(dataset_dir)
        if ground_truth:
            true_labels = [ground_truth.get(kid, {}).get("family", "?") for kid in kit_ids]
            ari = adjusted_rand_score(true_labels, labels)
            print(f"  Adjusted Rand Index vs. familias reales: {ari:.3f}  (1.0 = coincide perfecto, 0.0 = azar)")


if __name__ == "__main__":
    main()