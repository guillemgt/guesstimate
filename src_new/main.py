from functools import partial

import pipeline

if __name__ == "__main__":
    pipeline_stages = [
        pipeline.add_vital_topics,
        partial(
            pipeline.add_manual_topics,
            manual_topics_file="data/input/topics_manual.json",
        ),
        partial(
            pipeline.add_topics_by_pageviews,
            redirects_file="data/input/wikipedia_dumps/enwiki-20240901-redirect.sql",
            pageviews_files=["data/input/wikipedia_dumps/pageviews-20240206-user"],
            min_view_threshold=500,
        ),
        partial(
            pipeline.add_topics_by_pageviews,
            redirects_file="data/input/wikipedia_dumps/enwiki-20240901-redirect.sql",
            pageviews_files=["data/input/wikipedia_dumps/pageviews-20240206-user"],
            min_view_threshold=500,
        ),
        # pipeline.normalize_topics,
    ]

    last_output_file = None
    for stage in pipeline_stages:
        last_output_file = stage(input_file=last_output_file)
