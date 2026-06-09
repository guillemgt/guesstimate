import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.wikipedia import query

import os
import json
from bs4 import BeautifulSoup
from tokenizers import Tokenizer
from pathlib import Path
import concurrent.futures
import time

from utils.input_output import output_and_log_files


# Load GPT-3 tokenizer
tokenizer = Tokenizer.from_pretrained("gpt2")

# =============================
# Main Functions
# =============================


def query_and_process_wiki_articles(list_of_topic_and_path):
    for topic_and_path in list_of_topic_and_path:
        try:
            topic, wikidump_path = topic_and_path
            if Path(wikidump_path).exists():
                continue
            response = query(topic)
            process_wiki_article(response, topic, wikidump_path)
            time.sleep(2)
        except Exception as e:
            print("Error:", e)


def process_wiki_article(wikipedia_response_json_text, topic, wikidump_path):
    print(f"Processing article {topic}")

    if Path(wikidump_path).exists():
        return False

    json_data = json.loads(wikipedia_response_json_text)
    if "parse" not in json_data:
        print(f"Article not found: {topic}")
        return False

    html_txt = json_data["parse"]["text"]["*"]
    soup = BeautifulSoup(html_txt, "html.parser")

    # Clean up HTML
    for tag in soup(["sup", "style", "script"]):
        tag.decompose()

    parsed_text = ""
    next_parsed_text = ""
    last_dots = False

    ps = soup.select(".mw-parser-output > p")
    for paragraph in ps:
        original_html = str(paragraph)

        # Replace <sup> and <sub> tags with custom notations
        modified_html = (
            original_html.replace("<sup>", "^( ")
            .replace("</sup>", " )")
            .replace("<sub>", "_(")
            .replace("</sub>", ")")
        )

        paragraph_text = BeautifulSoup(modified_html, "html.parser").get_text()
        has_number = any(char.isdigit() for char in paragraph_text)

        if has_number:
            next_parsed_text = parsed_text + paragraph_text
            last_dots = False
        else:
            if not last_dots:
                next_parsed_text = parsed_text + "[...]\n"
                last_dots = True

        # Tokenize text and check length
        encoded = tokenizer.encode(next_parsed_text)
        if len(encoded.ids) > 20_000:
            break

        parsed_text = next_parsed_text

    parsed_text = parsed_text.strip()
    if not parsed_text or parsed_text == "[...]":
        return False

    with open(wikidump_path, "w", encoding="utf-8") as f:
        f.write(parsed_text)

    return True


def download_wikipedia_pages(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    dump_path: str = "data/wikipedia_dumps/",
):
    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    topics_file = input_file
    dir_wikidump = dump_path

    # Ensure the output directory exists
    os.makedirs(dir_wikidump, exist_ok=True)

    with open(topics_file, "r", encoding="utf-8") as f:
        topics = json.load(f)

    # Fix mojibake encoding issues (e.g., "PokÃ©mon" -> "Pokémon")
    def fix_encoding(text):
        try:
            # If text was incorrectly decoded, re-encode as latin-1 and decode as utf-8
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            # If it fails, the text is probably fine
            return text

    topics = list(set(t["_"] if isinstance(t, dict) else t for t in topics))
    topics = [fix_encoding(topic) for topic in topics]
    topics = sorted(topics)

    # Prepare topics for processing
    topics_with_paths = [
        (topic, os.path.join(dir_wikidump, f"{topic}.txt")) for topic in topics
    ]

    try:
        # Run parallel processing with concurrent tasks
        max_concurrent_tasks = 5
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(
                query_and_process_wiki_articles,
                [
                    topics_with_paths[i::max_concurrent_tasks]
                    for i in range(max_concurrent_tasks)
                ],
            )
    except Exception as e:
        print("Error:", e)
        os._exit(0)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            [
                {"topic": topic, "topic_dump_path": path}
                for topic, path in topics_with_paths
                if os.path.exists(path)
            ],
            f,
            ensure_ascii=False,
            indent=4,
        )

    return output_file
