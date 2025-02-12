import sys
import os
from enum import Enum

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import BaseModel, Field
from typing import Tuple, Union, Optional
from enum import Enum
from tqdm import tqdm
from dotenv import load_dotenv

from functools import partial
from utils.input_output import output_and_log_files
from pipeline.general.generic_api_step import (
    generic_api_processing_step,
    fetch_api_response_and_process_with_structured_outputs,
    fetch_api_response_and_process_with_logprobs,
)
from pipeline.stage_4_mine_quantities import SingleValueModifier


def format_question(question: dict) -> str:
    if "rewritten-description" in question:
        prompt = question["rewritten-description"]["prompt"]
        parts = [
            prompt,
            question["rewritten-description"]["date"],
            question["rewritten-description"]["units"],
        ]
        estimation_task_text = " ".join([part for part in parts if part])
    else:
        estimation_task_text = (
            question["topic"]
            + ": "
            + question["description"]
            + (
                f" (in {question['value']['unit']})"
                if question["value"]["unit"] is not None
                else ""
            )
        )

    value = question.get("rewritten-description", {}).get("answer", question["value"])
    if "single_value" in value:
        modifier = value["modifier"]
        modifier = (
            modifier
            if modifier
            in {SingleValueModifier.MORE_THAN, SingleValueModifier.LESS_THAN}
            else None
        )
        the_value = value["value"]
        unit = value["unit"]
        formatted_answer = " ".join(
            str(x) for x in [modifier, the_value, unit] if x is not None
        )
    elif "interval" in value:
        min_value = value["min_value"]
        max_value = value["max_value"]
        unit = value["unit"]
        formatted_value = f"between {min_value} and {max_value}"
        formatted_answer = " ".join(
            str(x) for x in [formatted_value, unit] if x is not None
        )

    return f"""# Estimation task
{estimation_task_text}

# Value to evaluate
{formatted_answer}

# Text passage
{question['found_excerpt']}"""


def filter_correct(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-4o-mini",
    logprob_threshold: float = -0.05,
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    logprob_key = "logprob-correctness"

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction="You will receive of description of a task about estimating a quantity, a value of the quantity and a text passage. You must reply only YES if the answer is erfectly correct according to the passage and NO otherwise.",
        format_question_into_prompt=format_question,
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_with_logprobs,
            logprob_key=logprob_key,
            logprob_positive_tokens="YES",
            logprob_negative_tokens="NO",
            completion_kwargs=dict(
                model=model,
            ),
        ),
        filter_questions=lambda questions: [
            question
            for question in questions
            if question[logprob_key] is not None
            and question[logprob_key] > logprob_threshold
        ],
        examples=[],
        sort_by_key=logprob_key,
    )

    return output_file
