import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from groq import Groq

from pipeline.config import GROQ_API_KEY, GROQ_MODEL

LLM_LOG_FILE = Path("llm_calls.jsonl")
PROVIDER = "groq"

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def call_llm(
    stage: str,
    prompt: str,
    input_artifacts: List[str],
    output_artifact: str,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or ""
    _log_call(stage, prompt, input_artifacts, output_artifact)
    return content


def _log_call(
    stage: str,
    prompt: str,
    input_artifacts: List[str],
    output_artifact: str,
) -> None:
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    record = {
        "stage": stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": PROVIDER,
        "model": GROQ_MODEL,
        "prompt_hash": prompt_hash,
        "input_artifacts": input_artifacts,
        "output_artifact": output_artifact,
    }
    with open(LLM_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
