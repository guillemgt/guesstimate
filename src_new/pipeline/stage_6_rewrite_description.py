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

SYSTEM_PROMPT = """You are helping design a game about estimating quantities. You will receive a topic, an excerpt and a preliminary description of a quanitity mentioned in the excerpt. Your task is to rewrite the the description as a prompt for the game, making it clear what quantity is to be estimated without seeing the topic or excerpt, and providing additional necessary information such as date and units of measurement; make sure this information is NOT included in the prompt. **The description should be clear enough that anyone would understand what they are being asked to estimate without seeing the topic or excerpt**."""


class EstimationPrompt(BaseModel):
    prompt: str = Field(
        ...,
        description='Game prompt for estimating of the quanitity, beginning with "Estimate " and NOT including units or dates of measurement. The description must be understandable without seeing the topic, excerpt or knowing the answer.',
    )
    date: str | None = Field(
        ...,
        description='Measurement date, beginning with "in ", "between ", "before ", etc., e.g. "in 2007". If no date is present, set to null.',
    )
    units: str | None = Field(
        ...,
        description='Measurement units, beginning with "in ", e.g. "in kg". If the quantity has no units, set to null.',
    )


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
            "found_excerpt": 'Until well into the 19th century, "stove" was defined as a single heated room.\nCooking was performed over an open fire since nearly two million years ago. It is uncertain how fires were started at these times; some hypotheses include the removal of burning branches from wildfires, spark generation through hitting rocks, or accidental lighting through the chipping of stone tools.',
            "description": "number of years humans have been cooking over open fires",
        },
        "output": EstimationPrompt(
            prompt="Estimate how long humans have been cooking over open fires",
            date=None,
            units="in years",
        ),
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
        "output": EstimationPrompt(
            prompt="Estimate the number of lives cats are believed to have in Italy and Germany",
            date=None,
            units=None,
        ),
    },
    {
        "input": {
            "topic": "Plastic",
            "found_excerpt": "9.2 billion metric tons of plastic are estimated to have been made between 1950 and 2017, more than half of which has been produced since 2004.",
            "description": "total plastic produced between 1950 and 2017",
        },
        "output": EstimationPrompt(
            prompt="Estimate the total amount of plastic produced",
            date="between 1950 and 2017",
            units="in metric tons",
        ),
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
        "output": EstimationPrompt(
            prompt="Estimate the length of the longest river in Sweden",
            date=None,
            units="in km",
        ),
    },
    {
        "input": {
            "topic": "Panda",
            "found_excerpt": "Copulation time ranges from 30 seconds to five minutes, but the male may mount her repeatedly to ensure successful fertilisation. The gestation period is somewhere between 95 and 160 days - the variability is due to the fact that the fertilized egg may linger in the reproductive system for a while before implanting on the uterine wall.",
            "description": "average days of gestation in giant pandas (in days)",
        },
        "output": EstimationPrompt(
            prompt="Estimate the average period of gestation in giant pandas",
            date=None,
            units="in days",
        ),
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


def make_input_human_readable(question):
    return f"""## Topic

{question["topic"]}

## Excerpt
{question["found_excerpt"]}

## Description
{question["description"]}"""


def rewrite_description(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-4o-mini",
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction=SYSTEM_PROMPT,
        format_question_into_prompt=make_input_human_readable,
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_with_structured_outputs,
            response_type=EstimationPrompt,
            response_key="rewritten-description",
            completion_kwargs=dict(
                model=model,
                temperature=0.0,
                max_completion_tokens=256,
            ),
        ),
        filter_questions=lambda questions: questions,
        examples=EXAMPLES,
    )
