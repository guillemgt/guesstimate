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

    def wait_for_batch(self, batch_id: str, timeout: Optional[int] = 60):
        print("Waiting for batch", batch_id)
        batch_object = self.client.batches.retrieve(batch_id)
        while batch_object.status not in FINISHED_BATCH_STATUSES:
            time.sleep(timeout)
            batch_object = self.client.batches.retrieve(batch_id)

    def download_batch(self, metadata: BatchInfo):
        batch_object = self.client.batches.retrieve(metadata.batch_id)
        content = self.client.files.content(batch_object.output_file_id)
        decoded_content = content.response.content.decode("utf-8")
        if self.log_dir is not None:
            with open(
                self._get_file_path(
                    batch_call_id=metadata.batch_call_id,
                    index=metadata.index,
                    suffix="output",
                ),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(decoded_content)

        return [json.loads(line) for line in decoded_content.split("\n") if line]

    def _upload_and_download(
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
                if metadata["hash"] == whole_content_hash or True:
                    file_handler.close()
                    if os.path.exists(
                        self._get_file_path(batch_call_id, index, "output")
                    ):
                        decoded_content = open(
                            self._get_file_path(batch_call_id, index, "output"),
                            "r",
                            encoding="utf-8",
                        ).read()
                        return [
                            json.loads(line)
                            for line in decoded_content.split("\n")
                            if line
                        ]
                    metadata = BatchInfo(**metadata)
                    print(f"Waiting for {metadata.batch_id}")
                    self.wait_for_batch(metadata.batch_id)
                    return self.download_batch(metadata)

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
        self.wait_for_batch(batch_object.id)
        return self.download_batch(batch_info)

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

        outputs_raw = []

        batch_index = 0
        jsonl_strings = []
        for request_index in range(len(batch_lines)):
            assert endpoint == "/v1/chat/completions"

            body = batch_lines[request_index]["body"]
            tokens_in_request = sum(
                len(self.tokenizer.encode(message["content"]))
                for message in body["messages"]
            ) + body.get("max_tokens", body.get("max_completion_tokens", 0))

            if (
                max_tokens_per_batch is not None
                and tokens_in_batch + tokens_in_request > max_tokens_per_batch
            ) or (
                max_requests_per_batch is not None
                and requests_in_batch >= max_requests_per_batch
            ):
                outputs_raw.extend(
                    self._upload_and_download(
                        batch_call_id=batch_call_id,
                        index=batch_index,
                        jsonl_string="\n".join(jsonl_strings),
                        endpoint=endpoint,
                        requests_in_batch=requests_in_batch,
                        tokens_in_batch=tokens_in_batch,
                    )
                )

                requests_in_batch = 0
                tokens_in_batch = 0
                batch_index += 1
                jsonl_strings = []

            requests_in_batch += 1
            tokens_in_batch += tokens_in_request

            jsonl_strings.append(json.dumps(batch_lines[request_index]))

        if requests_in_batch > 0:
            outputs_raw.extend(
                self._upload_and_download(
                    batch_call_id=batch_call_id,
                    index=batch_index,
                    jsonl_string="\n".join(jsonl_strings),
                    endpoint=endpoint,
                    requests_in_batch=requests_in_batch,
                    tokens_in_batch=tokens_in_batch,
                )
            )

        outputs_clean: list[dict | str | None] = [None for _ in range(len(batch_lines))]
        for output_raw in outputs_raw:
            original_index = int(output_raw["custom_id"].split("::")[-1])
            if output_raw["error"]:
                outputs_clean[original_index] = output_raw["error"]
            else:
                outputs_clean[original_index] = output_raw["response"]["body"]

        return outputs_clean
