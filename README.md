# AI Support-Ops Pipeline

A replayable, multi-stage AI pipeline for customer support operations. Ingests tickets from disk, normalises multilingual inputs, classifies intent and urgency, retrieves relevant knowledge-base guidance, scores and routes tickets to internal queues, and drafts safe customer replies — all as separate, auditable pipeline stages.

---

## Pipeline Overview

```
tickets.json          kb_articles.json
      │                      │
      ▼                      ▼
┌─────────────┐      ┌──────────────────┐
│  S1 · LOAD  │      │  S4 · RETRIEVAL  │ ◄── TF-IDF (deterministic)
└──────┬──────┘      └────────┬─────────┘
       │                      │
       ▼                      │
┌──────────────────┐          │
│ S2 · PREPROCESS  │ ◄── LLM  │  (translate non-English tickets)
└──────┬───────────┘          │
       │                      │
       ▼                      │
┌──────────────────┐          │
│ S3 · CLASSIFY    │ ◄── LLM  │  (intent · urgency · sentiment)
└──────┬───────────┘          │
       └──────────────────────┘
                  │
                  ▼
       ┌──────────────────┐
       │ S5 · PRIORITY    │  (deterministic formula → top-5)
       └──────┬───────────┘
              │
              ▼
       ┌──────────────────┐
       │  S6 · ROUTING    │ ◄── LLM  (assign internal queues)
       └──────┬───────────┘
              │
              ▼
       ┌──────────────────┐
       │  S7 · REPLIES    │ ◄── LLM  (top-5 only · KB-grounded)
       └──────┬───────────┘
              │
       ┌──────┴───────────┐
       │  S8 · ANALYSIS   │  (retrieval quality · ops summary)
       │  S9 · HANDOFF    │ ◄── LLM  (handoff memory · stretch)
       └──────────────────┘
```

**State machine:** `INIT → TICKETS_LOADED → PREPROCESSING_COMPLETE → TICKETS_CLASSIFIED → KB_RETRIEVAL_COMPLETE → PRIORITY_SCORES_COMPUTED → ROUTING_COMPLETE → REPLY_DRAFTS_GENERATED → VALIDATION_COMPLETE → RESULTS_FINALISED`

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| LLM provider | [Groq](https://groq.com) — `llama-3.3-70b-versatile` |
| Retrieval | scikit-learn TF-IDF + cosine similarity |
| Schema validation | Pydantic v2 |
| Dependency management | pip + `requirements.txt` |

---

## Quickstart

### 1 · Prerequisites

- Python 3.11+
- A Groq API key — get one free at [console.groq.com](https://console.groq.com)

### 2 · Install

```bash
# Clone and enter the repo
git clone https://github.com/dhanashree23112003/deriv-test.git
cd deriv-test

# Create virtual environment and install dependencies
make install
```

### 3 · Configure

```bash
cp .env.example .env
# Edit .env and set your GROQ_API_KEY
```

### 4 · Run the pipeline

```bash
make run
```

All output artifacts are written to the repo root.

### 5 · Validate

```bash
make validate
```

Exits `0` if all checks pass; writes a human-readable report to `validation_report.md`.

### 6 · Clean generated artifacts

```bash
make clean
```

---

## Input Files

| File | Description |
|---|---|
| `tickets.json` | Customer support tickets (see schema below) |
| `kb_articles.json` | Help-centre knowledge-base articles |

The pipeline reads both files from disk at runtime. You can replace them with any equivalent dataset that uses the same schema and the pipeline will process it correctly.

**Ticket schema:**
```json
{
  "ticket_id": "T01",
  "channel": "email",
  "customer_tier": "standard",
  "language_hint": "en",
  "subject": "...",
  "message": "...",
  "created_at": "2025-04-14T08:10:00Z"
}
```

---

## Output Artifacts

| Artifact | Stage | Description |
|---|---|---|
| `preprocessed_tickets.json` | S2 | Original + English-normalised text; `translated` flag |
| `classified_tickets.json` | S3 | Intent, urgency, sentiment, risk flags per ticket |
| `retrieval_results.json` | S4 | Top-2 KB articles per ticket with TF-IDF scores |
| `priority_scores.json` | S5 | Deterministic scores, sorted descending; top-5 flagged |
| `routing_decisions.json` | S6 | Internal queue assignments + reply safety labels |
| `reply_drafts.json` | S7 | KB-grounded draft replies for top-5 tickets |
| `retrieval_quality.json` | S8 | Weak-retrieval analysis with improvement notes |
| `ops_summary.md` | S8 | Batch summary: intent counts, urgency counts, risk flags |
| `handoff_memory.json` | S9 | Structured handoff objects for top-5 tickets |
| `validation_report.md` | — | Pass/fail table for all validation checks |
| `llm_calls.jsonl` | — | Append-only log of every LLM call |

---

## Controlled Vocabularies

All LLM outputs are validated against these vocabularies in code. Invalid values raise an error and are never persisted.

| Field | Allowed values |
|---|---|
| `intent` | `withdrawal_issue` · `deposit_issue` · `login_access` · `verification_kyc` · `account_restriction` · `product_behavior` · `privacy_request` · `statement_export` · `api_support` · `other` |
| `urgency` | `critical` · `high` · `medium` · `low` |
| `sentiment` | `calm` · `frustrated` · `angry` · `neutral` |
| `queue` | `General Support` · `Payments` · `Compliance` · `Risk` · `Engineering` · `Product` · `Privacy` · `Developer Support` |
| `reply_safety_label` | `safe_to_send_after_review` · `needs_specialist_review` · `needs_legal_or_compliance_review` |

---

## Priority Scoring Formula

Priority is computed **entirely in code** — the LLM is never used for scoring.

```
score = base_urgency
      + tier_bonus
      + funds_blocked_bonus
      + regulator_threat_bonus
      + specialist_handling_bonus
      + retrieval_weakness_bonus

where:
  base_urgency            critical=40  high=25  medium=10  low=3
  tier_bonus              vip=+10      standard=+0
  funds_blocked_bonus     +20  if mentions_funds_blocked
  regulator_threat_bonus  +25  if mentions_regulator_or_legal_threat
  specialist_bonus        +10  if requires_specialist_handling
  retrieval_weakness      +8   if top retrieval score < 0.55
```

Tickets are sorted by `priority_score` descending. The top 5 are flagged `expedited: true` and receive reply drafts.

---

## LLM Call Logging

Every LLM call is appended to `llm_calls.jsonl` as a single JSON object:

```json
{
  "stage": "ticket_classification",
  "timestamp": "2025-04-14T08:10:00.000000+00:00",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "prompt_hash": "6041a62d...",
  "input_artifacts": ["preprocessed_tickets.json"],
  "output_artifact": "classified_tickets.json"
}
```

Separate log entries are produced for: `preprocessing_translation`, `ticket_classification`, `queue_routing`, `reply_drafting`, and `handoff_memory`.

---

## Project Structure

```
deriv-test/
├── tickets.json                  # Input: support tickets
├── kb_articles.json              # Input: knowledge-base articles
│
├── pipeline/
│   ├── config.py                 # Stage enum, controlled vocabularies, env
│   ├── models.py                 # Pydantic schemas for all artifacts
│   ├── llm_client.py            # Groq client + llm_calls.jsonl logger
│   └── stages/
│       ├── s1_loader.py         # Load & validate input files
│       ├── s2_preprocessing.py  # Multilingual normalisation (LLM)
│       ├── s3_classification.py # Intent/urgency/sentiment (LLM)
│       ├── s4_retrieval.py      # TF-IDF knowledge retrieval
│       ├── s5_priority.py       # Deterministic priority scoring
│       ├── s6_routing.py        # Queue routing (LLM)
│       ├── s7_reply.py          # Reply drafting (LLM, top-5 only)
│       ├── s8_analysis.py       # Retrieval quality + ops summary
│       └── s9_handoff.py        # Handoff memory (LLM, stretch)
│
├── orchestrator.py              # State machine + pipeline runner
├── run.py                       # Entry point
├── validate.py                  # Validation script (17 checks)
├── Makefile                     # install / run / validate / clean
├── requirements.txt
└── .env.example
```

---

## Makefile Reference

| Command | Description |
|---|---|
| `make install` | Create `.venv` and install all dependencies |
| `make run` | Execute the full pipeline |
| `make validate` | Run all 17 validation checks |
| `make clean` | Delete all generated artifacts |

---

## Validation Checks

`validate.py` verifies:

1. All required artifacts exist
2. All JSON files parse without error
3. All tickets appear in every artifact
4. Non-English tickets have `translated=true` and non-empty English text
5. Classified outputs use only controlled vocabularies
6. Retrieval results reference valid KB article IDs
7. Each ticket has exactly 2 retrieved articles
8. Priority scores match the deterministic formula
9. Top-5 expedited tickets are the highest-scored
10. Routing queues and safety labels use controlled vocabularies
11. Reply drafts exist for all top-5 tickets
12. Reply draft citations reference valid KB article IDs
13. `llm_calls.jsonl` has separate records for all required stages
