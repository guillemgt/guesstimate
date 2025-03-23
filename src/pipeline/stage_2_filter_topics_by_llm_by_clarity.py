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


def filter_topic_by_clarity(
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

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction="Answer only YES if everyone would know what this is, otherwise NO.",
        format_question_into_prompt=lambda x: x["_"],
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_with_logprobs,
            logprob_key="logprob-topic-clarity",
            logprob_positive_tokens="YES",
            logprob_negative_tokens="NO",
            completion_kwargs=dict(
                model=model,
            ),
        ),
        filter_questions=lambda topics: [
            t
            for t in topics
            if t["logprob-topic-clarity"] is not None
            and t["logprob-topic-clarity"] > logprob_threshold
        ],
        examples=[],
        sort_by_key="logprob-topic-clarity",
    )
