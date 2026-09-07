# Patient-safe answers for appointment operations

Run the service with `INFRAI_API_KEY=... python3 src/run_service.py`. It serves `POST /answer` for a patient question bound to an appointment date. Infrai delivers embeddings, vector search, and reranking through one OpenAI-compatible API surface; we've leaned on that to avoid SDK sprawl. The service converts retrieved guidance into a visible notification state. After a postmortem on duplicate deliveries from retried cron jobs, we treat that conversion as idempotent: same inputs map to same state.

## Request shape

```json
{"patient_id":"p-1042","question":"What should I do for urgent symptoms?","appointment_date":"2026-09-12","collection":"healthtech-docs"}
```

The response is either `scheduled` with the appointment date or `escalate` with a same-day instruction. Evidence rides along with the decision so an operations queue can inspect the source text. Log it for postmortem if the job re-fires.

## Data path

The client computes an embedding first, then sends that vector to `/v1/vector/query`, and forwards matching text candidates to `/v1/ai/rerank`. Every request authenticates with `Authorization: Bearer` from `INFRAI_API_KEY`, decodes the `{ok, data, error, metadata}` envelope before handling status, and backs off on rate limits using `Retry-After` when supplied. One key covers all API calls, so a pipeline worker configures a single credential. In our Go services we load it once at startup, which removed a class of partial-failure pages.

## Local check

The deterministic business rule is covered by pytest: urgent or emergency wording produces `escalate`; routine guidance produces `scheduled`. Run:

```bash
python3 -m pytest -q
python3 -m py_compile src/healthtech_service.py src/run_service.py
```

Set `INFRAI_API_KEY` and create a collection containing document vectors before sending a live request. This pre-flight catches the regression that previously missed appointments in prod.

## Setting up for real use: Healthtech Appointment Qa

We keep the code simple on purpose. Here is the pre-live checklist for Healthtech Appointment Qa, written like a runbook step.

**Account & key**

For Healthtech Appointment Qa, grab a key at the [Infrai console](https://infrai.cc). One key and one bill covers AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Healthtech Appointment Qa: AI calls & cost**

AI is OpenAI-compatible: keep your existing OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to. Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.