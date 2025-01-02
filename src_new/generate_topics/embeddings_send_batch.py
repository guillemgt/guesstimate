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
    tmp_batch_file = f"{tmp_dir}/pageviews_{i}.jsonl"
    tmp_metadata_file = f"{tmp_dir}/pageviews_{i}-metadata.json"

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
        endpoint="/v1/embeddings",
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

    with open("data/wikipedia_pageviews/pageviews.json", "r", encoding="utf-8") as f:
        pageviews = json.load(f)

    batch_lines = [
        {
            "custom_id": f"embedding-request##{article_title}",
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {
                "model": "text-embedding-3-small",
                "input": article_title,
                "encoding_format": "float"
            }
        }
        for article_title in pageviews.keys()
    ]

    max_things = len(batch_lines) / 50_000

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(call_batch_api_wrapper, [(client, batch_lines[i*50_000:(i+1)*50_000], i) for i in range(int(max_things)+1)])
        # executor.map(call_batch_api_wrapper, range(int(max_things)+1))

    print("All tasks should have completed.")

    # for i in range(int(max_things)+1):


    #     # # Wait for the batch to complete
    #     # while batch_object.status != "completed" and batch_object.status != "failed":
    #     #     batch_object = client.batches.retrieve(batch_object.id)
    #     #     print(batch_object.id)
    #     #     print(batch_object.status)
    #     #     print(batch_object.output_file_id)
    #     #     print(batch_object.request_counts)

    #     #     time.sleep(60)

    #     # batch_object = batch_object
    #     # content = client.files.content(batch_object.output_file_id)
    #     # text_response = content.response.content.decode('UTF-8')
    #     # with open(tmp_batch_file.replace('.jsonl', '-output.jsonl'), "w") as f:
    #     #     f.write(text_response)
