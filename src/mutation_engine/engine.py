"""
engine.py

Mutation engine: takes the files of a seed kit and generates
variants by applying a random (but reproducible) combination of
the operators defined in operators.py.
"""

import random

from . import operators as ops

# The order of this list is the execution order (not the selection order, which is random).
# swap_quote_style is intentionally last, to avoid leaving mixed quotes.
OPERATOR_POOL = [
    ("add_optional_field", ops.op_add_optional_field),
    ("reorder_css_rules", ops.op_reorder_css_rules),
    ("randomize_config_destination", ops.op_randomize_config_destination),
    ("mutate_signature", ops.op_mutate_signature),
    ("vary_visible_text", ops.op_vary_visible_text),
    ("rebrand", ops.op_rebrand),
    ("rename_identifiers", ops.op_rename_identifiers),
    ("inject_obfuscation_marker", ops.op_inject_obfuscation_marker),
    ("inject_junk_comments", ops.op_inject_junk_comments),
    ("reformat_whitespace", ops.op_reformat_whitespace),
    ("swap_quote_style", ops.op_swap_quote_style),
]

INTENSITY_LEVELS = {
    "light": (1, 3),
    "medium": (4, 7),
    "heavy": (8, len(OPERATOR_POOL)),
}


class MutationEngine:
    def __init__(self, context, operator_pool=None):
        """
        context: dict with information about the family, such as:
            {
              "identifiers": [...],
              "brand_name": "NimbusBox",
              "alt_brands": ["Zephyr Mail", ...],
            }
        """
        self.context = context
        self.operator_pool = operator_pool or OPERATOR_POOL

    def generate_variant(self, seed_files, rng_seed, intensity="medium"):
        """
        seed_files : dict {relative_path: content} from seed kit.
        rng_seed   : integer -> same rng_seed = same result always.
        intensity  : 'light' | 'medium' | 'heavy'.

        Returns (new_files, manidest_of_this_variant).
        """
        rng = random.Random(rng_seed)

        lo, hi = INTENSITY_LEVELS[intensity]
        hi = min(hi, len(self.operator_pool))
        n_ops = rng.randint(lo, hi)

        chosen_names = {name for name, _ in rng.sample(self.operator_pool, k=n_ops)}
        # We filter the operator_pool to keep only the chosen operators, keeping their order intact.
        chosen_ops = [pair for pair in self.operator_pool if pair[0] in chosen_names]

        files = dict(seed_files)
        applied = []
        for name, func in chosen_ops:
            files, meta = func(files, rng, self.context)
            applied.append(meta)

        manifest = {
            "rng_seed": rng_seed,
            "intensity": intensity,
            "num_operators_applied": n_ops,
            "operators": applied,
        }
        return files, manifest