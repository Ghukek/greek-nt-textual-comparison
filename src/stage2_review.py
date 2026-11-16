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

    if stale_ids:
        for candidate_id in stale_ids:
            del components[candidate_id]

        save_json(COMPONENTS_PATH, components)
        print(f"Removed {len(stale_ids)} stale Stage 2 components.")

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
            save_json(COMPONENTS_PATH, components)
            print("Saved.")
            break

    print("\nReview session complete.")
    print(f"Components saved to {COMPONENTS_PATH}")


if __name__ == "__main__":
    main()
