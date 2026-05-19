import json
from pathlib import Path
from typing import Dict, List

from pipeline.config import QUEUE_VALUES, REPLY_SAFETY_LABELS
from pipeline.llm_client import call_llm
from pipeline.models import (
    ClassifiedTicket,
    PriorityScore,
    RoutingDecision,
    TicketRetrieval,
)

OUTPUT_FILE = "routing_decisions.json"


def _build_prompt(
    classified_tickets: List[ClassifiedTicket],
    retrieval_results: List[TicketRetrieval],
    priority_scores: List[PriorityScore],
) -> str:
    top5_ids = {s.ticket_id for s in priority_scores if s.expedited}

    classified_json = json.dumps([c.model_dump() for c in classified_tickets], indent=2)
    retrieval_json = json.dumps([r.model_dump() for r in retrieval_results], indent=2)
    top5_json = json.dumps(
        [s.model_dump() for s in priority_scores if s.expedited], indent=2
    )

    return f"""You are a customer support routing engine. Assign each ticket to one or more internal queues.

ALLOWED QUEUES (use ONLY these exact values):
{sorted(QUEUE_VALUES)}

ALLOWED REPLY SAFETY LABELS (use ONLY these exact values):
{sorted(REPLY_SAFETY_LABELS)}

RULES:
- Multiple queues may be assigned where genuinely justified.
- routing_rationale must be concise (1-2 sentences), specific, and evidence-based.
- Use reply_safety_label "needs_legal_or_compliance_review" if the ticket mentions legal threats or regulators.
- Use "needs_specialist_review" if the ticket involves account restriction, complex verification, or specialist escalation.
- Use "safe_to_send_after_review" only for straightforward informational queries.
- Top-5 priority tickets (expedited=true) should be routed with extra care.

Return ONLY a JSON array of objects, one per ticket, with EXACTLY these fields:
- ticket_id: string
- queues: array of queue name strings
- routing_rationale: string
- reply_safety_label: string

No explanation, no markdown.

CLASSIFIED TICKETS:
{classified_json}

RETRIEVAL RESULTS:
{retrieval_json}

TOP-5 PRIORITY TICKETS:
{top5_json}"""


def route_tickets(
    classified_tickets: List[ClassifiedTicket],
    retrieval_results: List[TicketRetrieval],
    priority_scores: List[PriorityScore],
) -> List[RoutingDecision]:
    prompt = _build_prompt(classified_tickets, retrieval_results, priority_scores)
    raw = call_llm(
        stage="queue_routing",
        prompt=prompt,
        input_artifacts=["classified_tickets.json", "retrieval_results.json", "priority_scores.json"],
        output_artifact=OUTPUT_FILE,
        temperature=0.1,
        max_tokens=4096,
    )
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw.strip())

    result: List[RoutingDecision] = []
    for item in parsed:
        queues = item["queues"]
        safety = item["reply_safety_label"]
        for q in queues:
            if q not in QUEUE_VALUES:
                raise ValueError(f"Invalid queue '{q}' for ticket {item['ticket_id']}")
        if safety not in REPLY_SAFETY_LABELS:
            raise ValueError(f"Invalid reply_safety_label '{safety}' for ticket {item['ticket_id']}")
        result.append(RoutingDecision(**item))

    Path(OUTPUT_FILE).write_text(
        json.dumps([r.model_dump() for r in result], indent=2),
        encoding="utf-8",
    )
    print(f"  Routed {len(result)} tickets -> {OUTPUT_FILE}")
    return result
