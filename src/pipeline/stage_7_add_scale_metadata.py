import sys
import os

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
from pipeline.stage_6_filter_clarity import format_question

SYSTEM_PROMPT = """You are helping design a game. You will receive a question about estimating a quantity. Your task is to reply with information about what range of values for the quantity even make sense (EVEN IF THEY ARE INFEASIBLE OR UNREALISTIC). So reply based ONLY on the units of the quantity being asked, not its actual value. These will be used for scoring players' answers in the game (namely, to distinguih between logarithmic and uniform scales).

Examples of ranges:
if the question asks about distances in km: [0, +infinity) since negative distances don't make sense
if the question asks about temperatures in Celsius: [-273.15, +infinity) since -273.15 is absolute zero
if the question asks about ages in years: [0, +infinity) since negative ages don't make sense
if the question asks about probabilities: [0, 1] since probabilities are always between 0 and 1

More examples:
if the question asks about percentages of a population: [0, 100]
if the question asks about percentages of improper fractions (e.g. rate of change): (-infty, +infty)
if the question asks about masses in kg: [0, +infinity)
if the question asks about degrees in angles: [0, 360]
etc.

Don't be pedantic, e.g. saying speed is [0, 3e8) m/s is not helpful. Just say [0, +infinity) m/s.

Remember: Reply based ONLY on the units of the quantity being asked, not its actual value."""


class Interval(BaseModel):
    lower_bound: int | float | None = Field(
        ...,
        description="The lower bound of the interval, or null if it is negative infinity",
    )
    upper_bound: int | float | None = Field(
        ...,
        description="The upper bound of the interval, or null if it is positive infinity",
    )


EXAMPLES = [
    {
        "input": {
            "rewritten-description": {
                "prompt": "Estimate the number of people who have ever lived.",
                "date": None,
                "units": None,
            },
        },
        "output": Interval(
            lower_bound=0,
            upper_bound=None,
        ),
    },
    {
        "input": {
            "rewritten-description": {
                "prompt": "Estimate the percentage of the population of Finland that owns a sauna",
                "date": None,
                "units": "in %",
            },
        },
        "output": Interval(
            lower_bound=0,
            upper_bound=100,
        ),
    },
    {
        "input": {
            "rewritten-description": {
                "prompt": "Estimate the temperature of the sun",
                "date": None,
                "units": "in °C",
            },
        },
        "output": Interval(
            lower_bound=0,
            upper_bound=None,
        ),
    },
    {
        "input": {
            "rewritten-description": {
                "prompt": "Estimate the standard number of ECTS credits required for a master's degree in the European Higher Education Area",
                "date": None,
                "units": "in credits",
            },
        },
        "output": Interval(
            lower_bound=0,
            upper_bound=None,
        ),
    },
]


def add_scale_metadata(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-4o-mini",
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction=SYSTEM_PROMPT,
        format_question_into_prompt=format_question,
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_with_structured_outputs,
            response_type=Interval,
            response_key="scale-interval",
            completion_kwargs=dict(
                model=model,
                temperature=0.0,
                max_completion_tokens=256,
            ),
        ),
        filter_questions=lambda questions: [
            question
            for question in questions
            for answer in [question["rewritten-description"]["answer"]]
            if print(answer)
            or (
                (
                    question["scale-interval"]["lower_bound"] is None
                    or question["scale-interval"]["lower_bound"]
                    < answer.get("value", answer.get("min_value"))
                )
                and (
                    question["scale-interval"]["upper_bound"] is None
                    or question["scale-interval"]["upper_bound"]
                    > answer.get("value", answer.get("max_value"))
                )
            )
        ],
        examples=EXAMPLES,
    )

    return output_file
