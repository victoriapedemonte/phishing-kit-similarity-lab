"""
operators.py

Each function in this module is a "mutation operator": it recieves the files of a kit (as a dict 
relative_path -> text), a pre-created random.Random and a `context` with family-specific data. All 
of them return (new_files, metadata), and all of them share the same signature (files, rng, context)
even if not all of them use `context`.
"""

import base64
import re


# ---------------------------------------------------------------------------
# Vocabulary and constants used by multiple operators
# ---------------------------------------------------------------------------

WORD_BANK = [
    "nova", "orion", "lynx", "atlas", "delta", "quokka", "ember", "flux",
    "vela", "onyx", "quill", "birch", "cobalt", "drift", "haze", "iris",
]

JUNK_COMMENTS_HTML = [
    "<!-- v1.2 -->",
    "<!-- actualizado -->",
    "<!-- build 2024 -->",
    "<!-- ok -->",
]
JUNK_COMMENTS_CSS = [
    "/* reset */",
    "/* ajuste visual */",
    "/* TODO revisar */",
]
JUNK_COMMENTS_JS = [
    "// TODO limpiar",
    "// revisado",
    "// v2",
]

TEXT_VARIANTS = {
    "Iniciar sesión": ["Acceder", "Entrar a tu cuenta", "Iniciar sesión ahora"],
    "Correo electrónico": ["Email", "Dirección de correo", "Correo electrónico"],
    "Contraseña": ["Clave de acceso", "Password", "Contraseña"],
    "Código de verificación": ["Código OTP", "Código de un solo uso", "Código de verificación"],
    "Recordarme": ["Recordarme", "Mantener la sesión iniciada"],
}

SIGNATURE_ALT_TAGS = ["resold_by_ghost", "cracked_v2", "clean_build", "repack_x"]


def _consistent_word_boundary_replace(text, mapping):
    """
    Substitutes all occurrences of the keys in `mapping` in `text`, 
    respecting word boundaries (\\b), in a single pass with a combined pattern.
    """
    if not mapping:
        return text
    keys = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b")
    return pattern.sub(lambda m: mapping[m.group(1)], text)


# ---------------------------------------------------------------------------
# Mutation operators
# ---------------------------------------------------------------------------


def op_add_optional_field(files, rng, context):
    """
    With 50% probability, adds a NON-essential field to the form (checkbox 'Remember me') 
    just before the submit button. Simulates that some variants of the same kit include 
    minor fields that others do not, without touching the real goal (stealing credentials).
    """
    if "index.html" not in files or rng.random() >= 0.5:
        return dict(files), {"operator": "add_optional_field", "applied": False}

    content = files["index.html"]
    if "rememberMe" in content:
        return dict(files), {"operator": "add_optional_field", "applied": False}

    snippet = '      <label><input type="checkbox" id="rememberMe"> Recordarme</label>\n'
    new_content, n = re.subn(
        r'([ \t]*<button type=["\']submit["\'])', snippet + r"\1", content, count=1,
    )
    if n == 0:
        return dict(files), {"operator": "add_optional_field", "applied": False}

    new_files = dict(files)
    new_files["index.html"] = new_content
    return new_files, {"operator": "add_optional_field", "applied": True}


def op_reorder_css_rules(files, rng, context):
    """
    Changes the order of CSS rules, which are independent in our seed stylesheets.
    The visual result is the same, while the file changes byte by byte.
    """
    if "style.css" not in files:
        return dict(files), {"operator": "reorder_css_rules", "applied": False}

    css = files["style.css"]
    blocks = [b.strip() for b in css.split("}") if b.strip()]
    blocks = [b + "\n}" for b in blocks]
    if len(blocks) < 2:
        return dict(files), {"operator": "reorder_css_rules", "applied": False}

    order = list(range(len(blocks)))
    rng.shuffle(order)
    new_css = "\n\n".join(blocks[i] for i in order) + "\n"

    new_files = dict(files)
    new_files["style.css"] = new_css
    return new_files, {"operator": "reorder_css_rules", "applied": True, "order": order}


def op_randomize_config_destination(files, rng, context):
    """
    Changes the numeric suffix of the fake destination in config.php.txt.
    Simulates that each resale of a real kit usually has its own exfiltration destination.
    """
    if "config.php.txt" not in files:
        return dict(files), {"operator": "randomize_config_destination", "applied": False}

    new_suffix = f"{rng.randint(0, 9999):04d}"
    content, n = re.subn(r"PLACEHOLDER_\d+", f"PLACEHOLDER_{new_suffix}", files["config.php.txt"])

    new_files = dict(files)
    new_files["config.php.txt"] = content
    return new_files, {
        "operator": "randomize_config_destination",
        "applied": n > 0,
        "new_suffix": new_suffix if n > 0 else None,
    }


def op_mutate_signature(files, rng, context):
    """
    Simulates what happens to the signature that some kit authors leave in the code.
    Sometimes it survives intact in resold copies, whilst others remove it or replace it.
    """
    if "process.php.txt" not in files:
        return dict(files), {"operator": "mutate_signature", "action": "skipped"}

    content = files["process.php.txt"]
    if not re.search(r"// kit build: .*", content):
        return dict(files), {"operator": "mutate_signature", "action": "not_found"}

    action = rng.choice(["keep", "strip", "replace"])
    if action == "strip":
        content = re.sub(r"\n?// kit build: .*", "", content)
    elif action == "replace":
        new_tag = rng.choice(SIGNATURE_ALT_TAGS)
        content = re.sub(r"// kit build: .*", f"// kit build: {new_tag}", content)
    # action == "keep" -> we don't change the content, just return it as is

    new_files = dict(files)
    new_files["process.php.txt"] = content
    return new_files, {"operator": "mutate_signature", "action": action}


def op_vary_visible_text(files, rng, context):
    """
    Replaces visible text (such as labels, buttons, warnings) with an equivalent variant.
    Simulates that two kits of the same family don't necessarily share the same wording, although the form structure is the same.
    """
    changes = []
    new_files = {}
    for name, content in files.items():
        if not name.endswith(".html"):
            new_files[name] = content
            continue
        for original, variants in TEXT_VARIANTS.items():
            if original in content:
                choice = rng.choice(variants)
                if choice != original:
                    content = content.replace(original, choice)
                    changes.append(f"{original} -> {choice}")
        new_files[name] = content
    return new_files, {"operator": "vary_visible_text", "changes": changes}


def op_rebrand(files, rng, context):
    """
    Substitutes the visible brand name with a different fictitious alternative,
    simulating that someone reskins the kit to resell it under a different appearance.
    """
    brand = context.get("brand_name")
    alternatives = context.get("alt_brands") or []
    if not brand or not alternatives or "index.html" not in files:
        return dict(files), {"operator": "rebrand", "applied": False}

    new_brand = rng.choice(alternatives)
    new_files = dict(files)
    new_files["index.html"] = files["index.html"].replace(brand, new_brand)
    return new_files, {"operator": "rebrand", "applied": True, "new_brand": new_brand}


def op_rename_identifiers(files, rng, context):
    """
    Consistently renames (same new name across code files) a subset of identifiers or class names in the kit.
    Simulates what happens when someone reuses a kit: variable and class names are changed, while keeping the logic intact.
    """
    identifiers = context.get("identifiers") or []
    if not identifiers:
        return dict(files), {"operator": "rename_identifiers", "mapping": {}}

    chosen = rng.sample(identifiers, k=rng.randint(1, len(identifiers)))
    mapping = {}
    used = set()
    for old_name in chosen:
        while True:
            candidate = f"{rng.choice(WORD_BANK)}{rng.randint(1, 99)}"
            if candidate not in used:
                used.add(candidate)
                break
        mapping[old_name] = candidate

    new_files = {
        name: _consistent_word_boundary_replace(content, mapping)
        for name, content in files.items()
    }
    return new_files, {"operator": "rename_identifiers", "mapping": mapping}


def op_inject_obfuscation_marker(files, rng, context):
    """
    With 50% probability, adds a line that looks like a base64 blob,
    although it is not executable code, just a decorative comment.
    """
    if "process.php.txt" not in files or rng.random() >= 0.5:
        return dict(files), {"operator": "inject_obfuscation_marker", "applied": False}

    payload = base64.b64encode(
        b"esto es un ejemplo sintetico, no es codigo funcional"
    ).decode("ascii")
    line = f'\n// [marcador simulado, NO funcional] blob_ofuscado = "{payload}"\n'

    new_files = dict(files)
    new_files["process.php.txt"] = files["process.php.txt"] + line
    return new_files, {"operator": "inject_obfuscation_marker", "applied": True}


def op_inject_junk_comments(files, rng, context):
    """
    Inserts filler comments that do not change the behaviour.
    """
    new_files = dict(files)
    if "index.html" in new_files:
        c = rng.choice(JUNK_COMMENTS_HTML)
        new_files["index.html"] = new_files["index.html"].replace("<head>", f"<head>\n  {c}", 1)
    if "style.css" in new_files:
        c = rng.choice(JUNK_COMMENTS_CSS)
        new_files["style.css"] = c + "\n" + new_files["style.css"]
    if "script.js" in new_files:
        c = rng.choice(JUNK_COMMENTS_JS)
        new_files["script.js"] = c + "\n" + new_files["script.js"]
    return new_files, {"operator": "inject_junk_comments"}


def op_reformat_whitespace(files, rng, context):
    """
    Adds or removes blank lines, simulating what a different editor or developer might do.
    """
    mode = rng.choice(["compact", "loose"])
    new_files = {}
    for name, content in files.items():
        lines = content.split("\n")
        if mode == "compact":
            lines = [ln for ln in lines if ln.strip() != ""]
        else:
            out = []
            for ln in lines:
                out.append(ln)
                if rng.random() < 0.15:
                    out.append("")
            lines = out
        new_files[name] = "\n".join(lines)
    return new_files, {"operator": "reformat_whitespace", "mode": mode}


def op_swap_quote_style(files, rng, context):
    """
    Changes double quotes to single quotes or vice versa, in HTML attributes and simple js strings.
    
    This  operator is intentionally last, to avoid leaving mixed quotes if another operatod inserted them.
    """
    target = rng.choice(["double_to_single", "single_to_double"])
    new_files = {}
    for name, content in files.items():
        if name.endswith(".html"):
            if target == "double_to_single":
                content = re.sub(r'="([^"]*)"', r"='\1'", content)
            else:
                content = re.sub(r"='([^']*)'", r'="\1"', content)
        elif name.endswith(".js"):
            if target == "double_to_single":
                content = re.sub(r'"([^"\n]*)"', r"'\1'", content)
            else:
                content = re.sub(r"'([^'\n]*)'", r'"\1"', content)
        new_files[name] = content
    return new_files, {"operator": "swap_quote_style", "target": target}
