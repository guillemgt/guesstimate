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
            "topic": question["topic"],
            "description": question["rewritten-description"],
            "answer": (
                question["value"]["value"]
                if "single_value" in question["value"]
                else [question["min_value"], question["max_value"]]
            ),
            "excerpt": question["found_excerpt"],
            "scale-interval": question["scale-interval"],
        }
        for question in questions
    ]

    # Write the final questions to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_questions, f, ensure_ascii=False, indent=1)

    return output_file
