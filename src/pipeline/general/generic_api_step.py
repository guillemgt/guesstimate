import sys
import os
from dataclasses import dataclass, asdict
import numpy as np
from typing import Any

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

# TODO: Include prompt examples
# TODO: Support e.g. retrieving quantities (1 input -> multiple outputs)

# =============================
# Response types
# =============================


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float

    def from_openai_outputs(outputs: dict) -> str:
        input_tokens = sum(
            [output["usage"]["prompt_tokens"] for output in outputs if output]
        )
        output_tokens = sum(
            [output["usage"]["completion_tokens"] for output in outputs if output]
        )

        model = outputs[0]["model"]
        if "gpt-4o-mini" in model:
            input_cost = 0.075 * 1e-6
            output_cost = 0.300 * 1e-6
        elif "gpt-4o" in model:
            input_cost = 1.25 * 1e-6
            output_cost = 5.0 * 1e-6
        else:
            input_cost = 0.0
            output_cost = 0.0
        usage = Usage(
            input_tokens,
            output_tokens,
            input_tokens * input_cost,
            output_tokens * output_cost,
        )
        return usage


def fetch_api_response_and_process_with_structured_outputs(
    system_prompt: str,
    user_prompts: list[str],
    inprompt_examples: list[tuple[str, BaseModel]],
    response_type: type[BaseModel],
    log_path: str,
    completion_kwargs: Optional[dict] = None,
    response_key: Optional[str] = None,
) -> tuple[list[dict], Usage]:
    # Form the request
    common_prompt_part = [
        {"role": "system", "content": system_prompt},
    ]
    response_format_param = type_to_response_format_param(response_type)
    model = completion_kwargs.pop("model", "gpt-4o-mini")
    requests = []
    for user_prompt in user_prompts:
        requests.append(
            {
                "model": model,
                "messages": common_prompt_part
                + sum(
                    (
                        [
                            {"role": "user", "content": user_prompt_},
                            {
                                "role": "assistant",
                                "content": example_output.model_dump_json(indent=4),
                            },
                        ]
                        for user_prompt_, example_output in inprompt_examples
                    ),
                    [],
                )
                + [{"role": "user", "content": user_prompt}],
                **(completion_kwargs or {}),
                "n": 1,
                "response_format": response_format_param,
            }
        )

    # Fetch the API response
    batch_handler = OpenAIBatchHandler(
        api_key=os.getenv("OPENAI_API_KEY"), log_dir=log_path
    )
    outputs = batch_handler.upload_batches(
        requests=requests,
        endpoint="/v1/chat/completions",
        batch_call_id="filter_correct",
        max_tokens_per_batch=35_000_000,
        max_requests_per_batch=20_000,
    )
    usage = Usage.from_openai_outputs(outputs)
    assert len(outputs) == len(user_prompts)

    # Process the response
    true_outputs = [
        output["choices"][0]["message"] if output else None for output in outputs
    ]
    return_dicts = []
    for true_output in true_outputs:
        if not true_output:
            return_dicts.append({response_key: None} if response_key else {})
            continue
        try:
            fixed_content = json.dumps(
                complete_truncated_json(true_output["content"]), indent=4
            )
            true_output["content"] = fixed_content
            parsed = maybe_parse_content(
                response_format=response_type,
                message=ChatCompletionMessage(**true_output),
            ).model_dump()

            return_dicts.append({response_key: parsed} if response_key else parsed)

        except Exception as e:
            print("Error:", e)
            print("Output:", true_output)
            return_dicts.append({response_key: None} if response_key else {})

    return return_dicts, usage


def fetch_api_response_and_process_with_logprobs(
    system_prompt: str,
    user_prompts: list[str],
    inprompt_examples: list[tuple[str, str]],
    logprob_key: str,
    logprob_positive_tokens: str | list[str],
    logprob_negative_tokens: str | list[str] | None,
    log_path: str,
    completion_kwargs: Optional[dict] = None,
) -> tuple[list[dict], Usage]:
    if isinstance(logprob_positive_tokens, str):
        logprob_positive_tokens = [logprob_positive_tokens]

    if isinstance(logprob_negative_tokens, str):
        logprob_negative_tokens = [logprob_negative_tokens]
    elif logprob_negative_tokens is None:
        logprob_negative_tokens = []

    # Form the request
    common_prompt_part = [
        {"role": "system", "content": system_prompt},
    ]
    model = completion_kwargs.pop("model", "gpt-4o-mini")
    requests = []
    for user_prompt in user_prompts:
        requests.append(
            {
                "model": model,
                "messages": common_prompt_part
                + sum(
                    (
                        [
                            {"role": "user", "content": example_input},
                            {
                                "role": "assistant",
                                "content": example_output,
                            },
                        ]
                        for example_input, example_output in inprompt_examples
                    ),
                    [],
                )
                + [{"role": "user", "content": user_prompt}],
                **(completion_kwargs or {}),
                "n": 1,
                "max_completion_tokens": 1,
                "logprobs": True,
                "top_logprobs": 20,
            }
        )

    # Fetch the API response
    batch_handler = OpenAIBatchHandler(
        api_key=os.getenv("OPENAI_API_KEY"), log_dir=log_path
    )
    outputs = batch_handler.upload_batches(
        requests=requests,
        endpoint="/v1/chat/completions",
        batch_call_id="filter_correct",
        max_tokens_per_batch=35_000_000,
    )
    usage = Usage.from_openai_outputs(outputs)
    assert len(outputs) == len(user_prompts)

    # Process the response
    seqs_logprobs = [
        output["choices"][0]["logprobs"] if output else None for output in outputs
    ]
    return_dicts = []
    for seq_logprobs in seqs_logprobs:
        if not seq_logprobs:
            return_dicts.append({logprob_key: None})
            continue
        try:
            logprob_objects = seq_logprobs["content"][0]["top_logprobs"]
            prob_positive = 0.0
            prob_negative = 0.0
            prob_positive_is_present = False
            for logprob_object in logprob_objects:
                if logprob_object["token"] in logprob_positive_tokens:
                    prob_positive_is_present = True
                    prob_positive += np.exp(logprob_object["logprob"])
                elif logprob_object["token"] in logprob_negative_tokens:
                    prob_negative += np.exp(logprob_object["logprob"])

            if len(logprob_negative_tokens) > 0:
                probs = np.array([prob_positive, prob_negative])
                if np.sum(probs) == 0:
                    probs = (
                        np.array([1.0, 0.0])
                        if prob_positive_is_present
                        else np.array([0.0, 1.0])
                    )
                probs /= np.sum(probs)
                prob_positive = probs[0]

            if len(logprob_positive_tokens) == 0:
                prob_positive = 1.0 - prob_negative

            logprob_correct = np.log(prob_positive).item()

            return_dicts.append({logprob_key: logprob_correct})

        except Exception as e:
            print("Error:", e)
            print("Output:", seq_logprobs)
            return_dicts.append({logprob_key: None})

    return return_dicts, usage


# =============================
# Main Functions
# =============================


def generic_api_processing_step(
    input_path: str,
    output_path: str,
    log_path: str,
    instruction: str,
    examples: list[tuple[Any, Any]],
    format_question_into_prompt: callable,
    fetch_api_response_and_process: callable,
    filter_questions: callable,
    sort_by_key: str | None = None,
):
    # Load input questions and prompts
    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Form the prompts
    user_prompts = [format_question_into_prompt(question) for question in questions]
    api_responses_dict_to_add, usage = fetch_api_response_and_process(
        system_prompt=instruction,
        user_prompts=user_prompts,
        log_path=log_path,
        inprompt_examples=[
            (format_question_into_prompt(example["input"]), example["output"])
            for example in examples
        ],
    )
    new_questions = [
        (question if isinstance(question, dict) else {"_": question})
        | api_response_dict
        for question, api_response_dict in zip(questions, api_responses_dict_to_add)
    ]
    if sort_by_key:
        new_questions = sorted(
            new_questions,
            key=lambda x: x[sort_by_key] if x[sort_by_key] is not None else -np.inf,
        )

    filtered_questions = filter_questions(new_questions)

    print("Number of original entries:", len(questions))
    print("Number of filtered entries:", len(filtered_questions))

    print("Total input tokens:", usage.input_tokens)
    print("Total output tokens:", usage.output_tokens)
    print(f"Cost: ${usage.input_cost+usage.output_cost:.4f}")

    # Write the modified questions with found excerpts
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(filtered_questions, f, ensure_ascii=False, indent=1)

    with open(
        output_path.replace(".json", ".unfiltered.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(new_questions, f, ensure_ascii=False, indent=1)

    with open(
        output_path.replace(".json", ".metadata.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(
            asdict(usage)
            | {
                "entries_before": len(questions),
                "entries_after": len(filtered_questions),
            },
            f,
            ensure_ascii=False,
            indent=4,
        )
