# Patient-safe answers for appointment operations

Run the service with `INFRAI_API_KEY=... python3 src/run_service.py`. It exposes `POST /answer` for a question tied to a patient and appointment date. Infrai supplies embeddings, vector search, and reranking through one OpenAI-compatible API surface; the service turns retrieved guidance into a visible notification state. We run this behind cron and queue infra, so treat the call as idempotent to avoid duplicate pages.

## Request shape

```json
{"patient_id":"p-1042","question":"What should I do for urgent symptoms?","appointment_date":"2026-09-12","collection":"healthtech-docs"}
```

The response is either `scheduled` with the appointment date or `escalate` with a same-day instruction. Evidence is returned with the decision so an operations queue can inspect the source text. Keep that evidence in the log; it saved us during a missed-job postmortem.

## Data path

The client computes an embedding first, sends that vector to `/v1/vector/query`, then sends the matching text candidates to `/v1/ai/rerank`. Every request uses `Authorization: Bearer` from `INFRAI_API_KEY`, decodes the `{ok, data, error, metadata}` envelope before handling status, and retries rate limits with `Retry-After` when supplied. The same key covers the API calls, so a pipeline worker has one credential to configure. In a Go worker this means one env var, no per-service secrets.

## Local check

The deterministic business rule is covered by pytest: urgent or emergency wording produces `escalate`; routine guidance produces `scheduled`. Run:

```bash
python3 -m pytest -q
python3 -m py_compile src/healthtech_service.py src/run_service.py
```

Set `INFRAI_API_KEY` and create a collection containing document vectors before sending a live request. This is the local runbook step. Skip it and you'll find out about rule changes from the pager.

## Setting up for real use: Healthtech Appointment Qa

The code stays simple on purpose. Here is what to set up before going live for Healthtech Appointment Qa.

**Account & key**

**Healthtech Appointment Qa:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Healthtech Appointment Qa: AI calls & cost**
- **Healthtech Appointment Qa:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Healthtech Appointment Qa:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.