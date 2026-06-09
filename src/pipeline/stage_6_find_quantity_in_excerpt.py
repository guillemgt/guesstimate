import sys
import os
from enum import Enum
from difflib import SequenceMatcher

from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enum import Enum

from functools import partial
from utils.input_output import output_and_log_files
from pipeline.general.generic_api_step import (
    generic_api_processing_step,
    fetch_api_response_and_process_raw_text,
)
from pipeline.stage_4_mine_quantities import QuantityValue


def format_question(question: dict) -> str:
    quantity = QuantityValue.model_validate(question["value"])
    return f"""## Quantity:
{question["description"]} -> {str(quantity)}

## Excerpt:
{question["found_excerpt"]}"""


def find_quantity_in_found_excerpt(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    model="gpt-5-nano",
) -> str:

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    instruction = """You will be given a description of a quantity, its value, and a text excerpt where the quantity is mentioned. Your task is to highlight the quantity in the excerpt with ***. Except for the ***, the text must remain exactly as in the original excerpt. Reply ONLY with the excerpt with highlight (no header).

# Example

## Quantity: 
Age range of the oldest ant fossils from the mid-Cretaceous -> between 100 and 113 million years

## Excerpt: 
The specimen, trapped in amber dating back to around 92 million years ago, has features found in some wasps, but not found in modern ants. The oldest fossils of ants date to the mid-Cretaceous, around 113–100 million years ago, which belong to extinct stem-groups such as the Haidomyrmecinae, Sphecomyrminae and Zigrasimeciinae, with modern ant subfamilies appearing towards the end of the Cretaceous around 80–70 million years ago. Ants diversified extensively during the Angiosperm Terrestrial Revolution and assumed ecological dominance around 60 million years ago.

## Excerpt with highlight: 
The specimen, trapped in amber dating back to around 92 million years ago, has features found in some wasps, but not found in modern ants. The oldest fossils of ants date to the mid-Cretaceous, around ***113–100 million years ago***, which belong to extinct stem-groups such as the Haidomyrmecinae, Sphecomyrminae and Zigrasimeciinae, with modern ant subfamilies appearing towards the end of the Cretaceous around 80–70 million years ago. Ants diversified extensively during the Angiosperm Terrestrial Revolution and assumed ecological dominance around 60 million years ago."""

    generic_api_processing_step(
        input_path=input_file,
        output_path=output_file,
        log_path=log_file,
        instruction=instruction,
        format_question_into_prompt=format_question,
        fetch_api_response_and_process=partial(
            fetch_api_response_and_process_raw_text,
            response_key="excerpt_with_highlight",
            completion_kwargs=dict(
                model=model,
                reasoning_effort="low",
                max_completion_tokens=4096,
            ),
        ),
        filter_questions=compare_excerpts,
        examples=[],
    )

    return output_file


def compare_excerpts(questions: list[dict]) -> list[dict]:
    filtered_questions = []
    for question in tqdm(questions):
        highlighted_excerpt = question.get("excerpt_with_highlight", "")
        original_excerpt = question.get("found_excerpt", "")
        if "***" in highlighted_excerpt and highlighted_excerpt.count("***") >= 2:
            # Remove the highlights for comparison
            cleaned_excerpt = highlighted_excerpt.replace("***", "")
            # Use similarity ratio instead of exact match (threshold: 0.95 = 95% similar)
            similarity = SequenceMatcher(
                None, cleaned_excerpt, original_excerpt
            ).ratio()
            if similarity >= 0.95:
                question["excerpt_with_highlight"] = highlighted_excerpt
                filtered_questions.append(question)
    return filtered_questions
