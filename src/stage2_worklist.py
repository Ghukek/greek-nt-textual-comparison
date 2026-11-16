
import json
from pathlib import Path

from src.normalization import normalize_word


CANDIDATES_PATH = Path("reports/candidates.json")
DECISIONS_PATH = Path("reports/decisions.json")
COMPONENTS_PATH = Path("reports/components.json")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_component(candidate, decision):
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

        if not region_a and region_b:
            component["words_added"] = len(region_b)
            component["words_removed"] = 0
            component["words_swapped"] = 0
            component["transpositions"] = 0
            component["status"] = "automatic"

        elif region_a and not region_b:
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
    candidates = load_json(CANDIDATES_PATH)
    current_ids = {candidate["id"] for candidate in candidates}
    decisions = load_json(DECISIONS_PATH)

    existing = (
        load_json(COMPONENTS_PATH)
        if COMPONENTS_PATH.exists()
        else {}
    )

    preserved = {
        candidate_id: component
        for candidate_id, component in existing.items()
        if candidate_id in current_ids and component["status"] in ("manual", "reused")
    }

    components = preserved.copy()

    for candidate in candidates:
        candidate_id = candidate["id"]

        if candidate_id in preserved:
            continue

        decision = decisions.get(candidate_id)

        if decision is None:
            continue

        component = build_component(candidate, decision)

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

