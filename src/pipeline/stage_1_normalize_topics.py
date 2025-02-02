import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.input_output import output_and_log_files
from utils.wikipedia import normalize_articles, are_disambiguation

import os
import json
from concurrent.futures import ThreadPoolExecutor


def normalize_topics(
    input_file: str | None = None,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
):
    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    # Read topics
    with open(input_file, "r", encoding="utf-8") as f:
        topics = json.load(f)

    # Remove duplicates
    topics = list(set(t["_"] if isinstance(t, dict) else t for t in topics))

    # Chunk topics into groups of 50
    chunked_topics = [topics[i : i + 10] for i in range(0, len(topics), 10)]

    # Check for disambiguation
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            disambiguation_results = list(
                executor.map(are_disambiguation, chunked_topics)
            )

        print(disambiguation_results)
        for chunk, r in zip(chunked_topics, disambiguation_results):
            if "2+2" in chunk:
                print(chunk)
            print(r)

        some_dis = False
        for result in disambiguation_results:
            for dis in result:
                print(f"Disambiguation needed for {dis}")
                some_dis = True

        if some_dis:
            os._exit(0)  # Exit if disambiguation is needed

    except Exception as e:
        print(f"Error during disambiguation check: {e}")
        os._exit(0)

    print("No disambiguation needed.")

    # Normalize article titles
    normalized_topics = []
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            normalization_results = list(
                executor.map(normalize_articles, chunked_topics)
            )

        for result in normalization_results:
            normalized_topics.extend(result)

    except Exception as e:
        print(f"Error during normalization: {e}")
        os._exit(0)

    # Remove duplicates again after normalization
    normalized_topics = list(set(normalized_topics))

    # Save normalized topics to output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(normalized_topics, f, ensure_ascii=False, indent=4)
