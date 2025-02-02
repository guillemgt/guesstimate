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


def remove_date_and_unit_from_descriptions(
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

    num_changed = 0
    for question in questions:
        if "rewritten-description" in question:
            prompt = question["rewritten-description"]["prompt"]
            date = question["rewritten-description"].get("date") or ""
            units = question["rewritten-description"].get("units") or ""
            new_prompt = prompt.replace(date, "").replace(units, "")
            if new_prompt != prompt:
                question["rewritten-description"]["prompt"] = new_prompt
                num_changed += 1

    print(f"Number of questions with date and unit removed: {num_changed}")

    # Write the filtered questions to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=1)

    return output_file
