import json


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def binary_search_interactive(data, key, questions_per_round=5):
    """Perform an interactive binary search to determine the threshold."""

    # Sort the values to ensure binary search works
    data.sort(key=lambda x: x[key])
    valid_indices = range(len(data))  # Keep track of valid indices

    while len(valid_indices) > questions_per_round:
        # Determine the indices to ask questions about
        median_index = len(valid_indices) // 2
        tested_low = median_index - questions_per_round // 2
        tested_high = median_index + questions_per_round // 2 + 1
        query_indices = valid_indices[tested_low:tested_high]

        # Display the selected values to the user
        print("\nPlease evaluate the following values:")
        valids = 0
        invalids = 0
        for i, idx in enumerate(query_indices):
            q = " ".join(
                v for v in data[idx]["rewritten-description"].values() if v is not None
            )
            print(f"{i + 1}: {q}")
            response = input(f"Is this valid? (yes/no): ").strip().lower()
            if response in ("yes", "y"):
                valids += 1
            else:
                invalids += 1

            if valids > questions_per_round / 2 or invalids > questions_per_round / 2:
                break

        questions_are_valid = valids > invalids

        if not questions_are_valid:
            valid_indices = valid_indices[tested_high:]
            print("Threshold >=", data[valid_indices[0]][key])
        else:
            valid_indices = valid_indices[:tested_low]
            print("Threshold <=", data[valid_indices[-1]][key])

    # When we have few enough indices, return their median as the threshold
    threshold = data[valid_indices[len(valid_indices) // 2]][key]
    print(f"\nThe determined threshold is approximately: {threshold}")
    return threshold


def main():
    file_path = r"data\pipeline\17_stage_6_filter_clarity.unfiltered.json"
    key = input("Enter the key containing the float values: ").strip()

    data = load_json(file_path)
    binary_search_interactive(data, key)


if __name__ == "__main__":
    main()
