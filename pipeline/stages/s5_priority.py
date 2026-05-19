import json
from pathlib import Path
from typing import Dict, List

from pipeline.config import RETRIEVAL_WEAKNESS_THRESHOLD, TOP_N_EXPEDITED
from pipeline.models import ClassifiedTicket, PriorityScore, RawTicket, TicketRetrieval

OUTPUT_FILE = "priority_scores.json"

_URGENCY_BASE = {"critical": 40, "high": 25, "medium": 10, "low": 3}
_TIER_BONUS = {"vip": 10, "standard": 0}


def _compute_score(
    classified: ClassifiedTicket,
    ticket: RawTicket,
    retrieval: TicketRetrieval,
) -> int:
    base = _URGENCY_BASE.get(classified.urgency, 3)
    tier_bonus = _TIER_BONUS.get(ticket.customer_tier, 0)
    funds_bonus = 20 if classified.mentions_funds_blocked else 0
    legal_bonus = 25 if classified.mentions_regulator_or_legal_threat else 0
    specialist_bonus = 10 if classified.requires_specialist_handling else 0
    top_score = retrieval.retrieved_articles[0].score if retrieval.retrieved_articles else 0.0
    weakness_bonus = 8 if top_score < RETRIEVAL_WEAKNESS_THRESHOLD else 0
    return base + tier_bonus + funds_bonus + legal_bonus + specialist_bonus + weakness_bonus


def compute_priority(
    classified_tickets: List[ClassifiedTicket],
    raw_tickets: List[RawTicket],
    retrieval_results: List[TicketRetrieval],
) -> List[PriorityScore]:
    classified_map: Dict[str, ClassifiedTicket] = {c.ticket_id: c for c in classified_tickets}
    raw_map: Dict[str, RawTicket] = {t.ticket_id: t for t in raw_tickets}
    retrieval_map: Dict[str, TicketRetrieval] = {r.ticket_id: r for r in retrieval_results}

    scores: List[PriorityScore] = []
    for ticket_id, classified in classified_map.items():
        raw = raw_map[ticket_id]
        retrieval = retrieval_map[ticket_id]
        top_score = retrieval.retrieved_articles[0].score if retrieval.retrieved_articles else 0.0
        score = _compute_score(classified, raw, retrieval)
        scores.append(
            PriorityScore(
                ticket_id=ticket_id,
                priority_score=score,
                urgency=classified.urgency,
                customer_tier=raw.customer_tier,
                mentions_funds_blocked=classified.mentions_funds_blocked,
                mentions_regulator_or_legal_threat=classified.mentions_regulator_or_legal_threat,
                requires_specialist_handling=classified.requires_specialist_handling,
                retrieval_weakness=top_score < RETRIEVAL_WEAKNESS_THRESHOLD,
                expedited=False,
            )
        )

    scores.sort(key=lambda s: s.priority_score, reverse=True)
    for i, score in enumerate(scores):
        score.expedited = i < TOP_N_EXPEDITED

    Path(OUTPUT_FILE).write_text(
        json.dumps([s.model_dump() for s in scores], indent=2),
        encoding="utf-8",
    )
    top5 = [s.ticket_id for s in scores if s.expedited]
    print(f"  Computed priority for {len(scores)} tickets -> {OUTPUT_FILE}")
    print(f"  Top-5 expedited: {top5}")
    return scores
