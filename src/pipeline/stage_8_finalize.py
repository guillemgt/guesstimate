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
                question["rewritten-description"]["prompt"][len("Estimate ") :],
                question["rewritten-description"]["date"],
                question["rewritten-description"]["units"],
            ],
            "answer": (
                question["rewritten-description"]["answer"]["value"]
                if "single_value" in question["rewritten-description"]["answer"]
                else [
                    question["rewritten-description"]["answer"]["min_value"],
                    question["rewritten-description"]["answer"]["max_value"],
                ]
            ),
            "excerpt": question["found_excerpt"],
            "scale-interval": question["scale-interval"],
        }
        for question in questions
        if (
            not use_handwritten_filter
            or question["scale-interval"]["lower_bound"] is not None
        )
        and question["rewritten-description"]["prompt"].startswith("Estimate ")
    ]

    # Write the final questions to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_questions, f, ensure_ascii=False, indent=1)

    return output_file
