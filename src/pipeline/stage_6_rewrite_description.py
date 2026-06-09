import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import BaseModel, Field
from typing import Union

from functools import partial
from utils.input_output import output_and_log_files
from pipeline.stage_4_mine_quantities import QuantityValue_, ValueModifier
from pipeline.general.generic_api_step import (
    generic_api_processing_step,
    fetch_api_response_and_process_with_structured_outputs,
    fetch_api_response_and_process_with_logprobs,
)


class EstimationPrompt(BaseModel):
    description: str = Field(
        ...,
        description='Game prompt for estimating of the quanitity, coming after with "Estimate " and NOT including units or dates of measurement. The description must be understandable without seeing the topic, excerpt or knowing the answer.',
    )
    time_period: str | None = Field(
        ...,
        description='Measurement date, beginning with "in ", "between ", "before ", "as of ", etc., e.g. "in 2007" for a question asks how many X happened in 2007. If the value of the quantity is the date, set to null. If no date is present, set to null.',
    )
    units: str | None = Field(
        ...,
        description='Measurement units, beginning with "in ", e.g. "in kg". If the quantity has no units, set to null.',
    )
    answer: QuantityValue_ = Field(
        ...,
        description="Value of the quantity.",
    )

    def prompt(self) -> str:
        parts = [
            "Estimate",
            self.description,
            self.time_period,
            self.units,
        ]
        return " ".join([part for part in parts if part])


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
            "excerpt_with_highlight": 'Until well into the 19th century, "stove" was defined as a single heated room.\nCooking was performed over an open fire since nearly **two million years ago**. It is uncertain how fires were started at these times; some hypotheses include the removal of burning branches from wildfires, spark generation through hitting rocks, or accidental lighting through the chipping of stone tools.',
        },
        "output": EstimationPrompt(
            description="how long humans have been cooking over open fires",
            time_period=None,
            units="in years",
            answer=QuantityValue_(
                modifier=ValueModifier.APPROXIMATELY,
                value_or_interval=2_000_000,
            ),
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
            "excerpt_with_highlight": "In many countries, they are believed to have nine lives, but in Italy, Germany, Greece, Brazil and some Spanish-speaking regions, they are said to have **seven lives**, while in Arabic traditions, the number of lives is six.",
        },
        "output": EstimationPrompt(
            description="the number of lives cats are believed to have in Italy and Germany",
            time_period=None,
            units=None,
            answer=QuantityValue_(
                modifier=ValueModifier.EXACTLY,
                value_or_interval=7,
            ),
        ),
    },
    {
        "input": {
            "topic": "Plastic",
            "excerpt_with_highlight": "**9.2 billion metric tons** of plastic are estimated to have been made between 1950 and 2017, more than half of which has been produced since 2004.",
        },
        "output": EstimationPrompt(
            description="the total amount of plastic produced",
            time_period="between 1950 and 2017",
            units="in metric tons",
            answer=QuantityValue_(
                modifier=ValueModifier.APPROXIMATELY,
                value_or_interval=9_200_000_000,
            ),
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
            "excerpt_with_highlight": "Northern and central Sweden have several wide rivers known as alvar, commonly sourced within the Scandinavian Mountains. The longest river is Klaralven-Gota alv, which originates in Trondelag in central Norway, running **1,160 kilometres (720 mi)** before it enters the sea at Gothenburg. In southern Sweden, narrower rivers known as aar are also common.",
        },
        "output": EstimationPrompt(
            description="the length of the longest river in Sweden",
            time_period=None,
            units="in km",
            answer=QuantityValue_(
                modifier=ValueModifier.EXACTLY,
                value_or_interval=1_160,
            ),
        ),
    },
    {
        "input": {
            "topic": "Panda",
            "excerpt_with_highlight": "Copulation time ranges from 30 seconds to five minutes, but the male may mount her repeatedly to ensure successful fertilisation. The gestation period is somewhere between **95 and 160 days** - the variability is due to the fact that the fertilized egg may linger in the reproductive system for a while before implanting on the uterine wall.",
        },
        "output": EstimationPrompt(
            description="the average period of gestation in giant pandas",
            time_period=None,
            units="in days",
            answer=QuantityValue_(
                modifier=ValueModifier.APPROXIMATELY,
                value_or_interval=[95, 160],
            ),
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
    if "found_excerpt_expansion" in question:
        text = "\n".join(
            x.strip()
            for x in [
                question["found_excerpt_expansion"][0],
                question["excerpt_with_highlight"],
                question["found_excerpt_expansion"][1],
            ]
            if x.strip()
        )
    else:
        text = question["excerpt_with_highlight"]

    return f"""## Topic
{question["topic"]}

## Text
{text}"""


def print_example(example: dict) -> str:
    return (
        "# Example\n\n"
        + make_input_human_readable(example["input"])
        + f"\n\n## Your output\n{example['output'].model_dump_json()}\n\n## Explanation\nThe prompt is: `{example['output'].prompt()}`"
    )


SEP = "\n\n"

SYSTEM_PROMPT = f"""You are helping design a trivia-like game about estimating quantities. You will receive a topic and a text where a quantity is highlighted with ***.
Your task is to write a prompt for the game about estimating that quality. The players will not see the topic or the excerpt, so the prompt must be self-contained and make no implicit references to them! The prompt is of the form "Estimate [description] ([units]) ([time_period])" where:
- `description` is written in plain language, avoiding jargon or technical terms, to make the game available to a wide audience. If some such term is unavoidable, briefly explainable. It is stated plainly and in natural-sounding language.
- `time_period` (optional) is used to specify that the description refers to a specific period, e.g. if the description was "the number of lightning strikes yearly" time_period could be "in 2007" (if that's the year that's mentioned in the text). Otherwise, leave as null. If the quantity itself is a time period, do not include it here since that would give away the output!
- `units` (optional) contains the unit of measurement, and begins with "in ". Prefer IS units of measurements, e.g. "in m". If it is counting items or the quantity does not have units, leave as null. Percentage "%" is considered a unit.


{SEP.join(print_example(x) for x in EXAMPLES)}"""


def rewrite_description_2(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-5-mini",
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
                reasoning_effort="medium",
                max_completion_tokens=2048,
            ),
        ),
        filter_questions=lambda questions: questions,
        examples=[],
    )

    return output_file


# TODO: In the future, it would have been better to rewrite the description and answer all at once, since then the information in the original answer (e.g. the units) can also be used to shape the new description (and answer)

if __name__ == "__main__":
    # print JSON schema for EstimationPrompt
    from openai.lib._parsing import type_to_response_format_param, maybe_parse_content

    print(SYSTEM_PROMPT)

    print(json.dumps(type_to_response_format_param(EstimationPrompt)["json_schema"]))
