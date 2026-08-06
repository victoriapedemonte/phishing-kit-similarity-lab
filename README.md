# phishing-kit-similarity-lab

A defensive-research project that studies how phishing kits
reuse code. Given a captured kit, it tells you how similar it
is to known kits, what family it likely belongs to, and whether
it looks malicious at all.

> **This repository contains no real phishing kits, stolen credentials,
> live phishing URLs, or working credential-collection code.** All kits
> are synthetic, use fictional brands and point to
> `example.invalid`, a domain reserved by RFC 2606 that never
> resolves. See [ETHICS.md](ETHICS.md).


## What this is, and how it fits together

This is a small pipeline: 

| Script | Question it answers | Needs |
|---|---|---|
| `generate_dataset.py` | (demo data) build a labeled synthetic corpus | nothing |
| `extract_features.py` | what does this kit's structure look like? | any kit files |
| `compute_similarity.py` | how well does the method work? | a labeled corpus |
| `analyze_kit.py` | **what is this one kit I just found?** | a labeled reference corpus |
| `cluster_kits.py` | which of these many kits are copies of each other? | any batch, no labels needed |
| `train_classifier.py` | train a fast, reusable classifier | a labeled corpus |

`analyze_kit.py` is the actual entry point for the real use case
(one new suspicious kit in, an answer out).

## Quick use

```bash
pip install -r requirements.txt
cd src

python3 generate_dataset.py        # build the synthetic reference corpus
python3 extract_features.py        # fingerprint every kit
python3 compute_similarity.py      # validate: does similarity separate families?
python3 cluster_kits.py            # discover structure
python3 train_classifier.py        # train the reusable classifier
python3 analyze_kit.py /path/to/a/suspicious/kit   # the real "what is this?" 
```

## Bringing your own data

To add your own kits:

1. Create `datasets/<your_source_name>/<family_name>/<kit_id>/` per
   kit, with its files inside as plain text (see `ETHICS.md` for why
   ours use a `.txt` suffix on anything that would normally be `.php`).
2. Optional, but needed for `analyze_kit.py` / `train_classifier.py`
   to use it as a reference: add
   `datasets/<your_source_name>/ground_truth.csv` with columns
   `kit_id, family, origin_seed, is_malicious`. Without it,
   `extract_features.py` / `compute_similarity.py` still run fine —
   you just lose the family/malicious validation reporting for that
   source.
3. Run `extract_features.py` and `compute_similarity.py` as usual —
   they process every source under `datasets/`.


## Why the kits look the way they do

Real phishing kits have a recognizable static shape, the same way a
malware binary has sections, imports, and packer artifacts. Before
generating data, this project maps that shape explicitly:

| Binary analysis concept | Phishing kit equivalent | 
|---|---|
| Exact + fuzzy file hash | SHA256 / ssdeep / TLSH per file & per kit | 
| Section table | File/folder layout: `config.php` vs `process.php`, `antibot/`, `.htaccess` |
| Imports / API calls | Hardcoded exfil destination (bot token, webhook, email) | 
| Packer / high-entropy sections | Base64-looking blobs, `eval()`-style patterns | 
| Anti-debug / anti-sandbox | Antibot folder, `.htaccess` visitor filtering | 
| Debug strings / compiler artifacts | Kit "signature" comment (`// kit build: ...`) | 

This is what the mutation engine actually varies not just cosmetic
noise, but the same categories a real analyst would fingerprint.

## Synthetic Data Generation

We use a small **mutation engine** (`src/mutation_engine/`) that takes
one seed kit per family and applies a random-but-reproducible combination 
of 11 transformations to generate realistic variants.

Three families are generated:

| Family | Seed | Simulates |
|---|---|---|
| `family_alpha` | fake webmail login (NimbusBox), no antibot layer | a "cheap" kit and its resold copies |
| `family_beta`  | fake bank login (Northwind Bank), **has** `antibot/` + `.htaccess` | a more "sophisticated" kit — unrelated to alpha |
| `family_gamma` | **derived from `family_alpha`** at high mutation intensity | a heavily modified copy — tests whether similarity detection can still trace it back to alpha |

Every generated kit is tracked in `datasets/synthetic/ground_truth.csv`
and `detailed_manifest.json`, so later phases can be objectively scored.

```bash
python3 generate_dataset.py --num-variants 6
```

This (re)generates everything under `datasets/synthetic/<family>/`
(deterministic: same command always produces byte-identical output).


## Feature Extraction

We turn each generated kit into a structured `features.json`
fingerprint, using the same categories mapped in the table above:

- **`src/feature_extraction/features.py`**: parses each kit
  and extracts 7 feature groups: file manifest, form fields, 
  exfiltration indicators, link/navigation richness, obfuscation 
  indicators, evasion indicators, and branding/signature.
- **`src/extract_features.py`**: runs the extractor over every source
  under `datasets/` and writes `features.json` and `features_summary.csv`.

```bash
python3 extract_features.py
```

## Similarity & Querying

- **`src/compute_similarity.py`**: validates the reference corpus:
  computes pairwise similarity between every kit, combining an
  ssdeep + TLSH + a dependency-free shingling method (code-level)
  with feature similarity (semantic-level). Writes `similarity_matrix.csv`
  and, when ground truth is available, reports how well the score separates same-family from unrelated pairs.
- **`src/analyze_kit.py`**: analyzes one new, unlabeled kit against the
  labeled reference corpus: nearest neighbors, most likely family, a
  malicious/benign verdict, and a checklist of which specific indicators 
  were detected.

```bash
python3 compute_similarity.py
python3 analyze_kit.py /path/to/a/kit
```
**A note on the verdict:** it's nearest-neighbor based by default, only
as good as the reference corpus, and only supplemented (not replaced)
by the trained classifier below if one exists.


## Clustering & a Trainable Classifier

- **`src/cluster_kits.py`**: given a *batch* of kits with no prior
  labels, groups them with DBSCAN over a precomputed distance matrix.
  Answers "which of these are copies of each other?".
- **`src/train_classifier.py`**: trains a Random Forest on the
  extracted features (excluding free-text fields) and saves it to `models/classifier.joblib`. Reports accuracy **against a naive majority-class baseline**. `analyze_kit.py` loads the model automatically if present,
  as a second opinion.

```bash
python3 cluster_kits.py
python3 train_classifier.py
python3 analyze_kit.py /path/to/a/kit
```