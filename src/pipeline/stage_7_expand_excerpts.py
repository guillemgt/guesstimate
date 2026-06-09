import os
import json
import unicodedata
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from utils.input_output import output_and_log_files


def normalize_unicode(text):
    # Normalize to NFC (Canonical Composition) or NFD (Canonical Decomposition)
    normalized_text = unicodedata.normalize("NFC", text)
    return normalized_text


def _is_period(string, index):
    # If not a dot, return false
    if string[index] != ".":
        return False

    # Check if it is part of a number
    if index > 0 and index < len(string) - 1:
        if string[index - 1].isdigit() and string[index + 1].isdigit():
            return False

    return True


def extend_on_left_to_sentence(text, start_i):
    d = 0
    while start_i >= 0 and not _is_period(text, start_i):
        start_i -= 1
        d += 1

    if text[start_i - 3 : start_i + 2] == "[...]":
        start_i += 2
    elif d < 8:
        start_i -= 1
        while start_i >= 0 and not _is_period(text, start_i):
            start_i -= 1
            d += 1

    return start_i


def extend_on_right_to_sentence(text, end_i):
    d = 0
    while end_i < len(text) and not _is_period(text, end_i):
        end_i += 1
        d += 1

    if d < 8 and text[end_i + 1 : end_i + 6] != "\n[...]":
        end_i += 1
        while end_i < len(text) and not _is_period(text, end_i):
            end_i += 1
            d += 1

    return end_i


def expand_excerpts_in_topic(topic, questions, wikidump_path, sentences_to_add=1):
    # print(f"Processing topic: {topic}")

    with open(wikidump_path, "r", encoding="utf-8") as f:
        wiki_text = normalize_unicode(f.read())

    for question in questions:
        found_excerpt = normalize_unicode(question["found_excerpt"])

        # Find exact match in text
        start_pos = wiki_text.find(found_excerpt)

        if start_pos == -1:
            # Excerpt not found exactly
            question["found_excerpt_expansion"] = None
            continue

        end_pos = start_pos + len(found_excerpt) - 1

        # Expand to the left to find sentences before
        sentence_before_start = start_pos - 1
        for _ in range(sentences_to_add):
            sentence_before_start = extend_on_left_to_sentence(
                wiki_text, sentence_before_start
            )
            if sentence_before_start <= 0:
                break
            sentence_before_start -= 1
        sentence_before_end = start_pos - 1

        # Expand to the right to find sentences after
        sentence_after_start = end_pos + 1
        sentence_after_end = end_pos + 1
        for _ in range(sentences_to_add):
            sentence_after_end = extend_on_right_to_sentence(
                wiki_text, sentence_after_end
            )
            if sentence_after_end >= len(wiki_text) - 1:
                break
            sentence_after_end += 1

        # Extract sentences
        sentence_before = wiki_text[
            sentence_before_start + 1 : sentence_before_end + 1
        ].strip()
        sentence_after = wiki_text[
            sentence_after_start : sentence_after_end + 1
        ].strip()

        # Clean up artifacts
        # Remove leading periods and spaces
        sentence_before = (
            sentence_before.split("...]")[-1].lstrip().lstrip(".").lstrip()
        )
        sentence_after = sentence_after.split("[...")[0].lstrip().lstrip(".").lstrip()

        if sentence_before.startswith("]"):
            sentence_before = sentence_before[1:].strip()
        if sentence_before.endswith("[."):
            sentence_before = sentence_before[:-2].strip()
        if sentence_before.endswith("["):
            sentence_before = sentence_before[:-1].strip()

        if sentence_after.startswith("]"):
            sentence_after = sentence_after[1:].strip()
        if sentence_after.endswith("[."):
            sentence_after = sentence_after[:-2].strip()
        if sentence_after.endswith("["):
            sentence_after = sentence_after[:-1].strip()

        question["found_excerpt_expansion"] = [sentence_before, sentence_after]

    return questions


def expand_excerpts(
    input_file: str,
    output_file: str | None = None,
    log_file: str | None = None,
    pipeline_step: int = 0,
    dump_path: str = "data/wikipedia_dumps/",
    sentences_to_add: int = 2,
):
    output_file, log_file = output_and_log_files(output_file, log_file, pipeline_step)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    # Read the input questions
    with open(input_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Starting with {len(questions)} questions.")

    questions_by_topic = {}
    for question in questions:
        if question["topic"] not in questions_by_topic:
            questions_by_topic[question["topic"]] = []
        question["found_excerpt_expansion"] = None
        questions_by_topic[question["topic"]].append(question)

    # Prepare arguments for parallel processing
    expanded_questions = []
    for topic in tqdm(questions_by_topic):
        wikidump_file = os.path.join(dump_path, f"{topic}.txt")
        if not os.path.exists(wikidump_file):
            continue
        expanded_questions.extend(
            expand_excerpts_in_topic(
                topic, questions_by_topic[topic], wikidump_file, sentences_to_add
            )
        )

    print(f"Done expanding excerpts in {len(expanded_questions)} questions.")

    # Write the modified questions with expanded excerpts
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(expanded_questions, f, ensure_ascii=False, indent=4)

    return output_file
