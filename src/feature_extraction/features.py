"""
features.py

Extracts, for a kit already loaded in memory, the 6 categories of features
we defined in the README: file_manifest, form_features, exfil_indicators,
obfuscation_indicators, evasion_indicators, branding_indicators.

Designed to work both on our synthetic kits and on a real kit.

Nothing is executed, only text is read.
"""

import re

from bs4 import BeautifulSoup

BASE64_BLOB_PATTERN = re.compile(r'"[A-Za-z0-9+/]{40,}={0,2}"')
PLACEHOLDER_VALUE_PATTERN = re.compile(r'"([A-Za-z0-9_./:-]*PLACEHOLDER[A-Za-z0-9_./:-]*)"')
RANDOMIZABLE_PLACEHOLDER_PATTERN = re.compile(r"PLACEHOLDER_\d+")
SIGNATURE_PATTERN = re.compile(
    r"(?:kit build|coded by|hacked by|made by|developed by|author|credits?)"
    r"\s*:?\s*(.+)",
    re.IGNORECASE,)

def logical_filename(rel_path):
    """
    Translates .php.txt suffixes back to .php.
    Also translates .htaccess.txt to .htaccess.
    """
    name = rel_path.split("/")[-1]
    if name.endswith(".php.txt"):
        return name[: -len(".txt")]
    if name == ".htaccess.txt":
        return ".htaccess"
    return name


def _find_file(files, logical_name):
    for rel_path, content in files.items():
        if logical_filename(rel_path) == logical_name:
            return content
    return None


def extract_file_manifest(files):
    file_list = sorted(files.keys())
    has_config = _find_file(files, "config.php") is not None
    has_process = _find_file(files, "process.php") is not None
    return {
        "files": file_list,
        "num_files": len(file_list),
        "has_config_engine_split": has_config and has_process,
    }


def extract_form_features(files):
    """
    Extracts features related to forms and input fields 
    from de HTML content of the kit.
    """
    html = files.get("index.html", "")
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    inputs = soup.find_all("input")

    field_types = sorted({inp.get("type", "text") for inp in inputs})
    field_names = sorted({inp.get("name") for inp in inputs if inp.get("name")})

    def name_has(*keywords):
        return any(k in (n or "").lower() for n in field_names for k in keywords)

    return {
        "num_forms": len(forms),
        "num_inputs": len(inputs),
        "field_types": field_types,
        "field_names": field_names,
        "has_password_field": name_has("pass"),
        "has_otp_field": name_has("otp", "code", "verif"),
        "has_card_field": name_has("card", "cc_number", "cvv"),
        "has_hidden_fields": any(inp.get("type") == "hidden" for inp in inputs),
        "has_checkbox_field": any(inp.get("type") == "checkbox" for inp in inputs),
    }


def extract_exfil_indicators(files):
    """
    Extracts features related to exfiltration of data.
    """
    html = files.get("index.html", "")
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form")
    action_domain = None
    if form and form.get("action"):
        m = re.search(r"://([^/]+)", form["action"])
        if m:
            action_domain = m.group(1)

    config_content = _find_file(files, "config.php") or ""
    values = PLACEHOLDER_VALUE_PATTERN.findall(config_content)
    has_backdoor = any(not RANDOMIZABLE_PLACEHOLDER_PATTERN.search(v) for v in values)

    # SFH vacío o about:blank: señal kit malicioso.
    raw_action = form.get("action") if form else None
    is_empty_action = raw_action in (None, "", "#", "about:blank")

    return {
        "form_action_domain": action_domain,
        "is_external_action": bool(action_domain),
        "has_empty_or_blank_action": is_empty_action,
        "config_placeholder_values": values,
        "has_fixed_backdoor_pattern": has_backdoor,
    }

def extract_link_indicators(files):
    """
    Category to distinguish phishing from benign.
    """
    html = files.get("index.html", "")
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    non_empty = [a for a in links if a.get("href") and a.get("href") not in ("#", "")]
    return {
        "num_links": len(links),
        "num_non_empty_links": len(non_empty),
        "has_navigation_links": len(non_empty) >= 2,
    }

def extract_obfuscation_indicators(files):
    process_content = _find_file(files, "process.php") or ""
    blobs = BASE64_BLOB_PATTERN.findall(process_content)
    longest = max((len(b) for b in blobs), default=0)

    lines = [ln for ln in process_content.split("\n") if ln.strip()]
    comment_lines = [ln for ln in lines if ln.strip().startswith(("//", "#"))]
    density = round(len(comment_lines) / len(lines), 2) if lines else 0.0

    return {
        "has_base64_blob": longest > 0,
        "longest_base64_run": longest,
        "comment_density": density,
    }


def extract_evasion_indicators(files):
    has_antibot = any(rel.split("/")[0] == "antibot" for rel in files if "/" in rel)
    has_htaccess = _find_file(files, ".htaccess") is not None
    return {"has_antibot_folder": has_antibot, "has_htaccess": has_htaccess}


def extract_branding_indicators(files):
    process_content = _find_file(files, "process.php") or ""
    sig_match = SIGNATURE_PATTERN.search(process_content)

    html = files.get("index.html", "")
    soup = BeautifulSoup(html, "html.parser")
    brand = None
    if soup.title and soup.title.string:
        brand = soup.title.string.split(" - ")[0].strip()

    return {
        "kit_signature": sig_match.group(1).strip() if sig_match else None,
        "brand_name_detected": brand,
    }


def extract_all_features(files):
    """
    Unique entry point: dict of files -> dict of features.
    """
    return {
        "file_manifest": extract_file_manifest(files),
        "form_features": extract_form_features(files),
        "exfil_indicators": extract_exfil_indicators(files),
        "link_indicators": extract_link_indicators(files),
        "obfuscation_indicators": extract_obfuscation_indicators(files),
        "evasion_indicators": extract_evasion_indicators(files),
        "branding_indicators": extract_branding_indicators(files),
    }