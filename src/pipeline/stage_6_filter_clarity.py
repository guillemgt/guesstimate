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


class ClarityType(str, Enum):
    NoTechnicalTerms = "NoTechnicalTerms"
    MakesSenseWithoutContext = "MakesSenseWithoutContext"
    LaypersonCanGuess = "LaypersonCanGuess"
    MakesSense = "MakesSense"
    OverallClear = "OverallClear"
    TryToAnswer = "TryToAnswer"
    OverallClearDetailed = "OverallClearDetailed"


TASK_INSTRUCTIONS = {
    ClarityType.NoTechnicalTerms: "the description does not contain any technical terms or terms not known to a wide audience",
    ClarityType.MakesSenseWithoutContext: "the description makes sense without any additional context",
    ClarityType.LaypersonCanGuess: "anyone (not necessarily from America) would understand what the description refers to, so that it is clear what quantity is being talked about, and they would be able to make a guess the value of the quantity (possibly a bad guess)",
    ClarityType.MakesSense: "the description of the quantity makes sense",
    ClarityType.OverallClear: "the description of the quantity is clear and unambiguous, so that it is clear what quantity is being talked about",
    ClarityType.OverallClearDetailed: "it is clear and unambiguous what quantity is being talked about, the entity or concept referenced is widely known or can reasonably be deduced, and the description does not contain any name that will not be known by most people. It is NOT necessary for people to know the value of the quantity.",
}


def format_question(question: dict) -> str:
    if "rewritten-description" in question:
        prompt = question["rewritten-description"]["prompt"]
        if prompt.startswith("Estimate "):
            prompt = prompt[len("Estimate ") :]
        parts = [
            prompt,
            question["rewritten-description"]["date"],
            question["rewritten-description"]["units"],
        ]
        return " ".join([part for part in parts if part])
    else:
        return (
            question["topic"]
            + ": "
            + question["description"]
            + (
                f" (in {question['value']['unit']})"
                if question["value"]["unit"] is not None
                else ""
            )
        )


def filter_clear(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-4o-mini",
    logprob_threshold: float = -0.05,
    task: ClarityType = ClarityType.OverallClear,
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    if task == ClarityType.TryToAnswer:
        instruction = "Reply ONLY with the value of the quantity you're given a description of or NA if it doesn't make sense."
        logprob_positive_tokens = []
        logprob_negative_tokens = "NA"
        logprob_key = "logprob-clarity-TryToAnswer"
    else:
        instruction = f"You will receive of description of a quantity. You must reply YES if the following is satisfied and NO otherwise: {TASK_INSTRUCTIONS[task]}."
        logprob_positive_tokens = "YES"
        logprob_negative_tokens = "NO"
        logprob_key = f"logprob-clarity-{task.value}"

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction=instruction,
        format_question_into_prompt=format_question,
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_with_logprobs,
            logprob_key=logprob_key,
            logprob_positive_tokens=logprob_positive_tokens,
            logprob_negative_tokens=logprob_negative_tokens,
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
