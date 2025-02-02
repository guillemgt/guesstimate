from functools import partial
from dotenv import load_dotenv
import numpy as np

import pipeline

if __name__ == "__main__":
    load_dotenv()

    pipeline_stages = [
        pipeline.add_vital_topics,
        # partial(
        #     pipeline.add_topics_by_pageviews,
        #     redirects_file="data/input/wikipedia_dumps/enwiki-20240901-redirect.sql",
        #     pageviews_files=["data/input/wikipedia_dumps/pageviews-20240206-user"],
        #     min_view_threshold=10_000,
        # ),
        pipeline.filter_topic_by_category,
        pipeline.filter_topic_by_clarity,
        partial(
            pipeline.filter_topic_by_clarity,
            model="gpt-4o-2024-11-20",
            logprob_threshold=-1e-5,
        ),
        partial(
            pipeline.add_manual_topics,
            manual_topics_file="data/input/topics_manual.json",
        ),
        pipeline.normalize_topics,
        pipeline.download_wikipedia_pages,
        pipeline.mine_quantities,
        pipeline.find_excerpts,
        pipeline.rewrite_description,
        partial(
            pipeline.filter_clear,
            task=pipeline.ClarityType.NoTechnicalTerms,
            logprob_threshold=-np.inf,
        ),
        partial(
            pipeline.filter_clear,
            task=pipeline.ClarityType.MakesSenseWithoutContext,
            logprob_threshold=-np.inf,
        ),
        partial(
            pipeline.filter_clear,
            task=pipeline.ClarityType.MakesSense,
            logprob_threshold=-np.inf,
        ),
        partial(
            pipeline.filter_clear,
            task=pipeline.ClarityType.OverallClear,
            logprob_threshold=-np.inf,
        ),
        partial(
            pipeline.filter_clear,
            task=pipeline.ClarityType.TryToAnswer,
            logprob_threshold=-np.inf,
        ),
        pipeline.deduplicate,  # Should have done this before...
        partial(
            pipeline.generic_filter,
            filters=[
                ("logprob-clarity-NoTechnicalTerms", -10.0),
                ("logprob-clarity-MakesSense", -5.0),
                ("logprob-clarity-TryToAnswer", -12.0),
                ("logprob-clarity-OverallClear", -0.001),
                ([("logprob-clarity-TryToAnswer", -1.0)], 1e-10),
            ],
            ignore_zeros=True,
        ),
        partial(
            pipeline.filter_clear,
            task=pipeline.ClarityType.OverallClearDetailed,
            logprob_threshold=-1e-7,  # An 'acceptable' less agressive threshold could be -0.25; but while most of the questions between the two are clear, it seems the interesting ones have lower logprobs
            model="gpt-4o-2024-11-20",
        ),
        partial(
            pipeline.filter_correct,
            logprob_threshold=-0.1,
        ),
        pipeline.remove_quantities_with_small_ints,
        pipeline.remove_date_and_unit_from_descriptions,
        partial(
            pipeline.add_scale_metadata,
            model="gpt-4o-2024-11-20",  # May not be necessary...
        ),
    ]

    last_output_file = None
    for i, stage in enumerate(pipeline_stages):
        last_output_file = stage(input_file=last_output_file, pipeline_step=i)
