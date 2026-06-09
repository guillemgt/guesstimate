import os
import json

from utils.input_output import output_and_log_files


def process_interval(answer):
    if not isinstance(answer, list):
        return answer
    if len(set(answer)) == 1:
        return answer[0]
    return list(sorted(answer))


def finalize(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    use_handwritten_filter: bool = False,
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    # Read the input questions
    with open(input_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    final_questions = [
        {
            "uuid": question["uuid"],
            "topic": question["topic"],
            "description": [
                question["rewritten-description"]["description"].removeprefix(
                    "Estimate "
                ),
                question["rewritten-description"]["time_period"],
                question["rewritten-description"]["units"],
            ],
            "answer": process_interval(
                question["rewritten-description"]["answer"]["value_or_interval"]
            ),
            "excerpt": " ".join(
                x
                for x in [
                    question["found_excerpt_expansion"][0],
                    question["excerpt_with_highlight"],
                    question["found_excerpt_expansion"][1],
                ]
                if x.strip()
            ),
            "scale-interval": (
                question["scale-interval"]
                if "scale-interval" in question
                else {"lower_bound": 0, "upper_bound": None}
            ),
        }
        for question in questions
        if (
            True
            # not use_handwritten_filter
            # or question["scale-interval"]["lower_bound"] is not None
        )
    ]

    # Write the final questions to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_questions, f, ensure_ascii=False, indent=1)

    with open(
        output_file.replace(".json", ".metadata.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(
            {
                "number_of_questions": len(final_questions),
            },
            f,
            ensure_ascii=False,
            indent=1,
        )

    return output_file
