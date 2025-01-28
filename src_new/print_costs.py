import os
import json

if __name__ == "__main__":

    pipeline_dir = "data/pipeline"

    # Read files ending with metadata.json
    metadata_files = [
        f for f in os.listdir(pipeline_dir) if f.endswith("metadata.json")
    ]

    # Read the metadata files
    input_costs = sum(
        json.load(open(f"{pipeline_dir}/{f}")).get("input_cost", 0.0)
        for f in metadata_files
    )
    output_costs = sum(
        json.load(open(f"{pipeline_dir}/{f}")).get("output_cost", 0.0)
        for f in metadata_files
    )

    # Print the total costs
    print(f"Total input cost: {input_costs}")
    print(f"Total output cost: {output_costs}")
    print(f"Total cost: {input_costs + output_costs}")
