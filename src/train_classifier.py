"""
train_classifier.py

Trains a random forest classifier on the extracted features, using the
ground_truth.csv label is_malicious. Saves the model to 
models/classifier.joblib so analyze_kit.py can load it.

Important: this is a toy example with a small dataset.
The model is not reliable for real-world use. It should be re-trained
with a larger corpus.

Use:
    cd src
    python3 train_classifier.py
"""

import os

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneOut, cross_val_score

from corpus_utils import ROOT_DIR, collect_kits, discover_dataset_dirs, flatten_features, load_ground_truth
from feature_extraction.features import extract_all_features

FEATURE_COLUMNS = [
    "file_manifest.num_files",
    "file_manifest.has_config_engine_split",
    "form_features.num_forms",
    "form_features.num_inputs",
    "form_features.has_password_field",
    "form_features.has_otp_field",
    "form_features.has_card_field",
    "form_features.has_hidden_fields",
    "form_features.has_checkbox_field",
    "exfil_indicators.is_external_action",
    "exfil_indicators.has_empty_or_blank_action",
    "exfil_indicators.has_fixed_backdoor_pattern",
    "link_indicators.num_links",
    "link_indicators.has_navigation_links",
    "obfuscation_indicators.has_base64_blob",
    "obfuscation_indicators.comment_density",
    "evasion_indicators.has_antibot_folder",
    "evasion_indicators.has_htaccess",
]

MODEL_PATH = os.path.join(ROOT_DIR, "models", "classifier.joblib")

def to_vector(features):
    flat = flatten_features(features)
    vector = []
    for col in FEATURE_COLUMNS:
        value = flat.get(col, 0)
        vector.append(float(value) if isinstance(value, bool) else float(value or 0))
    return vector


def load_training_data():
    X, y = [], []
    for dataset_dir in discover_dataset_dirs():
        ground_truth = load_ground_truth(dataset_dir)
        if not ground_truth:
            continue
        for kit_id, files in collect_kits(dataset_dir).items():
            meta = ground_truth.get(kit_id)
            if not meta:
                continue
            X.append(to_vector(extract_all_features(files)))
            y.append(1 if meta["is_malicious"] == "True" else 0)
    return X, y


def main():
    X, y = load_training_data()
    n_malicious, n_benign = sum(y), len(y) - sum(y)
    print(f"Training data: {len(y)} kits ({n_malicious} malicious, {n_benign} benign)")

    if n_benign < 2 or n_malicious < 2:
        print("\nWARNING: with less than 2 examples of any class, no metric below is representative.")
        print(" They just confirm that the pipeline works. \n")

    clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    clf.fit(X, y)

    baseline = max(n_malicious, n_benign) / len(y)
    print(f"Baseline (always predicts the dominating class): {baseline:.3f}")

    if len(set(y)) > 1 and len(y) > 3:
        scores = cross_val_score(clf, X, y, cv=LeaveOneOut())
        loo_accuracy = scores.mean()
        print(f"Leave-one-out Accuracy: {loo_accuracy:.3f}")
        margin = loo_accuracy - baseline
        if margin < 0.05:
            print(f"  -> Barely {margin:+.3f} over baseline: model is not learning.")
        else:
            print(f"  -> {margin:+.3f} over baseline: model has learnt.")

    print("\nEach feature's importance (weights):")
    ranked = sorted(zip(FEATURE_COLUMNS, clf.feature_importances_), key=lambda x: -x[1])
    for name, importance in ranked[:10]:
        print(f"  {importance:.3f}  {name}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": clf, "feature_columns": FEATURE_COLUMNS}, MODEL_PATH)
    print(f"\nModel saved in: {MODEL_PATH}")
    print("(analyze_kit.py uses it automatically to classify)")


if __name__ == "__main__":
    main()