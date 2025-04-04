import os
from dataclasses import dataclass
from typing import Optional
import io
import openai
import time
import json
import tiktoken

import hashlib


def consistent_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


@dataclass
class BatchInfo:
    hash: str
    batch_call_id: str
    index: int
    num_requests: int
    num_tokens: Optional[int] = None
    file_id: Optional[str] = None
    batch_id: Optional[str] = None

    def to_dict(self):
        return self.__dict__


FINISHED_BATCH_STATUSES = ["failed", "completed", "expired", "cancelled"]
NONFINISHED_BATCH_STATUSES = ["validating", "in_progress", "finalizing", "cancelling"]


class OpenAIBatchHandler:
    def __init__(self, api_key: Optional[str] = None, log_dir: Optional[str] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = openai.Client(api_key=api_key)
        self.tokenizer = tiktoken.get_encoding("o200k_base")
        self.log_dir = log_dir

    def _get_file_path(self, batch_call_id: str, index: int, suffix: str):
        if self.log_dir is None:
            return None
        else:
            extension = "jsonl" if suffix in ["input", "output"] else "json"
            os.makedirs(os.path.join(self.log_dir, batch_call_id), exist_ok=True)
            return os.path.join(
                self.log_dir, batch_call_id, f"{index}-{suffix}.{extension}"
            )

    def _write_metadata(self, metadata: BatchInfo, batch_call_id: str, index: int):
        if self.log_dir is None:
            return
        with open(
            self._get_file_path(
                batch_call_id=batch_call_id, index=index, suffix="metadata"
            ),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(metadata.to_dict(), f)

    def wait_for_batches(self, batch_ids: str | list[str], timeout: Optional[int] = 60):
        if not isinstance(batch_ids, list):
            batch_ids = [batch_ids]
        print("Waiting for batches", batch_ids)
        batch_objects = [
            self.client.batches.retrieve(batch_id) for batch_id in batch_ids
        ]
        while any(
            batch_object.status not in FINISHED_BATCH_STATUSES
            for batch_object in batch_objects
        ):
            total = sum(
                batch_object.request_counts.total for batch_object in batch_objects
            )
            completed = sum(
                batch_object.request_counts.completed for batch_object in batch_objects
            )
            failed = sum(
                batch_object.request_counts.failed for batch_object in batch_objects
            )
            print(
                f"{completed}/{total}"
                + ("" if failed == 0 else f"   [!] {failed} failed")
                + (f"      {[batch_object.status for batch_object in batch_objects]}")
            )

            time.sleep(timeout)
            batch_objects = [
                self.client.batches.retrieve(batch_id) for batch_id in batch_ids
            ]

    def download_batch(self, metadata: BatchInfo):
        batch_object = self.client.batches.retrieve(metadata.batch_id)
        content = self.client.files.content(batch_object.output_file_id)
        if self.log_dir is not None:
            filename = self._get_file_path(
                batch_call_id=metadata.batch_call_id,
                index=metadata.index,
                suffix="output",
            )
            if os.path.exists(filename):
                decoded_content = open(
                    filename,
                    "r",
                    encoding="utf-8",
                ).read()
            else:
                decoded_content = content.response.content.decode("utf-8")
                with open(
                    filename,
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(decoded_content)

        return [json.loads(line) for line in decoded_content.split("\n") if line]

    def _upload_and_return_batch_info(
        self,
        batch_call_id: str,
        index: int,
        jsonl_string: str,
        endpoint: str,
        requests_in_batch: int,
        tokens_in_batch: int,
    ):
        if self.log_dir is not None:
            filename = self._get_file_path(batch_call_id, index, "input")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(jsonl_string)
            file_handler = open(filename, "rb")
        else:
            file_handler = io.BytesIO(jsonl_string.encode("utf-8"))

        whole_content_hash = consistent_hash(jsonl_string)

        # Check if we've already uploaded this batch
        if self.log_dir is not None and os.path.exists(
            self._get_file_path(batch_call_id, index, "metadata")
        ):
            with open(
                self._get_file_path(batch_call_id, index, "metadata"),
                "r",
                encoding="utf-8",
            ) as f:
                print("Metadata exists")
                metadata = json.load(f)
                if metadata["hash"] == whole_content_hash:
                    file_handler.close()
                    metadata = BatchInfo(**metadata)
                    return metadata

        file_object = self.client.files.create(file=file_handler, purpose="batch")
        file_handler.close()
        batch_object = self.client.batches.create(
            input_file_id=file_object.id, endpoint=endpoint, completion_window="24h"
        )
        batch_info = BatchInfo(
            hash=whole_content_hash,
            batch_call_id=batch_call_id,
            index=index,
            num_requests=requests_in_batch,
            num_tokens=tokens_in_batch,
            file_id=file_object.id,
            batch_id=batch_object.id,
        )
        self._write_metadata(batch_info, batch_call_id, index)
        return batch_info

    def upload_batches(
        self,
        requests: list[dict],
        endpoint: str = "/v1/chat/completions",
        batch_call_id: str = "batch",
        max_tokens_per_batch: Optional[int] = 4096,
        max_requests_per_batch: Optional[int] = 50_000,
    ):
        batch_lines = []
        for index, request_args in enumerate(requests):
            batch_call_id_ = batch_call_id + "::" + str(index)

            batch_lines.append(
                {
                    "custom_id": batch_call_id_,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": request_args,
                }
            )

        request_index = 0
        tokens_in_batch = 0
        requests_in_batch = 0

        batch_infos = []

        batch_index = 0
        jsonl_strings = []
        for request_index in range(len(batch_lines)):
            assert endpoint == "/v1/chat/completions"

            body = batch_lines[request_index]["body"]
            tokens_in_request = sum(
                len(self.tokenizer.encode(message["content"]))
                for message in body["messages"]
            ) + body.get("max_tokens", body.get("max_completion_tokens", 0))

            reached_token_limit = (
                max_tokens_per_batch is not None
                and tokens_in_batch + tokens_in_request > max_tokens_per_batch
            )
            reached_request_limit = (
                max_requests_per_batch is not None
                and requests_in_batch >= max_requests_per_batch
            )

            if reached_token_limit or reached_request_limit:
                batch_infos.append(
                    self._upload_and_return_batch_info(
                        batch_call_id=batch_call_id,
                        index=batch_index,
                        jsonl_string="\n".join(jsonl_strings),
                        endpoint=endpoint,
                        requests_in_batch=requests_in_batch,
                        tokens_in_batch=tokens_in_batch,
                    )
                )

                if reached_token_limit:  # We can't do several batches concurrently
                    self.wait_for_batches(
                        [batch_info.batch_id for batch_info in batch_infos]
                    )

                requests_in_batch = 0
                tokens_in_batch = 0
                batch_index += 1
                jsonl_strings = []

            requests_in_batch += 1
            tokens_in_batch += tokens_in_request

            jsonl_strings.append(json.dumps(batch_lines[request_index]))

        if requests_in_batch > 0:
            batch_infos.append(
                self._upload_and_return_batch_info(
                    batch_call_id=batch_call_id,
                    index=batch_index,
                    jsonl_string="\n".join(jsonl_strings),
                    endpoint=endpoint,
                    requests_in_batch=requests_in_batch,
                    tokens_in_batch=tokens_in_batch,
                )
            )

        self.wait_for_batches([batch_info.batch_id for batch_info in batch_infos])
        outputs_raw = sum(
            (self.download_batch(batch_info) for batch_info in batch_infos), []
        )

        outputs_clean: list[dict | str | None] = [None for _ in range(len(batch_lines))]
        for output_raw in outputs_raw:
            original_index = int(output_raw["custom_id"].split("::")[-1])
            if output_raw["error"]:
                outputs_clean[original_index] = output_raw["error"]
            else:
                outputs_clean[original_index] = output_raw["response"]["body"]

        return outputs_clean
