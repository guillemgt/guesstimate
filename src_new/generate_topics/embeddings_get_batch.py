import os
from tqdm import tqdm
from collections import defaultdict
import re
import json
import time
import gc

from dotenv import load_dotenv

import numpy as np
from openai import OpenAI

if __name__ == "__main__":
    load_dotenv()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    tmp_dir = "tmp/openai_requests"
    
    embeddings = []
    labels = []

    skipped_lines = 0

    for file in os.listdir(tmp_dir):
        if file.endswith('-metadata.json') and file.startswith('pageviews_'):
            gc.collect()
            embeddings_for_this_file = []
            output_file = os.path.join(tmp_dir, file.replace('-metadata.json', '-output.jsonl'))
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    lines = f.readlines()
                    for line in tqdm(lines):
                        try:
                            datum_raw = json.loads(line)
                            embeddings_for_this_file.append(datum_raw['response']['body']['data'][0]['embedding'])
                            labels.append(datum_raw['custom_id'].split('##')[-1])
                        except:
                            skipped_lines += 1
                embeddings.append(np.array(embeddings_for_this_file))
                continue
            with open(os.path.join(tmp_dir, file), "r") as f:
                metadata = json.load(f)
                batch_id = metadata["batch_id"]
                print("Retrieving batch", batch_id, "for", file)
                batch_object = client.batches.retrieve(batch_id)
                batch_object = batch_object
                print("\tBatch status:", batch_object.status)
                content = client.files.content(batch_object.output_file_id)
                print("\tDownloaded response")
                text_response = content.response.content.decode('UTF-8')
                print("\tDecoded response")
                with open(output_file, "w") as f:
                    f.write(text_response)

                for line in tqdm(text_response.split("\n")):
                    if line:
                        try:
                            datum_raw = json.loads(line)
                            embeddings.append(datum_raw['response']['body']['data'][0]['embedding'])
                            labels.append(datum_raw['custom_id'].split('##')[-1])
                        except:
                            skipped_lines += 1

                embeddings.append(np.array(embeddings_for_this_file))

    print("Skipped", skipped_lines, "lines")

    # assert sum(e.shape[0] for e in embeddings) == len(labels), f"Length mismatch: {len(embeddings)} embeddings, {len(labels)} labels"
    print(sum(e.shape[0] for e in embeddings), len(labels))

    embeddings = np.vstack(embeddings)
    print(embeddings.shape)
    np.save("data/wikipedia_pageviews/embeddings.npy", embeddings)
    with open("data/wikipedia_pageviews/embeddings-articles.json", "w") as f:
        json.dump(labels, f)

# $0.03 for 600,000+