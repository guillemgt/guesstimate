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
from retrieve_quantities import SingleValueModifier

# =============================
# Main Functions
# =============================

SYSTEM_PROMPT = """You will receive a list of descriptions of quantities, a value and an excerpt. Your task is to say whether the provided quantity is correct, according to the excerpt.
Reply ONLY with YES or NO."""


def main(
    input_path="data/pipeline/rewrite_description.json",
    output_path="data/pipeline/filter_correct.json",
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
        formatted_excerpt = question["found_excerpt"]
        formatted_question = " ".join(x for x in [question["rewritten"]["prompt"], question["rewritten"]["date"], question["rewritten"]["units"]] if x is not None)
        if 'single_value' in question['value']:
            modifier = question['value']['modifier']
            modifier = modifier if modifier in {SingleValueModifier.MORE_THAN, SingleValueModifier.LESS_THAN} else None
            value = question['value']['value']
            unit = question['value']['unit']
            formatted_answer = " ".join(str(x) for x in [modifier, value, unit] if x is not None)
        elif 'interval' in question['value']:
            min_value = question['value']['min_value']
            max_value = question['value']['max_value']
            unit = question['value']['unit']
            formatted_value = f"between {min_value} and {max_value}"
            formatted_answer = " ".join(str(x) for x in [formatted_value, unit] if x is not None)
        else:
            raise ValueError(f"Invalid value type: {question['value']}")
        formatted_answer = formatted_answer.capitalize()
        content = f"""# Excerpt
{formatted_excerpt}

# Question
{formatted_question}

# Answer
{formatted_answer}"""

        requests.append(
            {
                "model": "gpt-4o-mini",
                "messages": common_prompt_part + [{"role": "user", "content": content}],
                "temperature": temperature,
                "max_completion_tokens": 1,
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
        batch_call_id="filter_correct",
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

    correct = 0

    filetered_questions = []

    for question, seq_logprobs in zip(questions, seqs_logprobs):
        if not seq_logprobs:
            continue
        try:
            logprob_objects = seq_logprobs["content"][0]["top_logprobs"]
            for logprob_object in logprob_objects:
                if logprob_object["token"] == "YES":
                    logprob_Y = logprob_object["logprob"]
                elif logprob_object["token"] == "NO":
                    logprob_N = logprob_object["logprob"]

            logprobs = np.array([logprob_Y, logprob_N])
            probs = np.exp(logprobs)
            probs /= np.sum(probs)

            logprob_correct = np.log(probs[0]).item()

            if logprob_correct > -5.5:  # Based on manually examining outputs
                correct += 1
                filetered_questions.append(question)

            qs_and_logprobs.append(question | {"correct_logprob": logprob_correct})

        except Exception as e:
            print("Error:", e)
            print("Output:", seq_logprobs)
            continue

    print("Number of questions:", len(questions))
    print("Correct:", correct)

    print("Total input tokens:", input_tokens)
    print("Total output tokens:", output_tokens)
    INPUT_COST = 0.075 * 1e-6
    OUTPUT_COST = 0.300 * 1e-6
    print(f"Cost: ${input_tokens*INPUT_COST+output_tokens*OUTPUT_COST:.4f}")

    print("Reduced from", len(questions), "to", len(filetered_questions), "questions")

    # Write the modified questions with found excerpts
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(filetered_questions, f, ensure_ascii=False, indent=1)

    qs_and_logprobs.sort(key=lambda x: x["correct_logprob"], reverse=True)
    with open(
        output_path.replace(".json", "-logprobs.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(qs_and_logprobs, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

# Cost: $1.0962
# Reduced from 89777 to 3985 question
