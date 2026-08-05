# phishing-kit-similarity-lab

A defensive-research project that studies how phishing kits
reuse code, using **fully synthetic data**. It measures similarity
between kit files (fuzzy hashing, structural features) and clusters
them into families, mirroring how real threat-intel teams track kit
reuse, resale, and attribution.

> **This repository contains no real phishing kits, stolen credentials,
> live phishing URLs, or working credential-collection code.** All kits
> are synthetic, use fictional brands and point to
> `example.invalid`, a domain reserved by RFC 2606 that never
> resolves. See [ETHICS.md](ETHICS.md).


## Why the kits look the way they do

Real phishing kits have a recognizable static "shape", the same way a
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

Instead of hand-writing kit variants one by one, a small **mutation
engine** (`src/mutation_engine/`) takes one seed kit per family and
applies a random-but-reproducible combination of 11 transformations
(renaming, reformatting, reordering, rebranding, signature mutation,
obfuscation markers...) to generate realistic variants.

Three families are generated:

| Family | Seed | Simulates |
|---|---|---|
| `family_alpha` | fake webmail login (NimbusBox), no antibot layer | a "cheap" kit and its resold copies |
| `family_beta`  | fake bank login (Northwind Bank), **has** `antibot/` + `.htaccess` | a more "sophisticated" kit — unrelated to alpha |
| `family_gamma` | **derived from `family_alpha`** at high mutation intensity | a heavily modified copy — tests whether similarity detection can still trace it back to alpha |

Two design choices worth calling out:

- **Config vs. engine split** — `config.php.txt` (the fake exfil
  destination) and `process.php.txt` (the validation "engine") are
  separate files, because in real kits the config is what changes
  between resold copies while the engine stays nearly identical.
- **`rebrand`** — swaps the visible brand name for a different
  fictional one while keeping the underlying form/JS/CSS structure.
  This is the key test case for the whole project: visual/brand
  matching would call these "different sites," but code-similarity
  should still see them as close relatives.

Every generated kit is tracked in `datasets/synthetic/ground_truth.csv`
and `detailed_manifest.json`, so later phases can be objectively scored.

## Running it

```bash
cd src
python3 generate_dataset.py --num-variants 6
```

This (re)generates everything under `datasets/synthetic/<family>/`
(deterministic: same command always produces byte-identical output).


## Feature Extraction

We turn each generated kit into a structured `features.json`
fingerprint, using the same categories mapped in the table above:

- **`src/feature_extraction/features.py`** — parses each kit
  (BeautifulSoup for HTML, regex for the rest) and extracts 6 feature
  groups: file manifest, form fields, exfiltration indicators
  (including detecting a fixed/hidden destination alongside the
  randomized one, a real backdoor pattern), obfuscation indicators,
  evasion indicators, and branding/signature.
- **`src/extract_features.py`** — runs the extractor over every kit in
  `datasets/synthetic/` and writes `features.json` (nested, for code)
  and `features_summary.csv` (flattened, for spreadsheets).

```bash
pip install -r requirements.txt
cd src
python3 extract_features.py
```
