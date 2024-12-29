import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.wikipedia import normalize_articles, are_disambiguation


import os
import json
from concurrent.futures import ThreadPoolExecutor

# =============================
# Main Functions
# =============================

def main(input_path="data/topics.json", output_path="data/topics_normalized.json"):

    topics_file = input_path
    output_path = output_path

    # Read topics
    with open(topics_file, 'r', encoding='utf-8') as f:
        topics = json.load(f)

    # Remove duplicates
    topics = list(set(topics))

    # Chunk topics into groups of 50
    chunked_topics = [topics[i:i + 10] for i in range(0, len(topics), 10)]

    # Check for disambiguation
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            disambiguation_results = list(executor.map(are_disambiguation, chunked_topics))

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
            normalization_results = list(executor.map(normalize_articles, chunked_topics))

        for result in normalization_results:
            normalized_topics.extend(result)

    except Exception as e:
        print(f"Error during normalization: {e}")
        os._exit(0)

    # Remove duplicates again after normalization
    normalized_topics = list(set(normalized_topics))

    # Save normalized topics to output file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(normalized_topics, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()

# GPT-4o mini: $4.2194 for 89777 questions in 547 topics
