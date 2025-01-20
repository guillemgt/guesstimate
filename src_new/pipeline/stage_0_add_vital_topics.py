import os
import json
import requests
from collections import defaultdict
import string

from utils.input_output import output_and_log_files

DISALLOWED_VITAL_TOPICS = ["People", "History", "Arts", "Philosophy and religion"]
ALLOWED_VITAL_TOPICS = [
    "Geography",
    "Everyday life",
    "Society and social sciences",
    "Biology and health sciences",
    "Physical sciences",
    "Technology",
    "Mathematics",
]


def fetch_json_data(letter: str) -> dict:
    """
    Fetches the JSON data for a specific letter from the Wikipedia API.

    Args:
    - letter (str): The letter representing the page to fetch.

    Returns:
    - dict: Parsed JSON data from the response, or None if fetching fails.
    """
    url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=revisions&titles=Wikipedia:Vital_articles/data/{letter}.json&rvprop=content&formatversion=2"

    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data for {letter}")
        return None


def process_into_article_list(
    json_data: dict,
    allowed_topics: list[str] = ALLOWED_VITAL_TOPICS,
    disallowed_topics: list[str] = DISALLOWED_VITAL_TOPICS,
) -> list[str]:
    """
    Parses the JSON data and merges articles into a single list filtered by topic.

    Args:
    - json_data (dict): JSON data containing articles and their details.
    - allowed_topics (list[str]): List of topics to include in the list.
    - disallowed_topics (list[str]): List of topics to exclude from the list.

    Returns:
    - list[str]: A list of articles filtered by topic.
    """

    articles = []

    pages = json_data.get("query", {}).get("pages", [])
    for page in pages:
        revisions = page.get("revisions", [])
        for revision in revisions:
            content = revision.get("content")
            if content:
                json_articles = json.loads(content)
                for article, details in json_articles.items():
                    topic = details.get("topic")
                    if topic in allowed_topics:
                        articles.append(article)
                    elif topic in disallowed_topics:
                        pass
                    else:
                        raise ValueError(f"Unknown topic: {topic}")

    return articles


def add_vital_topics(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
) -> str:
    """
    Fetches data for all letters of the alphabet and merges them into a single list.

    Returns:
    - dict: A merged list with all articles from A to Z.
    """

    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    if input_file is not None and os.path.exists(input_file):
        with open(input_file, "r") as f:
            articles = json.load(f)

    articles = []
    for letter in string.ascii_uppercase:  # A-Z
        json_data = fetch_json_data(letter)
        if json_data:
            articles.extend(process_into_article_list(json_data))

    with open(output_file, "w") as f:
        json.dump(articles, f, indent=4)

    return output_file
