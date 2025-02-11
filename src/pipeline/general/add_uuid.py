import sys
import os
from dataclasses import dataclass, asdict
import numpy as np
from typing import Any
import uuid

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


def add_uuid(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
) -> str:
    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    # Load input questions and prompts
    with open(input_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    for question in questions:
        question["uuid"] = uuid.uuid4().hex

    # Write the modified questions with found excerpts
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=1)

    return output_file
