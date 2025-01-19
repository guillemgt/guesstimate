import os
from tqdm import tqdm
from collections import defaultdict
import re
import json

import os
import json
from collections import defaultdict

from utils.input_output import output_and_log_files


def parse_redirects(file_path):
    # Initialize a dictionary to store redirects
    redirects = {}

    # Regex to capture the INSERT statements containing redirect data
    redirect_pattern = re.compile(r"INSERT INTO `redirect` VALUES \((\d+),(\d+),.*?\);")

    with open(file_path, "r", encoding="utf-8") as f:
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


def add_topics_by_pageviews(
    input_file: str | None = None,
    output_file: str | None = None,
    log_file: str | None = None,
    redirects_file: str = "data/input/wikipedia_pageviews/enwiki-20240901-redirect.sql.json",
    pageviews_files: list[str] = ["data/input/wikipedia_dumps/pageviews-20240206-user"],
    min_view_threshold: int = 3,
) -> str:
    output_file, log_file = output_and_log_files(output_file, log_file)
    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists.")
        return output_file

    if input_file is not None and os.path.exists(input_file):
        with open(input_file, "r") as f:
            articles = json.load(f)

    redirects_map = parse_redirects(redirects_file)

    page_views = defaultdict(int)

    for pageviews_file in pageviews_files:
        # Read the pageviews file
        with open(pageviews_file, "r", encoding="utf-8") as f:
            pageviews = f.readlines()

        # Parse the pageviews
        for pageview in tqdm(pageviews):
            pageview = pageview.strip()
            fields = pageview.split(" ")
            project = fields[0]
            title = fields[1]
            views = fields[4]
            if project == "en.wikipedia" or project == "en.m.wikipedia":
                title_formatted = title.replace("_", " ")
                page_views[redirects_map.get(title_formatted, title_formatted)] += int(
                    views
                )

    pages_by_views = sorted(page_views.items(), key=lambda x: x[1], reverse=True)

    pages_by_views = {
        page[0]: page[1]
        for page in pages_by_views
        if page[1] >= min_view_threshold and is_ascii(page[0])
    }
    print("Filtered to ", len(pages_by_views), "pages")

    for k in ["Bee", "Ant", "Spain", "Key", "Bed"]:
        print(k, page_views.get(k, 0))

    articles.extend(list(pages_by_views.keys()))

    with open(output_file, "w") as f:
        json.dump(articles, f, indent=4)

    return output_file
