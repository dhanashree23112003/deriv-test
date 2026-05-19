import json
from pathlib import Path
from typing import Dict, List

from pipeline.llm_client import call_llm
from pipeline.models import (
    ClassifiedTicket,
    HandoffMemory,
    PriorityScore,
    RawTicket,
    RoutingDecision,
    TicketRetrieval,
)

OUTPUT_FILE = "handoff_memory.json"


def _build_prompt(
    ticket: RawTicket,
    classified: ClassifiedTicket,
    routing: RoutingDecision,
    retrieval: TicketRetrieval,
) -> str:
    return f"""You are creating a compact handoff object for a follow-up support agent.

TICKET:
ticket_id: {ticket.ticket_id}
channel: {ticket.channel}
customer_tier: {ticket.customer_tier}
subject: {ticket.subject}
message: {ticket.message}
intent: {classified.intent}
urgency: {classified.urgency}
sentiment: {classified.sentiment}
mentions_funds_blocked: {classified.mentions_funds_blocked}
mentions_regulator_or_legal_threat: {classified.mentions_regulator_or_legal_threat}
requires_specialist_handling: {classified.requires_specialist_handling}
queues: {routing.queues}
reply_safety_label: {routing.reply_safety_label}

Return ONLY a JSON object with EXACTLY these fields:
- ticket_id: "{ticket.ticket_id}"
- customer_problem_summary: concise 1-2 sentence summary of the customer's core problem
- open_questions: array of 2-3 questions the follow-up agent should clarify
- do_not_say: array of 2-3 specific things the agent must NOT say or promise
- recommended_next_action: one sentence describing the most important next step

No explanation, no markdown."""


def generate_handoff_memory(
    priority_scores: List[PriorityScore],
    raw_tickets: List[RawTicket],
    classified_tickets: List[ClassifiedTicket],
    routing_decisions: List[RoutingDecision],
    retrieval_results: List[TicketRetrieval],
) -> List[HandoffMemory]:
    top5_ids = {s.ticket_id for s in priority_scores if s.expedited}
    raw_map: Dict[str, RawTicket] = {t.ticket_id: t for t in raw_tickets}
    classified_map: Dict[str, ClassifiedTicket] = {c.ticket_id: c for c in classified_tickets}
    routing_map: Dict[str, RoutingDecision] = {d.ticket_id: d for d in routing_decisions}
    retrieval_map: Dict[str, TicketRetrieval] = {r.ticket_id: r for r in retrieval_results}

    handoffs: List[HandoffMemory] = []
    for ticket_id in top5_ids:
        prompt = _build_prompt(
            raw_map[ticket_id],
            classified_map[ticket_id],
            routing_map[ticket_id],
            retrieval_map[ticket_id],
        )
        raw = call_llm(
            stage="handoff_memory",
            prompt=prompt,
            input_artifacts=["priority_scores.json", "classified_tickets.json", "routing_decisions.json"],
            output_artifact=OUTPUT_FILE,
            temperature=0.2,
            max_tokens=512,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        handoffs.append(HandoffMemory(**parsed))

    Path(OUTPUT_FILE).write_text(
        json.dumps([h.model_dump() for h in handoffs], indent=2),
        encoding="utf-8",
    )
    print(f"  Handoff memory objects for {len(handoffs)} tickets -> {OUTPUT_FILE}")
    return handoffs
