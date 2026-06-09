import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import BaseModel, Field
from typing import Union, Optional
from enum import Enum

from functools import partial
from utils.input_output import output_and_log_files
from pipeline.general.generic_api_step import (
    generic_api_processing_step,
    fetch_api_response_and_process_with_structured_outputs,
)

SYSTEM_PROMPT = """You are an information processing man assisting in the creation of a trivia game about estimating numerical quantities of universally recognisable concepts.

Task: You will receive an article and reply with the information of *all* numerical quantities of concepts that are univerally recognizable.

Guidelines:
- The quantity must be of something that is universally recognizable: children can understand without having to be explained.
- Absolutely no technical terms.
- Only quantities that are known numerical quantities and whose value is mentioned EXPLICITLY in the article. Never count yourself.
- Specific dates or years are not considered quantities.
- No quantities whose value is extremely obvious (e.g., "number of days in a week").
- DO NOT REPEAT YOURSELF: do not repeat any quantities.
- The description must be precise and stand-alone. Anyone must be able to understand what it refers to without reading the article and be able to formulate a guess (not necessarily a good guess).
- If more than one estimate is given for a quantity, include only the most recent one. If a measurement is given in different units, include only metric system units.
- Include *all* quantities satisfying the above conditions.
- Before you include a quantity, check that it satisifies the guidelines."""


# Define structured output schema
class ValueModifier(str, Enum):
    EXACTLY = "exactly"
    APPROXIMATELY = "approximately"
    MORE_THAN = "more than"
    LESS_THAN = "less than"


# Define a model for single-value or comparative quantities
class QuantityValue_(BaseModel):
    modifier: ValueModifier = Field(
        ...,
        description="Modifier type (exactly, approximately, more than, less than). Only use 'more than' and 'less than' if only one bound is given, otherwise use 'exactly' or 'approximately' and provide an interval in the value field",
    )
    value_or_interval: float | int | list[int] | list[float] = Field(
        ...,
        description="The numerical value, or a pair of numerical values representing an interval.",
    )

    def __str__(self):
        if (
            isinstance(self.value_or_interval, list)
            and len(set(self.value_or_interval)) == 1
        ):
            self.value_or_interval = self.value_or_interval[0]
        if not isinstance(self.value_or_interval, list):
            return " ".join(
                [
                    x
                    for x in [
                        (self.modifier if self.modifier != "exactly" else ""),
                        str(self.value_or_interval),
                    ]
                    if x
                ]
            )
        else:
            return " ".join(
                [
                    x
                    for x in [
                        (self.modifier if self.modifier != "exactly" else ""),
                        "between",
                        str(self.value_or_interval[0]),
                        "and",
                        str(self.value_or_interval[1]),
                    ]
                    if x
                ]
            )


class QuantityValue(BaseModel):
    modifier: ValueModifier = Field(
        ...,
        description="Modifier type (exactly, approximately, more than, less than). Only use 'more than' and 'less than' if only one bound is given, otherwise use 'exactly' or 'approximately' and provide an interval in the value field",
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of the quantity (e.g., 'kg', 'tres'). No numerical modifiers like 'million'. If no units are present, set to null",
    )
    value_or_interval: float | int | list[int] | list[float] = Field(
        ...,
        description="The numerical value, or a pair of numerical values representing an interval.",
    )

    def __str__(self):
        if (
            isinstance(self.value_or_interval, list)
            and len(set(self.value_or_interval)) == 1
        ):
            self.value_or_interval = self.value_or_interval[0]
        if not isinstance(self.value_or_interval, list):
            return " ".join(
                [
                    x
                    for x in [
                        (self.modifier if self.modifier != "exactly" else ""),
                        str(self.value_or_interval),
                        self.unit,
                    ]
                    if x
                ]
            )
        else:
            return " ".join(
                [
                    x
                    for x in [
                        (self.modifier if self.modifier != "exactly" else ""),
                        "between",
                        str(self.value_or_interval[0]),
                        "and",
                        str(self.value_or_interval[1]),
                        self.unit,
                    ]
                    if x
                ]
            )


# Define the main Quantity class using Union
class Quantity(BaseModel):
    description: str = Field(
        ...,
        description="Description of what quantity is being discussed (e.g., 'number of trees')",
    )
    excerpt: str = Field(
        ...,
        description="Excerpt from the text where the quantity is mentioned, containing the description and value of the quantity. Written exactly as in the text",
    )
    value: QuantityValue = Field(
        ...,
        description="Value of the quantity",
    )


class ListOfQuantities(BaseModel):
    quantities: list[Quantity]


def mine_quantities(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-5-mini",
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
        format_question_into_prompt=lambda x: open(
            x["topic_dump_path"], "r", encoding="utf-8"
        ).read(),
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_with_structured_outputs,
            response_type=ListOfQuantities,
            response_key=None,
            completion_kwargs=dict(
                model=model,
                reasoning_effort="minimal",
                max_completion_tokens=32_768,
            ),
        ),
        filter_questions=lambda topics_and_quantities: [
            {"topic": x["topic"]} | quantity
            for x in topics_and_quantities
            for quantity in x.get("quantities", [])
        ],
        examples=[],
    )

    return output_file
