import sys
import os
from dataclasses import dataclass, asdict
import numpy as np
from typing import Any, Callable
import asyncio
from collections import defaultdict

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


def parallelize(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    stages: list[Callable] | None = None,
) -> str:
    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    with open(input_file, "r", encoding="utf-8") as f:
        questions = json.load(f)
        assert all("uuid" in question for question in questions)

    async def run_things_in_parallel():
        tasks = []
        for i, stage in enumerate(stages):
            output_file_, log_file_ = output_and_log_files(
                None, None, pipeline_step, prefix=f".{i:02}"
            )

            tasks.append(
                asyncio.to_thread(
                    stage,
                    input_file=input_file,
                    output_file=output_file_,
                    log_file=log_file_,
                    pipeline_step=pipeline_step,
                )
            )

        task_output_files = await asyncio.gather(*tasks)

        uuid_to_questions = defaultdict(dict)
        for file in task_output_files:
            with open(file, "r", encoding="utf-8") as f:
                questions = json.load(f)
                for question in questions:
                    uuid_to_questions[question["uuid"]] |= question

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(list(uuid_to_questions.values()), f, ensure_ascii=False, indent=1)

    asyncio.run(run_things_in_parallel())
