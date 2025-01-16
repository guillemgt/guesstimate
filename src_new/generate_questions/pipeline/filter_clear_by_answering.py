import sys
import os
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import BaseModel, Field
from typing import Tuple, Union, Optional
from enum import Enum
from tqdm import tqdm
from dotenv import load_dotenv

from openai.types.chat import ChatCompletionMessage
from openai.lib._parsing import type_to_response_format_param, maybe_parse_content
from utils.openai import OpenAIBatchHandler
from utils.json import complete_truncated_json
import json

# =============================
# Main Functions
# =============================

SYSTEM_PROMPT = """Reply ONLY with the value of this quantity or NA if it doesn't make sense"""


def main(
    input_path="data/pipeline/find_excerpt.json",
    output_path="data/pipeline/filter_clear_by_answering.json",
    log_path="data/pipeline/logs/",
    temperature=0.0,
):

    # Load input questions and prompts
    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    common_prompt_part = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # Form the prompts
    requests = []
    for question in questions:
        content = question["topic"] + ": " + question["description"]
        if question["value"]["unit"] is not None:
            content += f" (in {question['value']['unit']})"
        requests.append(
            {
                "model": "gpt-4o-mini",
                "messages": common_prompt_part + [{"role": "user", "content": content}],
                "temperature": temperature,
                "max_completion_tokens": 64,
                "n": 1,
                "logprobs": True,
                "top_logprobs": 20,
            }
        )

    batch_handler = OpenAIBatchHandler(
        api_key=os.getenv("OPENAI_API_KEY"), log_dir=log_path
    )
    outputs = batch_handler.upload_batches(
        requests=requests,
        endpoint="/v1/chat/completions",
        batch_call_id="filter_clear_by_answering",
        max_tokens_per_batch=35_000_000,
    )

    input_tokens = sum(
        [output["usage"]["prompt_tokens"] for output in outputs if output]
    )
    output_tokens = sum(
        [output["usage"]["completion_tokens"] for output in outputs if output]
    )

    print(outputs[0])
    seqs_logprobs = [
        output["choices"][0]["logprobs"] if output else None for output in outputs
    ]

    qs_and_logprobs = []

    print(len(seqs_logprobs), len(questions))

    clear = 0

    filetered_questions = []

    for question, seq_logprobs in zip(questions, seqs_logprobs):
        if not seq_logprobs:
            continue
        try:
            logprob_objects = seq_logprobs["content"][0]["top_logprobs"]
            logprob_NA = -np.inf
            for logprob_object in logprob_objects:
                if logprob_object["token"] == "NA":
                    logprob_NA = logprob_object["logprob"]

            if logprob_NA < -0.69:  # Based on manually examining outputs
                clear += 1
                filetered_questions.append(question)

            qs_and_logprobs.append(question | {"unclear_logprob": logprob_NA})

        except Exception as e:
            print("Error:", e)
            print("Output:", seq_logprobs)
            continue

    print("Number of questions:", len(questions))
    print("Clear:", clear)

    print("Total input tokens:", input_tokens)
    print("Total output tokens:", output_tokens)
    INPUT_COST = 0.075 * 1e-6
    OUTPUT_COST = 0.300 * 1e-6
    print(f"Cost: ${input_tokens*INPUT_COST+output_tokens*OUTPUT_COST:.4f}")

    print("Reduced from", len(questions), "to", len(filetered_questions), "questions")

    # Write the modified questions with found excerpts
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(filetered_questions, f, ensure_ascii=False, indent=1)

    qs_and_logprobs.sort(key=lambda x: -x["unclear_logprob"], reverse=True)
    with open(
        output_path.replace(".json", "-logprobs.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(qs_and_logprobs, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

# Cost: $1.0962
# Reduced from 89777 to 3985 question
