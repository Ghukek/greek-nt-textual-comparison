
import json
from pathlib import Path
from src.normalization import normalize_word


REPORT_PATH = Path("reports/candidates.json")
DECISIONS_PATH = Path("reports/decisions.json")
RULES_PATH = Path("reports/rules.json")

DECISION_LABELS = {
    "s": "spelling",
    "m": "movable_nu",
    "w": "word_segmentation",
    "t": "transposition",
    "d": "textual_difference",
    "u": "unresolved",
}

def save_rules(rules):
    RULES_PATH.parent.mkdir(exist_ok=True)
    with RULES_PATH.open("w", encoding="utf-8") as output:
        json.dump(rules, output, ensure_ascii=False, indent=2)
        output.write("\n")


def matches_rule(candidate, rules):
    region_a = [
        normalize_word(word)
        for word in candidate["source_a_region"]
    ]
    region_b = [
        normalize_word(word)
        for word in candidate["source_b_region"]
    ]

    if bool(region_a) != bool(region_b):
        return "textual_difference"

    for rule in rules:
        forms = sorted([region_a, region_b])

        if "forms" in rule and forms == rule["forms"]:
            return rule["type"]

        if "forms" in rule:
            continue

        if rule["type"] in ("spelling", "movable_nu"):
            if len(region_a) != 1 or len(region_b) != 1:
                continue

            words = sorted([region_a[0], region_b[0]])

            if words == rule["words"]:
                if rule["type"] == "spelling":
                    if words[0] + "ν" == words[1] or words[1] + "ν" == words[0]:
                        continue

                return rule["type"]

        elif rule["type"] == "word_segmentation":
            if len(region_a) == len(region_b):
                continue

            forms = sorted([region_a, region_b])

            if forms == rule["forms"]:
                return rule["type"]

        elif rule["type"] == "textual_difference":
            forms = sorted([region_a, region_b])

            if forms == rule["forms"]:
                return rule["type"]

        elif rule["type"] == "transposition":
            forms = sorted([region_a, region_b])

            if forms == rule["forms"]:
                return rule["type"]

    return False


def add_classification_rule(candidate, label, rules):
    words_a = [
        normalize_word(word)
        for word in candidate["source_a_region"]
    ]
    words_b = [
        normalize_word(word)
        for word in candidate["source_b_region"]
    ]

    if words_a == words_b:
        return False

    if label == "unresolved":
        return False

    rule = {
        "type": label,
        "forms": sorted([words_a, words_b]),
    }

    if rule in rules:
        return False

    rules.append(rule)
    return True



def load_json(path, default):
    if not path.exists():
        return default

    with path.open(encoding="utf-8") as source:
        return json.load(source)


def save_decisions(decisions):
    DECISIONS_PATH.parent.mkdir(exist_ok=True)
    with DECISIONS_PATH.open("w", encoding="utf-8") as output:
        json.dump(decisions, output, ensure_ascii=False, indent=2)
        output.write("\n")


def format_reference(reference):
    if reference is None:
        return "(none)"

    return f"{reference[0]}:{reference[1]}"


def show_region(candidate, source):
    start = format_reference(candidate[f"{source}_start_reference"])
    end = format_reference(candidate[f"{source}_end_reference"])

    region = " ".join(
        normalize_word(word, normalize_final_sigma=False)
        for word in candidate[f"{source}_region"]
    )
    before = " ".join(
        normalize_word(word, normalize_final_sigma=False)
        for word in candidate[f"{source}_context_before"]
    )
    after = " ".join(
        normalize_word(word, normalize_final_sigma=False)
        for word in candidate[f"{source}_context_after"]
    )

    print(f"\n{source} ({start}–{end})")
    print(f"  Before: {before or '(beginning)'}")
    print(f"  Region: {region or '(no words)'}")
    print(f"  After:  {after or '(end)'}")


def main():
    candidates = load_json(REPORT_PATH, None)

    if candidates is None:
        raise FileNotFoundError(f"Candidate report not found: {REPORT_PATH}")

    decisions = load_json(DECISIONS_PATH, {})
    rules = load_json(RULES_PATH, [])

    ids = [candidate["id"] for candidate in candidates]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate candidate IDs found in the report.")

    current_ids = set(ids)
    stale_ids = set(decisions) - current_ids

    automatic_changes = False

    if stale_ids:
        for candidate_id in stale_ids:
            del decisions[candidate_id]

        print(f"Removed {len(stale_ids)} stale saved decisions.")
        automatic_changes = True

    for candidate in candidates:
        candidate_id = candidate["id"]

        if decisions.get(candidate_id, {}).get("automatic_rule"):
            del decisions[candidate_id]
            automatic_changes = True

    for candidate in candidates:
        candidate_id = candidate["id"]

        if candidate_id in decisions:
            continue

        label = matches_rule(candidate, rules)

        if label:
            decisions[candidate_id] = {
                "decision": label,
                "note": "Automatically classified by reusable rule",
                "automatic_rule": True,
            }
            automatic_changes = True

    if automatic_changes:
        save_decisions(decisions)

    print(
        f"Automatically classified candidates: "
        f"{sum(1 for candidate in candidates if decisions.get(candidate['id'], {}).get('automatic_rule'))}"
    )


    if not candidates:
        print("No candidates to review.")
        return

    index = 0

    while index < len(candidates) and candidates[index]["id"] in decisions:
        index += 1

    if index == len(candidates):
        print("All candidates have recorded decisions.")
        return

    while True:
        while index < len(candidates) and candidates[index]["id"] in decisions:
            index += 1

        if index == len(candidates):
            print("All candidates have recorded decisions.")
            break

        candidate = candidates[index]
        candidate_id = candidate["id"]
        decision = decisions.get(candidate_id)

        print("\n" + "=" * 72)
        print(
            f"Candidate {index + 1}/{len(candidates)}  "
            f"{candidate['book']}  "
            f"{candidate['source_a']} vs {candidate['source_b']}"
        )
        print(f"ID: {candidate_id}")
        print(f"Alignment type: {candidate['type']}")

        if decision:
            print(f"Saved decision: {decision['decision']}")
            if decision.get("note"):
                print(f"Note: {decision['note']}")

        show_region(candidate, "source_a")
        show_region(candidate, "source_b")

        print("\nDecisions:")
        print("  s = spelling / orthography")
        print("  m = movable nu")
        print("  w = word segmentation")
        print("  t = transposition")
        print("  d = genuine textual difference")
        print("  u = unresolved")
        print("  > = next candidate")
        print("  < = previous candidate")
        print("  q = quit")

        choice = input("\nChoice: ").strip().lower()

        if choice == "q":
            break

        if choice == ">":
            index += 1
            continue

        if choice == "<":
            index = max(0, index - 1)

            while index > 0 and candidates[index]["id"] in decisions:
                index -= 1

            continue

        if choice not in DECISION_LABELS:
            print("Unrecognized choice.")
            continue

        label = DECISION_LABELS[choice]
        note = ""#input("Optional note (Enter for none): ").strip()

        decisions[candidate_id] = {
            "decision": label,
            "note": note,
        }

        if label in (
            "spelling",
            "movable_nu",
            "word_segmentation",
            "textual_difference",
            "transposition",
        ):
            if add_classification_rule(candidate, label, rules):
                save_rules(rules)
                print("Reusable rule saved.")

                for other in candidates:
                    other_id = other["id"]

                    if other_id in decisions:
                        continue

                    matched_label = matches_rule(other, [rules[-1]])

                    if matched_label:
                        decisions[other_id] = {
                            "decision": matched_label,
                            "note": "Automatically classified by reusable rule",
                            "automatic_rule": True,
                        }

        save_decisions(decisions)

        print("Decision saved.")
        index = (index + 1) % len(candidates)

    decision_counts = {}

    for candidate in candidates:
        decision = decisions.get(candidate["id"])
        if decision:
            label = decision["decision"]
            decision_counts[label] = decision_counts.get(label, 0) + 1

    reviewed = sum(decision_counts.values())

    print("\nReview summary:")
    print(f"  Total candidates: {len(candidates)}")
    print(f"  With decisions:  {reviewed}")
    print(f"  Remaining:       {len(candidates) - reviewed}")

    for label in DECISION_LABELS.values():
        print(f"  {label}: {decision_counts.get(label, 0)}")

    print(f"\nSaved decisions: {DECISIONS_PATH}")
    print(f"Total decisions recorded: {len(decisions)}")


if __name__ == "__main__":
    main()

