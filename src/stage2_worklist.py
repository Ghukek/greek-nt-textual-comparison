
import json
from pathlib import Path
from difflib import SequenceMatcher
from src.normalization import normalize_word
import argparse

CANDIDATES_PATH = Path("reports/candidates.json")
DECISIONS_PATH = Path("reports/decisions.json")
COMPONENTS_PATH = Path("reports/components.json")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def verse_ranges(candidate):
    ranges = []

    for side in ("a", "b"):
        start = candidate.get(f"source_{side}_start_reference")
        end = candidate.get(f"source_{side}_end_reference")

        if start and end:
            ranges.append((tuple(start), tuple(end)))

    return ranges


def ranges_overlap(candidate_a, candidate_b):
    ranges_a = verse_ranges(candidate_a)
    ranges_b = verse_ranges(candidate_b)

    return any(
        start_a <= end_b and start_b <= end_a
        for start_a, end_a in ranges_a
        for start_b, end_b in ranges_b
    )


def contains_sequence(words, target):
    if not target or len(target) > len(words):
        return False

    return any(
        words[i:i + len(target)] == target
        for i in range(len(words) - len(target) + 1)
    )


def has_opposite_text(region_a, region_b, target, target_side):
    matcher = SequenceMatcher(
        None, region_a, region_b, autojunk=False
    )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        segment_a = region_a[i1:i2]
        segment_b = region_b[j1:j2]

        if target_side == "a":
            # The current candidate has text only on A.
            # Look for corresponding B-only text elsewhere.
            if tag == "insert" and tuple(segment_b) == target:
                return True

            if (
                tag == "replace"
                and len(segment_b) > len(segment_a)
                and contains_sequence(segment_b, target)
                and not contains_sequence(segment_a, target)
            ):
                return True

        else:
            # The current candidate has text only on B.
            # Look for corresponding A-only text elsewhere.
            if tag == "delete" and tuple(segment_a) == target:
                return True

            if (
                tag == "replace"
                and len(segment_a) > len(segment_b)
                and contains_sequence(segment_a, target)
                and not contains_sequence(segment_b, target)
            ):
                return True

    return False


def has_opposite_variant(candidate, candidates, decisions):
    region_a = tuple(
        normalize_word(word)
        for word in candidate["source_a_region"]
    )
    region_b = tuple(
        normalize_word(word)
        for word in candidate["source_b_region"]
    )

    if not region_a and region_b:
        target = region_b
        target_side = "b"
    elif region_a and not region_b:
        target = region_a
        target_side = "a"
    else:
        return False

    for other in candidates:
        if other["id"] == candidate["id"]:
            continue

        if (
            other["book"] != candidate["book"]
            or other["source_a"] != candidate["source_a"]
            or other["source_b"] != candidate["source_b"]
        ):
            continue

        other_decision = decisions.get(other["id"])

        if (
            other_decision is None
            or other_decision["decision"] != "textual_difference"
        ):
            continue

        if not ranges_overlap(candidate, other):
            continue

        other_a = [
            normalize_word(word)
            for word in other["source_a_region"]
        ]
        other_b = [
            normalize_word(word)
            for word in other["source_b_region"]
        ]

        if has_opposite_text(
            other_a, other_b, target, target_side
        ):
            return True

    return False

def build_component(candidate, decision, opposite_variant=False):
    label = decision["decision"]

    if label not in ("transposition", "textual_difference"):
        return None

    region_a = [
        normalize_word(word)
        for word in candidate["source_a_region"]
    ]
    region_b = [
        normalize_word(word)
        for word in candidate["source_b_region"]
    ]

    component = {
        "book": candidate["book"],
        "source_a": candidate["source_a"],
        "source_b": candidate["source_b"],
        "stage1_decision": label,
        "status": "manual_review",
    }


    if label == "transposition":
        component.update({
            "transpositions": None,
        })

        n = len(region_a)

        if (
            n >= 2
            and len(region_b) == n
            and region_a != region_b
        ):
            shifts = [
                k for k in range(1, n)
                if region_a[k:] + region_a[:k] == region_b
            ]

            proposed_counts = {
                min(k, n - k)
                for k in shifts
            }

            if len(proposed_counts) == 1:
                component["transpositions"] = proposed_counts.pop()
                component["status"] = "automatic"

    else:
        component.update({
            "transpositions": None,
            "words_added": None,
            "words_removed": None,
            "words_swapped": None,
        })

        if not region_a and region_b and not opposite_variant:
            component["words_added"] = len(region_b)
            component["words_removed"] = 0
            component["words_swapped"] = 0
            component["transpositions"] = 0
            component["status"] = "automatic"

        elif region_a and not region_b and not opposite_variant:
            component["words_added"] = 0
            component["words_removed"] = len(region_a)
            component["words_swapped"] = 0
            component["transpositions"] = 0
            component["status"] = "automatic"

        elif len(region_a) == 1 and len(region_b) == 1:
            component["words_added"] = 0
            component["words_removed"] = 0
            component["words_swapped"] = 1
            component["transpositions"] = 0
            component["status"] = "automatic"

    return component

def variant_key(candidate, decision):
    return (
        decision["decision"],
        tuple(
            normalize_word(word)
            for word in candidate["source_a_region"]
        ),
        tuple(
            normalize_word(word)
            for word in candidate["source_b_region"]
        ),
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recheck-automatic",
        action="store_true",
        help="Re-evaluate existing automatic classifications.",
    )
    args = parser.parse_args()


    candidates = load_json(CANDIDATES_PATH)
    current_ids = {candidate["id"] for candidate in candidates}
    decisions = load_json(DECISIONS_PATH)

    existing = (
        load_json(COMPONENTS_PATH)
        if COMPONENTS_PATH.exists()
        else {}
    )


    linked_ids = set()

    for candidate_id, component in existing.items():
        if not isinstance(component, dict):
            continue

        linked_to = component.get("linked_to")

        if linked_to:
            linked_ids.add(candidate_id)
            linked_ids.add(linked_to)


    preserved = {
        candidate_id: component
        for candidate_id, component in existing.items()
        if candidate_id in current_ids
        and (
            candidate_id in linked_ids
            or component["status"] in ("manual", "reused")
            or (
                component["status"] == "automatic"
                and not args.recheck_automatic
            )
        )
    }


    for candidate_id in linked_ids:
        component = preserved.get(candidate_id)

        if component and component.get("status") == "automatic":
            component["status"] = "manual_review"


    components = preserved.copy()

    for candidate in candidates:
        candidate_id = candidate["id"]

        if candidate_id in preserved:
            continue

        if candidate_id in linked_ids:
            continue

        decision = decisions.get(candidate_id)

        if decision is None:
            continue

        opposite_variant = has_opposite_variant(
            candidate, candidates, decisions
        )

        component = build_component(
            candidate, decision, opposite_variant
        )

        if component is not None:
            components[candidate_id] = component


    candidates_by_id = {
        candidate["id"]: candidate
        for candidate in candidates
    }

    reviewed_variants = {}

    for candidate_id, component in components.items():
        if component["status"] not in ("manual", "reused"):
            continue

        candidate = candidates_by_id.get(candidate_id)
        decision = decisions.get(candidate_id)

        if candidate is None or decision is None:
            continue

        key = variant_key(candidate, decision)
        reviewed_variants.setdefault(key, component)

    for candidate in candidates:
        candidate_id = candidate["id"]
        component = components.get(candidate_id)

        if component is None or component["status"] != "manual_review":
            continue

        if candidate_id in linked_ids:
            continue

        decision = decisions.get(candidate_id)
        if decision is None:
            continue

        key = variant_key(candidate, decision)
        reviewed = reviewed_variants.get(key)

        if reviewed is None:
            continue

        fields = (
            ("transpositions",)
            if component["stage1_decision"] == "transposition"
            else (
                "transpositions",
                "words_added",
                "words_removed",
                "words_swapped",
            )
        )

        for field in fields:
            component[field] = reviewed[field]

        component["status"] = "reused"


    COMPONENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPONENTS_PATH.write_text(
        json.dumps(components, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    automatic = sum(
        item["status"] == "automatic"
        for item in components.values()
    )
    manual = sum(
        item["status"] == "manual_review"
        for item in components.values()
    )
    reused = sum(
        item["status"] == "reused"
        for item in components.values()
    )

    print(f"Stage 2 candidates: {len(components)}")
    print(f"Automatically completed: {automatic}")
    print(f"Need manual review: {manual}")
    print(f"Reused classifications: {reused}")
    print(f"Saved to {COMPONENTS_PATH}")


if __name__ == "__main__":
    main()

