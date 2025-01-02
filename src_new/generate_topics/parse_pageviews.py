import os
from tqdm import tqdm
from collections import defaultdict
import re
import json

def parse_redirects(file_path):
    # Initialize a dictionary to store redirects
    redirects = {}

    # Regex to capture the INSERT statements containing redirect data
    redirect_pattern = re.compile(r"INSERT INTO `redirect` VALUES \((\d+),(\d+),.*?\);")

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f):
            match = redirect_pattern.search(line)
            if match:
                # Extract source and target page IDs
                source_id = int(match.group(1))
                target_id = int(match.group(2))
                # Store the redirect relationship
                redirects[source_id] = target_id

    return redirects


def is_ascii(s):
    return all(ord(c) < 128 for c in s)

if __name__ == "__main__":
    redirects_map = parse_redirects('data/wikipedia_pageviews/enwiki-20240901-redirect.sql')


    # Read the pageviews file
    with open("data/wikipedia_pageviews/pageviews-20240206-150000", "r", encoding="utf-8") as f:
        pageviews = f.readlines()

    page_views = defaultdict(int)

    # Parse the pageviews
    for pageview in tqdm(pageviews):
        pageview = pageview.strip()
        fields = pageview.split(" ")
        project = fields[0]
        title = fields[1]
        views = fields[2]
        if project == "en" or project == "en.m":
            title_formatted = title.replace("_", " ")
            page_views[redirects_map.get(title_formatted, title_formatted)] += int(views)

    pages_by_views = sorted(page_views.items(), key=lambda x: x[1], reverse=True)

    # print("Top 100 pages by views:")
    # for page in pages_by_views[:100]:
    #     print(page)

    pages_by_views = {page[0]: page[1] for page in pages_by_views if page[1] >= 3 and is_ascii(page[0])}
    print(len(pages_by_views))

    for k in ["Bee", "Ant", "Spain", "Key", "Bed"]:
        print(k, page_views.get(k, 0))

    with open("data/wikipedia_pageviews/pageviews.json", "w") as f:
        json.dump(pages_by_views, f, indent=0)