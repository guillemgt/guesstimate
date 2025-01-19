import os
import json
import requests
from collections import defaultdict
import string

from utils.input_output import output_and_log_files


def add_manual_topics(
    input_file: str | None = None,
    output_file: str | None = None,
    log_file: str | None = None,
    manual_topics_file: str = "data/input/topics_manual.json",
) -> str:
    output_file, log_file = output_and_log_files(output_file, log_file)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    if input_file is not None and os.path.exists(input_file):
        with open(input_file, "r") as f:
            articles = json.load(f)

    if os.path.exists(manual_topics_file):
        with open(manual_topics_file, "r") as f:
            manual_topics = json.load(f)
        articles.extend(manual_topics)

    with open(output_file, "w") as f:
        json.dump(articles, f, indent=4)

    return output_file
