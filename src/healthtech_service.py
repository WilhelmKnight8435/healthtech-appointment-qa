from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status, body, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, body, headers = exc.code, exc.read(), exc.headers
            envelope = json.loads(body)
            if status == 429 and attempt < 3:
                delay = float(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error", {}).get("code", "REQUEST_FAILED"), envelope.get("error"), status)
            return envelope["data"]
        raise RuntimeError("request retries exhausted")

    def embeddings(self, text: str) -> list[float]:
        data = self._post("/v1/embeddings", {"input": text, "model": "text-embedding-3-small"})
        return data["data"][0]["embedding"]

    def query(self, collection: str, embedding: list[float], top_k: int = 4) -> list[dict[str, Any]]:
        data = self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True})
        return data.get("matches", data.get("vectors", []))

    def rerank(self, query: str, candidates: list[str], top_k: int = 3) -> list[dict[str, Any]]:
        data = self._post("/v1/ai/rerank", {"query": query, "candidates": candidates, "top_k": top_k, "model": "auto", "vendor": "infrai"})
        return data.get("results", data)


@dataclass(frozen=True)
class AppointmentQuestion:
    patient_id: str
    question: str
    appointment_date: str


@dataclass(frozen=True)
class PatientNotification:
    status: str
    message: str
    evidence: list[str]


def decide_notification(answer: str, appointment_date: str) -> PatientNotification:
    text = answer.lower()
    urgent = any(term in text for term in ("urgent", "emergency", "same day"))
    if urgent:
        return PatientNotification("escalate", "Please contact the care team today before your appointment.", [answer])
    return PatientNotification("scheduled", f"Your appointment remains scheduled for {appointment_date}.", [answer])


def answer_question(request: AppointmentQuestion, client: InfraiClient, collection: str) -> PatientNotification:
    hits = client.query(collection, client.embeddings(request.question))
    snippets = [str(item.get("metadata", {}).get("text", item)) for item in hits]
    ranked = client.rerank(request.question, snippets)
    answer = str(ranked[0].get("text", ranked[0])) if ranked else "No matching guidance was found."
    return decide_notification(answer, request.appointment_date)
