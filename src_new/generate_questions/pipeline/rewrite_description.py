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

SYSTEM_PROMPT = """You are helping design a game about estimating quantities. You will receive a topic, an excerpt and a preliminary description of a quanitity mentioned in the excerpt. Your task is to rewrite the the description as a prompt for the game, making it clear what quantity is to be estimated without seeing the topic or excerpt, and providing additional necessary information such as date and units of measurement; make sure this information is NOT included in the prompt. The description should be clear enough that anyone would understand what they are being asked to estimate.
"""

EXAMPLES = [
    # {
    #     "input": {
    #         "topic": "Tropic of Capricorn",
    #         "found_excerpt": "See under circles of latitude for information.\nThere are approximately 10 hours, 41 minutes of daylight during the June solstice (Southern Hemisphere winter).",
    #         "description": "hours of daylight during the June solstice",
    #     },
    #     "output": {
    #         "description": "Estimate the daylight duration during the June solstice in the Tropic of Capricorn",
    #         "date": None,
    #         "units": "in minutes"
    #     }
    # },
    {
        "input": {
            "topic": "Stove",
            "found_excerpt": "Until well into the 19th century, \"stove\" was defined as a single heated room.\nCooking was performed over an open fire since nearly two million years ago. It is uncertain how fires were started at these times; some hypotheses include the removal of burning branches from wildfires, spark generation through hitting rocks, or accidental lighting through the chipping of stone tools.",
            "description": "number of years humans have been cooking over open fires",
        },
        "output": {
            "prompt": "Estimate how long humans have been cooking over open fires",
            "date": None,
            "units": "in years"
        },
    },
    # {
    #     "input": {
    #         "topic": "Moon",
    #         "found_excerpt": "A major geologic process that has affected the Moon's surface is impact cratering, with craters formed when asteroids and comets collide with the lunar surface. There are estimated to be roughly 300,000 craters wider than 1 km (0.6 mi) on the Moon's near side. Lunar craters exhibit a variety of forms, depending on their size.",
    #         "description": "number of craters wider than 1 km on the Moon",
    #     },
    #     "output": {
    #         "prompt": "Estimate the number of craters wider than 1 km on the Moon",
    #         "date": None,
    #         "units":  None
    #     },
    # },
    {
        "input": {
            "topic": "Cat",
            "found_excerpt": "In many countries, they are believed to have nine lives, but in Italy, Germany, Greece, Brazil and some Spanish-speaking regions, they are said to have seven lives, while in Arabic traditions, the number of lives is six.",
            "description": "number of lives cats are believed to have in some cultures (like Italy and Germany)",
        },
        "output": {
            "prompt": "Estimate the number of lives cats are believed to have in Italy and Germany",
            "date": None,
            "units":  None
        },
    },
    {
        "input": {
            "topic": "Plastic",
            "found_excerpt": "9.2 billion metric tons of plastic are estimated to have been made between 1950 and 2017, more than half of which has been produced since 2004.",
            "description": "total plastic produced between 1950 and 2017",
        },
        "output": {
            "prompt": "Estimate the total amount of plastic produced",
            "date": "between 1950 and 2017",
            "units":  "in metric tons"
        },
    },
    # {
    #     "input": {
    #         "topic": "Canada",
    #         "found_excerpt": "A record 405,000 immigrants were admitted in 2021. Canada leads the world in refugee resettlement; it resettled more than 47,600 in 2022. New immigrants settle mostly in major urban areas, such as Toronto, Montreal, and Vancouver.",
    #         "description": "number of refugees resettled in 2022",
    #     },
    #     "output": {
    #         "prompt": "Estimate the number of refugees resettled in Canada",
    #         "date": None,
    #         "units": "in 2022"
    #     },
    # },
    # {
    #     "input": {
    #         "topic": "Asteroid Belt",
    #         "found_excerpt": "Nonetheless, hundreds of thousands of asteroids are currently known, and the total number ranges in the millions or more, depending on the lower size cutoff. Over 200 asteroids are known to be larger than 100 km, and a survey in the infrared wavelengths has shown that the asteroid belt has between 700,000 and 1.",
    #         "description": "number of known asteroids larger than 100 km",
    #     },
    #     "output": {
    #         "prompt": "Estimate the number of known asteroids larger than 100 km",
    #         "date": None,
    #         "units": None
    #     },
    # },
    # {
    #     "input": {
    #         "topic": "Corn",
    #         "found_excerpt": "Maize is cultivated throughout the world; a greater weight of maize is produced each year than any other grain. In 2020, world production was 1.1 billion tonnes. It is afflicted by many pests and diseases; two major insect pests, European corn borer and corn rootworms, have each caused annual losses of a billion dollars in the US." ,
    #         "description": "world production of maize in 2020 (in tonnes)",
    #     },
    #     "output": {
    #         "prompt": "Estimate the world production of maize",
    #         "date": "in 2020",
    #         "units": "in tonnes"
    #     },
    # },
    {
        "input": {
            "topic": "Sweden",
            "found_excerpt": "Northern and central Sweden have several wide rivers known as alvar, commonly sourced within the Scandinavian Mountains. The longest river is Klaralven-Gota alv, which originates in Trondelag in central Norway, running 1,160 kilometres (720 mi) before it enters the sea at Gothenburg. In southern Sweden, narrower rivers known as aar are also common.",
            "description": "longest river in Sweden (in km)",
        },
        "output": {
            "prompt": "Estimate the length of the longest river in Sweden",
            "date": None,
            "units": "in km"
        },
    },
    {
        "input": {
            "topic": "Panda",
            "found_excerpt": "Copulation time ranges from 30 seconds to five minutes, but the male may mount her repeatedly to ensure successful fertilisation. The gestation period is somewhere between 95 and 160 days - the variability is due to the fact that the fertilized egg may linger in the reproductive system for a while before implanting on the uterine wall.",
            "description": "average days of gestation in giant pandas (in days)",
        },
        "output": {
            "prompt": "Estimate the average period of gestation in giant pandas",
            "date": None,
            "units": "in days"
        },
    },
    # {
    #     "input": {
    #         "topic": "Solar System",
    #         "found_excerpt": "The Sun is the Solar System's star and by far its most massive component. Its large mass (332,900 Earth masses), which comprises 99.",
    #         "description": "mass of the Sun compared to the mass of Earth",
    #     },
    #     "output": {
    #         "prompt": "Estimate the ratio between the mass of the Sun and the mass of Earth",
    #         "date": None,
    #         "units": None
    #     },
    # }
]
def show_input(x):
    return f'''## Topic

{x["topic"]}

## Excerpt
{x["found_excerpt"]}

## Description
{x["description"]}'''

class EstimationPrompt(BaseModel):
    prompt: str = Field(..., description='Game prompt for estimating of the quanitity, beginning with "Estimate " and not including units or dates of measurement. The description must be understandable without seeing the topic, excerpt or knowing the answer.')
    date: str | None = Field(..., description='Measurement date, beginning with "in ", "between ", "before ", etc., e.g. "in 2007". If no date is present, set to null.')
    units: str | None = Field(..., description='Measurement units, beginning with "in ", e.g. "in kg". If the quantity has no units, set to null.')

def main(
    input_path = "data/pipeline/filter_clear.json",
    output_path = "data/pipeline/rewrite_description.json",
    log_path = "data/pipeline/logs/",
    temperature = 0.01,
):

    # Load input questions and prompts
    with open(input_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    response_format_param = type_to_response_format_param(EstimationPrompt)

    common_prompt_part = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
    ] + sum((
        [
            {
                "role": "user",
                "content": show_input(example["input"])
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
        content = show_input(question)
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
        batch_call_id="rewrite_description",
        max_tokens_per_batch=35_000_000
    )

    input_tokens = sum([output["usage"]["prompt_tokens"] for output in outputs if output])
    output_tokens = sum([output["usage"]["completion_tokens"] for output in outputs if output])

    true_outputs = [output["choices"][0]["message"] if output else None for output in outputs ]

    print(len(true_outputs), len(questions))

    new_questions = []

    for question, true_output in zip(questions, true_outputs):
        if not true_output:
            continue
        try:
            fixed_content = json.dumps(complete_truncated_json(true_output["content"]), indent=4)
            true_output["content"] = fixed_content
            parsed = maybe_parse_content(
                response_format=EstimationPrompt,
                message=ChatCompletionMessage(**true_output)
            )

            new_questions.append(question | {
                "rewritten": parsed.model_dump()
            })
            
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

    

    print("Total input tokens:", input_tokens)
    print("Total output tokens:", output_tokens)
    INPUT_COST = 0.075 * 1e-6
    OUTPUT_COST = 0.300 * 1e-6
    print(f"Cost: ${input_tokens*INPUT_COST+output_tokens*OUTPUT_COST:.4f}")

    # Write the modified questions with found excerpts
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_questions, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

# $3.4859 for 89777 -> 35305