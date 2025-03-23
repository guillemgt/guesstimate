import sys
import os
import json

from pydantic import BaseModel, Field
from typing import Tuple, Union, Optional
from enum import Enum
from tqdm import tqdm
from dotenv import load_dotenv

from functools import partial
from utils.input_output import output_and_log_files


def remove_quantities_with_small_ints(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    # Read the input questions
    with open(input_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    filtered_questions = [
        question
        for question in questions
        if "value" in question["value"]
        and not any(
            isinstance(answer, int) and 0 < answer < 10
            for answer in [question["value"]["value"]]
        )
    ]

    print("Number of original entries:", len(questions))
    print("Number of filtered entries:", len(filtered_questions))

    # Write the filtered questions to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered_questions, f, ensure_ascii=False, indent=1)

    # Write metadata
    with open(
        output_file.replace(".json", ".metadata.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(
            {
                "entries_before": len(questions),
                "entries_after": len(filtered_questions),
            },
            f,
            ensure_ascii=False,
            indent=1,
        )

    return output_file
