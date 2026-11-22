import json
from pathlib import Path
from src.normalization import normalize_word

CANDIDATES_PATH = Path("reports/candidates.json")
COMPONENTS_PATH = Path("reports/components.json")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

COUNT_FIELDS = (
    "transpositions",
    "words_added",
    "words_removed",
    "words_swapped",
)


def required_count_fields(component):
    if component["stage1_decision"] == "transposition":
        return ("transpositions",)

    if component["stage1_decision"] == "textual_difference":
        return COUNT_FIELDS

    return ()


def valid_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def normalized_region(candidate, side):
    return [
        normalize_word(word, normalize_final_sigma=False)
        for word in candidate[f"source_{side}_region"]
    ]


def nearby_variants(candidate, candidates):
    nearby = []

    for other in candidates:
        if other["id"] == candidate["id"]:
            continue

        if (
            other["book"] != candidate["book"]
            or other["source_a"] != candidate["source_a"]
            or other["source_b"] != candidate["source_b"]
        ):
            continue

        candidate_ranges = [
            (
                tuple(candidate[f"source_{side}_start_reference"]),
                tuple(candidate[f"source_{side}_end_reference"]),
            )
            for side in ("a", "b")
        ]

        other_ranges = [
            (
                tuple(other[f"source_{side}_start_reference"]),
                tuple(other[f"source_{side}_end_reference"]),
            )
            for side in ("a", "b")
        ]

        if any(
            start_a <= end_b and start_b <= end_a
            for start_a, end_a in candidate_ranges
            for start_b, end_b in other_ranges
        ):
            nearby.append(other)

    return nearby


def matching_component(candidate, other_candidate, component, other_component):
    if candidate["id"] == other_candidate["id"]:
        return None

    if component["stage1_decision"] != other_component.get("stage1_decision"):
        return None

    candidate_a = normalized_region(candidate, "a")
    candidate_b = normalized_region(candidate, "b")
    other_a = normalized_region(other_candidate, "a")
    other_b = normalized_region(other_candidate, "b")

    if candidate_a == other_a and candidate_b == other_b:
        return "same"

    if candidate_a == other_b and candidate_b == other_a:
        return "reverse"

    return None


def propagate_component(candidate, component, candidates, components):
    propagated = 0

    linked_ids = set()

    for candidate_id, existing_component in components.items():
        if not isinstance(existing_component, dict):
            continue

        linked_to = existing_component.get("linked_to")

        if linked_to:
            linked_ids.add(candidate_id)
            linked_ids.add(linked_to)

    if candidate["id"] in linked_ids:
        return 0

    for other in candidates:
        if other["id"] == candidate["id"]:
            continue

        if other["id"] in linked_ids:
            continue

        if (
            other["id"] not in components
            or components[other["id"]].get("status") != "manual_review"
        ):
            continue

        match = matching_component(
            candidate,
            other,
            component,
            components[other["id"]],
        )

        if match is None:
            continue

        copied = component.copy()

        if (
            match == "reverse"
            and component["stage1_decision"] == "textual_difference"
        ):
            copied["words_added"], copied["words_removed"] = (
                copied["words_removed"],
                copied["words_added"],
            )

        components[other["id"]] = copied
        propagated += 1

    return propagated

def main():
    candidates = load_json(CANDIDATES_PATH)
    components = load_json(COMPONENTS_PATH)

    repaired = 0

    for component in components.values():
        if not isinstance(component, dict):
            continue

        fields = required_count_fields(component)

        if (
            component.get("status") == "manual"
            and any(
                field not in component
                or not valid_count(component[field])
                for field in fields
            )
        ):
            component["status"] = "manual_review"
            repaired += 1

    if repaired:
        save_json(COMPONENTS_PATH, components)
        print(f"Returned {repaired} components with invalid counts to manual review.")

    current_ids = {candidate["id"] for candidate in candidates}
    stale_ids = set(components) - current_ids


    current_ids = {candidate["id"] for candidate in candidates}
    stale_ids = set(components) - current_ids

    changed = True
    while changed:
        changed = False

        for candidate_id, component in components.items():
            if candidate_id in stale_ids or not isinstance(component, dict):
                continue

            if component.get("linked_to") in stale_ids:
                stale_ids.add(candidate_id)
                changed = True

    if stale_ids:
        for candidate_id in stale_ids:
            del components[candidate_id]

        save_json(COMPONENTS_PATH, components)
        print(
            f"Removed {len(stale_ids)} stale or linked Stage 2 components."
        )

    pending = [
        candidate
        for candidate in candidates
        if candidate["id"] in components
        and components[candidate["id"]]["status"] == "manual_review"
        and components[candidate["id"]]["stage1_decision"]
        in ("transposition", "textual_difference")
    ]

    print(f"Pending manual cases: {len(pending)}")

    for index, candidate in enumerate(pending, start=1):
        component = components[candidate["id"]]

        print("\n" + "=" * 72)

        nearby = nearby_variants(candidate, candidates)

        if nearby:
            print(f"\nNearby variants ({len(nearby)}):")

            for other in nearby:
                other_component = components.get(other["id"], {})
                stage2_status = (
                    f"{other_component.get('transpositions', 0)},"
                    f"{other_component.get('words_added', 0)},"
                    f"{other_component.get('words_removed', 0)},"
                    f"{other_component.get('words_swapped', 0)}"
                    if other_component
                    else "not classified"
                )

                print(f"\n  ID: {other['id']}")
                print(
                    f"  Reference: {other['source_a_start_reference'][0]}:"
                    f"{other['source_a_start_reference'][1]}"
                    f"-{other['source_a_end_reference'][0]}:"
                    f"{other['source_a_end_reference'][1]}"
                )
                print(f"  Stage 2: {stage2_status}")
                print("  A:", " ".join(normalized_region(other, "a")))
                print("  B:", " ".join(normalized_region(other, "b")))
        else:
            print("\nNearby variants: none")
        print("")

        print(
            f"{index}/{len(pending)}  {candidate['book']}  "
            f"{candidate['source_a']} -> {candidate['source_b']}"
        )
        print(f"ID: {candidate['id']}")
        print(
            f"Reference: {candidate['source_a_start_reference'][0]}:"
            f"{candidate['source_a_start_reference'][1]}"
            f"-{candidate['source_a_end_reference'][0]}:"
            f"{candidate['source_a_end_reference'][1]}"
        )
        print(f"Type: {component['stage1_decision']}")
        print("A:", " ".join(
            normalize_word(word, normalize_final_sigma=False)
            for word in candidate["source_a_region"]
        ))
        print("B:", " ".join(
            normalize_word(word, normalize_final_sigma=False)
            for word in candidate["source_b_region"]
        ))


        if nearby:
            current_link = component.get("linked_to") or ""
            valid_ids = {item["id"] for item in candidates}

            while True:
                linked_input = input(
                    f"Linked to candidate ID "
                    f"[{current_link or 'none'}] "
                    "(Enter = keep, - = clear, q = quit): "
                ).strip()

                if linked_input.lower() == "q":
                    print("Review stopped. Saved answers are preserved.")
                    return

                if linked_input == "":
                    break

                if linked_input == "-":
                    component["linked_to"] = None
                    break

                if linked_input == candidate["id"]:
                    print("A candidate cannot be linked to itself.")
                    continue

                if linked_input not in valid_ids:
                    print("That ID is not in the current candidates.")
                    continue

                component["linked_to"] = linked_input
                break

            if component.get("linked_to") != current_link:
                linked_to = component.get("linked_to")
                linked_component = components.get(linked_to)

                if (
                    linked_component
                    and not linked_component.get("linked_to")
                    and linked_component.get("status") in ("automatic", "manual")
                ):
                    for field in COUNT_FIELDS:
                        linked_component[field] = None

                    linked_component["status"] = "manual_review"

                    print(
                        f"Reset linked candidate {linked_to} "
                        "to manual review."
                    )

                save_json(COMPONENTS_PATH, components)
                print("Saved linked-to field.")


        while True:

            if component["stage1_decision"] == "transposition":
                answer = input(
                    "Number of words moved (q = quit): "
                ).strip().lower()
            else:
                prompts = [
                    "Number of words moved: ",
                    "Number of words added: ",
                    "Number of words removed: ",
                    "Number of words swapped: ",
                ]

                while True:
                    counts = []
                    retry = False
                    answer = None

                    for prompt in prompts:
                        value = input(prompt + "(Enter = skip, q = quit): ").strip().lower()

                        if value == "q":
                            answer = "q"
                            break

                        if value == "":
                            value = "0"

                        try:
                            count = int(value)
                        except ValueError:
                            print("Please enter a non-negative whole number.")
                            retry = True
                            break

                        if count < 0:
                            print("The count cannot be negative.")
                            retry = True
                            break

                        counts.append(count)

                    if answer in ("q", ""):
                        break

                    if retry:
                        print("Let's enter the four counts again.")
                        continue

                    print("\nPlease confirm these counts:")
                    print(f"  Transpositions: {counts[0]}")
                    print(f"  Words added:    {counts[1]}")
                    print(f"  Words removed:  {counts[2]}")
                    print(f"  Words swapped:  {counts[3]}")

                    confirm = input("Save these counts? (y/n/q): ").strip().lower()

                    if confirm == "q":
                        answer = "q"
                        break

                    if confirm == "y" or confirm == "":
                        answer = ",".join(str(count) for count in counts)
                        break

                    print("Let's enter the four counts again.")


            if answer == "q":
                print("Review stopped. Saved answers are preserved.")
                return

            if answer == "":
                break

            if component["stage1_decision"] == "transposition":
                try:
                    count = int(answer)
                except ValueError:
                    print("Enter a non-negative whole number, Enter, or q.")
                    continue

                if count < 0:
                    print("The count cannot be negative.")
                    continue

                component["transpositions"] = count

            else:
                try:
                    counts = [int(value.strip()) for value in answer.split(",")]
                except ValueError:
                    print("Enter four non-negative whole numbers separated by commas.")
                    continue

                if len(counts) != 4 or any(count < 0 for count in counts):
                    print("Enter exactly four non-negative whole numbers separated by commas.")
                    continue

                (
                    component["transpositions"],
                    component["words_added"],
                    component["words_removed"],
                    component["words_swapped"],
                ) = counts

            fields = required_count_fields(component)

            if any(
                not valid_count(component.get(field))
                for field in fields
            ):
                print("Cannot save: all required counts must be non-negative whole numbers.")
                continue

            component["status"] = "manual"

            propagated = propagate_component(
                candidate,
                component,
                candidates,
                components,
            )

            save_json(COMPONENTS_PATH, components)

            print("Saved.")
            if propagated:
                print(
                    f"Applied this classification to "
                    f"{propagated} matching candidate(s)."
                )
            break

    print("\nReview session complete.")
    print(f"Components saved to {COMPONENTS_PATH}")


if __name__ == "__main__":
    main()
