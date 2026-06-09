import sys
import os
from enum import Enum

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enum import Enum

from functools import partial
from utils.input_output import output_and_log_files
from pipeline.general.generic_api_step import (
    generic_api_processing_step,
    fetch_api_response_and_process_float_result,
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
    ClarityType.NoTechnicalTerms: "the description does not contain any technical terms or any terms that are not known to a wide audience",
    ClarityType.MakesSenseWithoutContext: "the description makes sense without any additional context",
    ClarityType.LaypersonCanGuess: "anyone (not necessarily from America) would understand what the description refers to, so that it is clear what quantity is being talked about, and they would be able to make a guess the value of the quantity (possibly a bad guess)",
    ClarityType.MakesSense: "the description of the quantity makes sense",
    ClarityType.OverallClear: "the description of the quantity is clear and unambiguous, so that it is clear what quantity is being talked about",
    ClarityType.OverallClearDetailed: "it is clear and unambiguous what quantity is being talked about, the entity or concept referenced is widely known or can reasonably be deduced, and the description does not contain any name that will not be known by most people. It is NOT necessary for people to know the value of the quantity.",
}


def format_question(question: dict) -> str | None:
    if "rewritten-description" in question:
        if question["rewritten-description"] is None:
            return None
        prompt = question["rewritten-description"]["description"]
        if prompt.startswith("Estimate "):
            prompt = prompt[len("Estimate ") :]
        parts = [
            prompt.strip(),
            question["rewritten-description"]["time_period"],
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
    model="gpt-5-mini",
    reasoning_effort="low",
    task: ClarityType = ClarityType.OverallClear,
    score_threshold: float = 0.0,
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    if task == ClarityType.TryToAnswer:
        instruction = "Reply ONLY with the value of the quantity you're given a description of or NA if it doesn't make sense."
        raise NotImplementedError("TryToAnswer clarity filtering not implemented yet.")
    else:
        instruction = f"You will receive of description of a quantity. Reply ONLY with a score from 0 to 100 describing how well the description satisfies the following criterion: {TASK_INSTRUCTIONS[task]}."

    score_key = task.value

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction=instruction,
        format_question_into_prompt=format_question,
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_float_result,
            min_value=0.0,
            max_value=100.0,
            score_key=score_key,
            completion_kwargs=dict(
                model=model,
                reasoning_effort=reasoning_effort,
            ),
        ),
        filter_questions=lambda questions: [
            question
            for question in questions
            if question[score_key] is not None and question[score_key] > score_threshold
        ],
        examples=[],
        sort_by_key=score_key,
    )

    return output_file
