import os
import json
import tiktoken
import unicodedata
from tqdm import tqdm
from pathlib import Path

def normalize_unicode(text):
    # Normalize to NFC (Canonical Composition) or NFD (Canonical Decomposition)
    normalized_text = unicodedata.normalize('NFC', text)
    return normalized_text

# Tokenizer initialization using tiktoken
tokenizer = tiktoken.get_encoding("gpt2")

# =============================
# Main Functions
# =============================

def count_tokens(encoded):
    tokens = {}
    for token in encoded:
        if token not in tokens:
            tokens[token] = 1
        else:
            tokens[token] += 1
    return tokens

def count_overlap(tokens1, tokens2):
    count = 0
    for key in tokens1:
        if key in tokens2:
            count += min(tokens1[key], tokens2[key])
    return count

def _is_period(string, index):
    # If not a dot, return false
    if string[index] != ".":
        return False

    # Check if it is part of a number
    if index > 0 and index < len(string) - 1:
        if string[index-1].isdigit() and string[index+1].isdigit():
            return False

    return True

def find_excerpt_in_topic(topic, questions, wikidump_path):
    # print(f"Processing topic: {topic}")

    with open(wikidump_path, 'r', encoding='utf-8') as f:
        wiki_text = normalize_unicode(f.read())
    
    wiki_encoded = tokenizer.encode(wiki_text)

    for question in questions:
        reported_excerpt = normalize_unicode(question["excerpt"])
        excerpt_encoded = tokenizer.encode(reported_excerpt)
        excerpt_tokens = count_tokens(excerpt_encoded)

        best_i = 0
        best_overlap = 0

        for i in range(len(wiki_encoded) - len(excerpt_encoded)):
            wiki_tokens = count_tokens(wiki_encoded[i:i+len(excerpt_encoded)])
            unordered_overlap = count_overlap(excerpt_tokens, wiki_tokens)
            if unordered_overlap > best_overlap:
                best_overlap = unordered_overlap
                best_i = i

        start_i = len(tokenizer.decode(wiki_encoded[:best_i]))
        end_i = start_i + len(tokenizer.decode(wiki_encoded[best_i:best_i+len(excerpt_encoded)]))

        # Adjusting to get complete sentences
        d = 0
        while start_i >= 0 and not _is_period(wiki_text, start_i):
            start_i -= 1
            d += 1

        if wiki_text[start_i-3:start_i+2] == "[...]":
            start_i += 2
        elif d < 8:
            start_i -= 1
            while start_i >= 0 and not _is_period(wiki_text, start_i):
                start_i -= 1
                d += 1

        d = 0
        while end_i < len(wiki_text) and not _is_period(wiki_text, end_i):
            end_i += 1
            d += 1

        if d < 8 and wiki_text[end_i+1:end_i+6] != "\n[...]":
            end_i += 1
            while end_i < len(wiki_text) and not _is_period(wiki_text, end_i):
                end_i += 1
                d += 1

        extended_found_excerpt = wiki_text[start_i+1:end_i+1].strip()

        if extended_found_excerpt.startswith("]"):
            extended_found_excerpt = extended_found_excerpt[1:].strip()
        if extended_found_excerpt.endswith("["):
            extended_found_excerpt = extended_found_excerpt[:-1].strip()
        if extended_found_excerpt.endswith("[."):
            extended_found_excerpt = extended_found_excerpt[:-2].strip()

        question["found_excerpt"] = extended_found_excerpt

    return questions

def main(
    input_path = "data/pipeline/retrieve_quantities.json",
    output_path = "data/pipeline/find_excerpt.json",
    log_path = "data/pipeline/logs/find_excerpt/",
    wikidump_path = "data/wikipedia_dumps/"
):

    # Read the input questions
    with open(input_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    questions_by_topic = {}
    for question in questions:
        if question["topic"] not in questions_by_topic:
            questions_by_topic[question["topic"]] = []
        question["found_excerpt"] = None
        questions_by_topic[question["topic"]].append(question)

    for topic in tqdm(questions_by_topic):
        wikidump_file = os.path.join(wikidump_path, f"{topic}.txt")
        find_excerpt_in_topic(topic, questions_by_topic[topic], wikidump_file)

    print("Done")

    # Write the modified questions with found excerpts
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
