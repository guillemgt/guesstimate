import sys
import os
from enum import Enum

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enum import Enum

from functools import partial
from utils.input_output import output_and_log_files
from pipeline.general.generic_api_step import (
    generic_api_processing_step,
    fetch_api_response_and_process_float_result,
)

from pipeline.stage_4_mine_quantities import Quantity

PROMPT = """## Goal

Rank quantities that can become **fun, surprising, hard-to-guess estimation questions**.

Favor **curiosity and scale intuition**, not factual correctness.

Reply with ONLY a number from 0 to 100 indicating how well the quantity meets the criteria below. 0 = completely unsuitable, 100 = perfect for an estimation question.

## Give a high score (80-100) if a quantity...

* Makes you think *"huh, I never thought about that"*
* Involves **scale**, **extremes**, or **hidden magnitude** (very big, very small, very fast, very old, very numerous)
* Can be estimated using **everyday anchors** (human scale, objects, time, money, distance, food, animals) or **Fermi estimation**
* Would be interesting to **argue about before looking up the answer**
* Could be phrased as *"How big / how many / how fast / how long / what fraction…?"*

Examples of good vibes:

* "How many X exist in the world?"
* "How fast can X really move?"
* "How much X is there compared to humans / a city / a year?"
* "What's the biggest / smallest / longest-lasting X?"

## Say a low number (0-20) if a quantity...

* Is **clearly broken** (nonsense units, impossible values, extraction errors)
* Is **pure trivia** (exact dates, named awards, catalogue facts)
* Requires **specialist domain knowledge** to even take a guess
* Has **no intuitive scale** a human could reason about

## Strongly prefer

* Global totals and proportions
* Extremes and limits
* Comparisons to familiar things
* Ranges instead of exact values
* Weird but concrete real-world contexts (food, animals, money, speed, size)


## Upshot

The descriptions and answers will be normalized later, so focus on **interestingness** over precision or clarity, but make sure the answer is contained in the excerpt.
Overall, value:
* surprise > cleanliness
* argument-worthiness > precision
* intuition > expertise"""


def format_question(question: dict) -> str | None:
    if "rewritten-description" in question:
        raise NotImplementedError(
            "Rewritten description formatting not implemented yet."
        )
    else:
        quantity = Quantity.model_validate(question)

    try:
        return f"""# Topic:
{question['topic']}

# Excerpt:
{quantity.excerpt}

# Quantity description:
{quantity.description}

# Quantity value:
{str(quantity.value)}"""
    except IndexError:
        return None


def filter_potential(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-5.1",
    score_threshold: float = 0.8,
    reasoning_effort: str = "minimal",
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    score_key = "rough-potential"

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction=PROMPT,
        format_question_into_prompt=format_question,
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_float_result,
            min_value=0.0,
            max_value=100.0,
            score_key=score_key,
            completion_kwargs={
                k: v
                for k, v in dict(
                    model=model,
                    reasoning_effort=(
                        reasoning_effort if reasoning_effort != "minimal" else None
                    ),
                    temperature=0.6 if reasoning_effort == "minimal" else None,
                ).items()
                if v is not None
            },
        ),
        filter_questions=lambda questions: [
            question
            for question in questions
            if question[score_key] is not None and question[score_key] > score_threshold
        ],
        examples=[],
        sort_by_key=score_key,
    )

    return output_file
