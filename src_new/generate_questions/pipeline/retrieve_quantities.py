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


SYSTEM_PROMPT = """You are an information processing man assisting in the creation of a trivia game about estimating numerical quantities of universally recognisable concepts.

Task: You will receive an article and reply with the information of *all* numerical quantities of concepts that are univerally recognizable.

Guidelines:
- The quantity must be of something that is universally recognizable: children can understand without having to be explained.
- Absolutely no technical terms.
- Only quantities that are known numerical quantities and whose value is mentioned EXPLICITLY in the article. Never count yourself.
- Specific dates or years are not considered quantities.
- No quantities whose value is extremely obvious (e.g., "number of days in a week").
- DO NOT REPEAT YOURSELF: do not repeat any quantities. If, by mistake, you do repeat yourself, stop and do not continue.
- The description must be precise. Anyone must be able to understand what it refers to without reading the article and be able to formulate a guess (not necessarily a good guess).
- If more than one estimate is given for a quantity, include only the most recent one.
- Include *all* quantities satisfying the above conditions.
- Before you include a quantity, check that it satisifies the guidelines."""

# Define types of comparisons for single-value quantities
class SingleValueModifier(str, Enum):
    EXACTLY = "exactly"
    APPROXIMATELY = "approximately"
    MORE_THAN = "more than"
    LESS_THAN = "less than"

# Define types of comparisons for interval quantities
class IntervalModifier(str, Enum):
    EXACTLY = "exactly"
    APPROXIMATELY = "approximately"

# Define a model for single-value or comparative quantities
class SingleValue(BaseModel):
    single_value: bool = Field(..., description="Specifies that the quantity is a single value and not an interval. Must be true")
    modifier: SingleValueModifier = Field(..., description="Modifier type (exactly, approximately, more than, less than)")
    unit: Optional[str] = Field(None, description="Unit of the quantity (e.g., 'kg', 'tres'). No numerical modifiers like 'million'. If no units are present, set to null")
    value: float | int = Field(..., description="The numerical value")

# Define a model for interval quantities
class IntervalValue(BaseModel):
    interval: bool = Field(..., description="Specifies that the quantity is an interval and not a single value. Must be true")
    modifier: IntervalModifier = Field(..., description="Modifier (exactly or approximately)")
    unit: Optional[str] = Field(None, description="Unit of the quantity (e.g., 'kg', 'tres'). No numerical modifiers like 'million'. If no units are present, set to null")
    min_value: float | int = Field(..., description="The minimum value of the interval")
    max_value: float | int = Field(..., description="The maximum value of the interval")

# Define the main Quantity class using Union
class Quantity(BaseModel):
    description: str = Field(..., description="Description of what quantity is being discussed (e.g., 'number of trees')")
    excerpt: str = Field(..., description="Excerpt from the text where the quantity is mentioned, containing the description and value of the quantity. Written exactly as in the text")
    
    # Union for the two quantity types
    value: Union[SingleValue, IntervalValue] = Field(..., description="Value of the quantity, depending on its type (single value or interval)")

class ListOfQuantities(BaseModel):
    quantities: list[Quantity]



def main(
    input_path = "data/wikipedia_dumps/",
    output_path = "data/pipeline/retrieve_quantities.json",
    log_path = "data/pipeline/logs/",
    temperature = 0.1,
):
    load_dotenv()

    # Generate the JSON schema
    response_format_param = type_to_response_format_param(ListOfQuantities)
    
    requests = []
    topics = []
    
    for file in tqdm(os.listdir(input_path)):
        if not file.endswith(".txt"):
            continue

        topic = file.replace(".txt", "")
        input_file = os.path.join(input_path, file)
        contents = f"## {topic}\n\n" + open(input_file, "r", encoding="utf-8").read()

        if " may refer to:" in contents: # Some disambiguations were not caught by the previous steps
            continue

        topics.append(topic)
        requests.append({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": contents
                }
            ],
            "temperature": temperature,
            "max_completion_tokens": 16_384,
            "n": 1,
            "response_format": response_format_param
        })

    batch_handler = OpenAIBatchHandler(
        api_key=os.getenv("OPENAI_API_KEY"),
        log_dir=log_path
    )
    outputs = batch_handler.upload_batches(
        requests=requests,
        endpoint="/v1/chat/completions",
        batch_call_id="retrieve_quantities",
        max_tokens_per_batch=35_000_000
    )

    input_tokens = sum([output["usage"]["prompt_tokens"] for output in outputs if output])
    output_tokens = sum([output["usage"]["completion_tokens"] for output in outputs if output])

    true_outputs = [output["choices"][0]["message"] if output else None for output in outputs ]
    qs = []

    print(len(true_outputs), len(requests), len(topics))

    for request, true_output, topic in zip(requests, true_outputs, topics):
        if not true_output:
            continue
        try:
            fixed_content = json.dumps(complete_truncated_json(true_output["content"]), indent=4)
            true_output["content"] = fixed_content
            qs.extend(
                [
                    {
                        "topic": topic,
                    } | q.model_dump()
                    for q in
                    maybe_parse_content(
                        response_format=ListOfQuantities,
                        message=ChatCompletionMessage(**true_output)
                    ).quantities
                ]
            )
        except Exception as e:
            print("Error:", e)
            print("Output:", true_output)
            continue

    print("Number of questions generated:", len(qs))

    print("Total input tokens:", input_tokens)
    print("Total output tokens:", output_tokens)
    INPUT_COST = 0.075 * 1e-6
    OUTPUT_COST = 0.300 * 1e-6
    print(f"Cost: ${input_tokens*INPUT_COST+output_tokens*OUTPUT_COST:.4f}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(qs, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()