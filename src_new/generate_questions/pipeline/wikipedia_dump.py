import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.wikipedia import query

import os
import json
import requests
from bs4 import BeautifulSoup
from tokenizers import Tokenizer
from pathlib import Path
import concurrent.futures

# Load GPT-3 tokenizer
tokenizer = Tokenizer.from_pretrained("gpt2")

# =============================
# Main Functions
# =============================

def query_and_process_wiki_articles(list_of_topic_and_path):
    print(len(list_of_topic_and_path))
    for topic_and_path in list_of_topic_and_path:
        try:
            topic, wikidump_path = topic_and_path
            response = query(topic)
            process_wiki_article(response, topic, wikidump_path)
        except Exception as e:
            print('Error:', e)

def process_wiki_article(wikipedia_response_json_text, topic, wikidump_path):
    print(f"Processing article {topic}")

    if Path(wikidump_path).exists():
        return

    json_data = json.loads(wikipedia_response_json_text)
    if 'parse' not in json_data:
        print("Article not found")
        return

    html_txt = json_data['parse']['text']['*']
    soup = BeautifulSoup(html_txt, 'html.parser')

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
        modified_html = original_html.replace('<sup>', '^( ').replace('</sup>', ' )').replace('<sub>', '_(').replace('</sub>', ')')
        
        paragraph_text = BeautifulSoup(modified_html, 'html.parser').get_text()
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
        if len(encoded.ids) > 9000:
            break

        parsed_text = next_parsed_text

    parsed_text = parsed_text.strip()
    if not parsed_text or parsed_text == '[...]':
        return

    with open(wikidump_path, 'w', encoding='utf-8') as f:
        f.write(parsed_text)

def main(input_path="data/topics_normalized.json", output_path="data/wikipedia_dumps/"):
    
    topics_file = input_path
    dir_wikidump = output_path
    
    # Ensure the output directory exists
    os.makedirs(dir_wikidump, exist_ok=True)

    with open(topics_file, 'r', encoding='utf-8') as f:
        topics = json.load(f)

    topics = list(set(topics))

    # Prepare topics for processing
    topics_with_paths = [(topic, os.path.join(dir_wikidump, f"{topic}.txt")) for topic in topics]

    try:
        # Run parallel processing with concurrent tasks
        max_concurrent_tasks = 5
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(query_and_process_wiki_articles, [topics_with_paths[i::max_concurrent_tasks] for i in range(max_concurrent_tasks)])
    except Exception as e:
        print('Error:', e)
        os._exit(0)

    print("All tasks have finished.")

if __name__ == "__main__":
    main()
