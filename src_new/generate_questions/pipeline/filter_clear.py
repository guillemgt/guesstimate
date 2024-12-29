import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

SYSTEM_PROMPT = """You will receive of description of a quantity. Your task is to say whether:
- the question contains any technical or not well-known terms.
- the question makes a reference something, but it is not clear what without more context.
- the question makes sense without further context.
- anyone (not necessarily from America) would understand what the description refers to, so that it is clear what quantity is being talked about: if you were asked to guess the value of the quantity, could you even?"""

EXAMPLES = [
    {
        "input": "Silicone: operating temperature range for silicone encapsulation",
        "output": {
            "technical_terms": True,
            "ambiguous_reference": False,
            "makes_sense": True,
            "clear": False
        },
    },
    {
        "input": "Chicken (food): tonnes of meat produced in 2021",
        "output": {
            "technical_terms": False,
            "ambiguous_reference": False,
            "makes_sense": True,
            "clear": True
        },
    },
    {
        "input": "Picnic basket: number of people served by the picnic hamper",
        "output": {
            "technical_terms": False,
            "ambiguous_reference": True,
            "makes_sense": False,
            "clear": False
        },
    },
]

class DescriptionInformation(BaseModel):
    technical_terms: bool = Field(..., description="Whether the question contains any technical or not well-known terms.")
    ambiguous_reference: bool = Field(..., description="Whether the question makes a reference something, but it is not clear what without more context.")
    makes_sense: bool = Field(..., description="Whether the question makes sense without further context.")
    clear: bool = Field(..., description="Whether anyone (not necessarily from America) would understand what the description refers to, so that it is clear what quantity is being talked about. If providing measurement units would make the description clear, treat it as good.")

def main(
    input_path = "data/pipeline/find_excerpt.json",
    output_path = "data/pipeline/filter_clear.json",
    log_path = "data/pipeline/logs/",
    temperature = 0.0,
):

    # Load input questions and prompts
    with open(input_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    response_format_param = type_to_response_format_param(DescriptionInformation)

    common_prompt_part = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
    ] + sum((
        [
            {
                "role": "user",
                "content": example["input"]
            },
            {
                "role": "assistant",
                "content": json.dumps(example["output"], indent=4)
            },
        ] for example in EXAMPLES
    ), [])

    # Form the prompts
    requests = []
    for question in questions:
        content = question["topic"] + ": " + question["description"]
        if question["value"]["unit"] is not None:
            content += f" (in {question['value']['unit']})"
        requests.append({
            "model": "gpt-4o-mini",
            "messages": common_prompt_part + [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": temperature,
            "max_completion_tokens": 64,
            "n": 1,
            "response_format": response_format_param,
            # "logprobs": True,
            # "top_logprobs": 20,
        })

    batch_handler = OpenAIBatchHandler(
        api_key=os.getenv("OPENAI_API_KEY"),
        log_dir=log_path
    )
    outputs = batch_handler.upload_batches(
        requests=requests,
        endpoint="/v1/chat/completions",
        batch_call_id="filter_clear",
        max_tokens_per_batch=35_000_000
    )

    input_tokens = sum([output["usage"]["prompt_tokens"] for output in outputs if output])
    output_tokens = sum([output["usage"]["completion_tokens"] for output in outputs if output])

    true_outputs = [output["choices"][0]["message"] if output else None for output in outputs ]
    qs = []

    print(len(true_outputs), len(questions))

    non_technical = 0
    non_ambiguous = 0
    makes_sense = 0
    clear = 0

    filetered_questions = []

    for question, true_output in zip(questions, true_outputs):
        if not true_output:
            continue
        try:
            fixed_content = json.dumps(complete_truncated_json(true_output["content"]), indent=4)
            true_output["content"] = fixed_content
            parsed = maybe_parse_content(
                response_format=DescriptionInformation,
                message=ChatCompletionMessage(**true_output)
            )
            if parsed.technical_terms:
                non_technical += 1
            if parsed.ambiguous_reference:
                non_ambiguous += 1
            if parsed.makes_sense:
                makes_sense += 1
            if parsed.clear:
                clear += 1

            if parsed.clear and not parsed.technical_terms and parsed.makes_sense:
                filetered_questions.append(question)
            
            # if parsed.clear and parsed.technical_terms:
            #     print("Clear and technical:", question)
            # if parsed.clear and parsed.ambiguous_reference:
            #     print("Clear and ambiguous:", question)

            # if not parsed.clear:
            #     content = question["topic"] + ": " + question["description"]
            #     if question["value"]["unit"] is not None:
            #         content += f" (in {question['value']['unit']})"
            #     print(content)
            
        except Exception as e:
            print("Error:", e)
            print("Output:", true_output)
            continue

    print("Number of questions:", len(questions))
    print("Non-technical:", non_technical)
    print("Non-ambiguous:", non_ambiguous)
    print("Makes sense:", makes_sense)
    print("Clear:", clear)

    

    print("Total input tokens:", input_tokens)
    print("Total output tokens:", output_tokens)
    INPUT_COST = 0.075 * 1e-6
    OUTPUT_COST = 0.300 * 1e-6
    print(f"Cost: ${input_tokens*INPUT_COST+output_tokens*OUTPUT_COST:.4f}")

    print("Reduced from", len(questions), "to", len(filetered_questions), "questions")

    # Write the modified questions with found excerpts
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filetered_questions, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

# $3.4859 for 89777 -> 35305