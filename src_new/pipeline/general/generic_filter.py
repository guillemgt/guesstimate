import sys
import os
from dataclasses import dataclass, asdict
import numpy as np
from typing import Any

from pydantic import BaseModel, Field
from typing import Tuple, Union, Optional
from enum import Enum
from tqdm import tqdm
from dotenv import load_dotenv

from openai.types.chat import ChatCompletionMessage
from openai.lib._parsing import type_to_response_format_param, maybe_parse_content
from utils.openai import OpenAIBatchHandler
from utils.json import complete_truncated_json
from utils.input_output import output_and_log_files
import json


GeneralizedKey = str | list[str] | list[tuple[str, float]]
KeyWithThreshold = tuple[GeneralizedKey, float]


def generic_filter(
    input_file: str,
    filters: list[KeyWithThreshold],
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    ignore_zeros: bool = False,
) -> str:
    """
    Filters according to wether a linear combination of some keys is above a certain threshold.
    filters can be:
    - a tuple of a key and a threshold
    - a tuple of a list of keys and a threshold (the keys are summed up)
    - a tuple of a list of tuples of keys and weights and a threshold (the keys are linearly combined)
    """

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    # Process filters, convert them to a standard format
    filters = [
        (
            (
                [(generalized_key, 1.0)]
                if isinstance(generalized_key, str)
                else [
                    (
                        (generalized_key_term, 1.0)
                        if isinstance(generalized_key_term, str)
                        else generalized_key_term
                    )
                    for generalized_key_term in generalized_key
                ]
            ),
            threshold,
        )
        for generalized_key, threshold in filters
    ]

    # Load input questions and prompts
    with open(input_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    filtered_questions = [
        question
        for question in questions
        if all(
            [
                sum([weight * question[key] for key, weight in generalized_key])
                > threshold
                or (
                    ignore_zeros
                    and sum([weight * question[key] for key, weight in generalized_key])
                    == 0.0
                )  # TODO: This is a hack because sometimes the logprobs where set to 0.0 erroneously
                for generalized_key, threshold in filters
            ]
        )
    ]

    print("Number of original entries:", len(questions))
    print("Number of filtered entries:", len(filtered_questions))

    # Write the modified questions with found excerpts
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered_questions, f, ensure_ascii=False, indent=1)

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
            indent=4,
        )

    return output_file
