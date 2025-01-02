import os
from tqdm import tqdm
from collections import defaultdict
import re
import json
import time
import concurrent.futures
from dotenv import load_dotenv

from openai import OpenAI

def call_batch_api(client, batch_lines, i):
    print("Started", i)
    if len(batch_lines) == 0:
        print("No batch lines")
        return

    # Save .jsonl file
    tmp_dir = "tmp/openai_requests"
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_batch_file = f"{tmp_dir}/llm_filter_{i}.jsonl"
    tmp_metadata_file = f"{tmp_dir}/llm_filter_{i}-metadata.json"

    if os.path.exists(tmp_metadata_file):
        print(f"Skipping {i} as there is already metadata")
        return

    with open(tmp_batch_file, "w", encoding="utf-8") as f:
        for line in batch_lines:
            f.write(json.dumps(line) + "\n")

    # Upload file
    file_object = client.files.create(file=open(tmp_batch_file, "rb"), purpose="batch")

    # Run the batch
    batch_object = client.batches.create(
        input_file_id=file_object.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    with open(tmp_metadata_file, "w") as f:
        f.write(json.dumps({"batch_id": batch_object.id}))

    print(i, batch_object.id)

def call_batch_api_wrapper(args):
    call_batch_api(*args)

if __name__ == "__main__":
    load_dotenv()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with open("data/wikipedia_pageviews/filtered_with_classifier.json", "r", encoding="utf-8") as f:
        article_titles = json.load(f)

    batch_lines = [
        {
            "custom_id": f"filter-request##{article_title}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You will receive one topic. Reply with Y if everyone knows what it is, it is SFW, and it is not a person or historical event. Otherwise, reply with N."},
                    {"role": "user", "content": article_title},
                ],
                "temperature": 0.0,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "max_tokens": 4,
                "stream": False,
                "n": 1,
                "logprobs": True,
                "top_logprobs": 20,
            }
        }
        for article_title in article_titles
    ]

    max_things = len(batch_lines) / 50_000

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(call_batch_api_wrapper, [(client, batch_lines[i*50_000:(i+1)*50_000], i) for i in range(int(max_things)+1)])

    print("All tasks should have completed.")
