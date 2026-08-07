"""
build_similarity_graph.py

Each kit is a node in a graph. An edge joins them if their combined
similarity exceeds a threshold.
It colors nodes by family (ground truth).

Use:
    python3 build_similarity_graph.py
    python3 build_similarity_graph.py --threshold 0.6
"""

import argparse
import itertools
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from corpus_utils import collect_kits, discover_dataset_dirs, load_ground_truth
from feature_extraction.features import extract_all_features
from similarity.feature_similarity import feature_similarity
from similarity.fuzzy_hash import compare_fingerprints, compute_kit_fingerprint, kit_blob

NOISY_FEATURE_KEYS = {"exfil_indicators.config_placeholder_values"}

FAMILY_COLORS = {
    "family_alpha": "#96add3",
    "family_beta": "#e98de0",
    "family_gamma": "#d497ea",
    "family_benign": "#b3eabf",
}
DEFAULT_COLOR = "#999999"


def compute_pairwise_scores(kits):
    kit_ids = sorted(kits)
    features = {kid: extract_all_features(kits[kid]) for kid in kit_ids}
    fingerprints = {
        kid: compute_kit_fingerprint(kit_blob(kits[kid], exclude_logical_names={"config.php"}))
        for kid in kit_ids
    }

    scores = {}
    for kit_a, kit_b in itertools.combinations(kit_ids, 2):
        engine_sim = compare_fingerprints(fingerprints[kit_a], fingerprints[kit_b])["ensemble"]
        feat_sim = feature_similarity(features[kit_a], features[kit_b], ignore_keys=NOISY_FEATURE_KEYS)
        scores[(kit_a, kit_b)] = 0.5 * engine_sim + 0.5 * feat_sim
    return scores


def build_graph(kits, ground_truth, threshold):
    graph = nx.Graph()
    for kit_id in kits:
        family = ground_truth.get(kit_id, {}).get("family", "?")
        graph.add_node(kit_id, family=family)

    for (kit_a, kit_b), combined_score in compute_pairwise_scores(kits).items():
        if combined_score >= threshold:
            graph.add_edge(kit_a, kit_b, weight=combined_score)

    return graph


def draw_graph(graph, out_path, title):
    plt.figure(figsize=(12, 9))
    pos = nx.spring_layout(graph, seed=42, k=0.6)

    node_colors = [FAMILY_COLORS.get(graph.nodes[n]["family"], DEFAULT_COLOR) for n in graph.nodes]
    node_sizes = [300 + 120 * graph.degree(n) for n in graph.nodes]
    edge_widths = [1 + 3 * graph[u][v]["weight"] for u, v in graph.edges]

    nx.draw_networkx_edges(graph, pos, width=edge_widths, alpha=0.4, edge_color="#888888")
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_sizes,
                            edgecolors="white", linewidths=1.5)
    nx.draw_networkx_labels(graph, pos, font_size=7, font_color="black")

    families_present = sorted({graph.nodes[n]["family"] for n in graph.nodes})
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label=fam,
                    markerfacecolor=FAMILY_COLORS.get(fam, DEFAULT_COLOR), markersize=10)
        for fam in families_present
    ]
    plt.legend(handles=legend_handles, loc="upper left", title="Family (ground truth)")
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Generates a similarity graph between kits.")
    parser.add_argument("--threshold", type=float, default=0.6,
                         help="Minimum combined similarity to draw an edge between two kits (0-1).")
    args = parser.parse_args()

    for dataset_dir in discover_dataset_dirs():
        kits = collect_kits(dataset_dir)
        if len(kits) < 2:
            continue

        ground_truth = load_ground_truth(dataset_dir)
        graph = build_graph(kits, ground_truth, args.threshold)

        source_name = os.path.basename(dataset_dir)
        out_path = os.path.join(dataset_dir, "similarity_graph.png")
        draw_graph(graph, out_path, f"Similarity graph - {source_name} (threshold={args.threshold})")

        isolated = list(nx.isolates(graph))
        print(f"[{source_name}] Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        if isolated:
            print(f"No connections (isolated): {isolated}")
        print(f"  -> {out_path}")


if __name__ == "__main__":
    main()