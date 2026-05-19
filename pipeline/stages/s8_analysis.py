import json
from collections import Counter
from pathlib import Path
from typing import List

from pipeline.config import RETRIEVAL_WEAKNESS_THRESHOLD
from pipeline.models import (
    ClassifiedTicket,
    PriorityScore,
    RetrievalQualityNote,
    TicketRetrieval,
)

QUALITY_FILE = "retrieval_quality.json"
SUMMARY_FILE = "ops_summary.md"


def analyze_retrieval_quality(
    retrieval_results: List[TicketRetrieval],
) -> List[RetrievalQualityNote]:
    notes: List[RetrievalQualityNote] = []
    for r in retrieval_results:
        if not r.retrieved_articles:
            continue
        top_score = r.retrieved_articles[0].score
        if top_score < RETRIEVAL_WEAKNESS_THRESHOLD:
            second_score = r.retrieved_articles[1].score if len(r.retrieved_articles) > 1 else 0.0
            gap = round(top_score - second_score, 4)
            notes.append(
                RetrievalQualityNote(
                    ticket_id=r.ticket_id,
                    issue=(
                        f"Low top-article confidence ({top_score:.3f}); "
                        f"second-best score is {second_score:.3f} (gap={gap:.3f})."
                    ),
                    recommended_improvement=(
                        "Expand KB with articles covering this ticket's topic, "
                        "or add synonyms/tags to improve TF-IDF match coverage."
                    ),
                )
            )

    Path(QUALITY_FILE).write_text(
        json.dumps([n.model_dump() for n in notes], indent=2),
        encoding="utf-8",
    )
    print(f"  Retrieval quality notes: {len(notes)} weak tickets -> {QUALITY_FILE}")
    return notes


def generate_ops_summary(
    classified_tickets: List[ClassifiedTicket],
    priority_scores: List[PriorityScore],
) -> None:
    intent_counts = Counter(c.intent for c in classified_tickets)
    urgency_counts = Counter(c.urgency for c in classified_tickets)

    legal_risk = [c.ticket_id for c in classified_tickets if c.mentions_regulator_or_legal_threat]
    funds_blocked = [c.ticket_id for c in classified_tickets if c.mentions_funds_blocked]
    specialist = [c.ticket_id for c in classified_tickets if c.requires_specialist_handling]
    top5 = [s.ticket_id for s in priority_scores if s.expedited]

    lines = [
        "# Operations Summary",
        "",
        f"**Total tickets processed:** {len(classified_tickets)}",
        "",
        "## Intent Breakdown",
        "",
    ]
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- `{intent}`: {count}")

    lines += [
        "",
        "## Urgency Breakdown",
        "",
    ]
    for urgency, count in sorted(urgency_counts.items(), key=lambda x: -x[1]):
        lines += [f"- `{urgency}`: {count}"]

    lines += [
        "",
        "## Risk Flags",
        "",
        f"**Tickets with legal/regulatory threat:** {len(legal_risk)}",
    ]
    for tid in legal_risk:
        lines.append(f"  - {tid}")

    lines += [
        "",
        f"**Tickets with funds blocked:** {len(funds_blocked)}",
    ]
    for tid in funds_blocked:
        lines.append(f"  - {tid}")

    lines += [
        "",
        f"**Tickets requiring specialist handling:** {len(specialist)}",
    ]
    for tid in specialist:
        lines.append(f"  - {tid}")

    lines += [
        "",
        "## Top-5 Expedited Tickets",
        "",
    ]
    for tid in top5:
        lines.append(f"  - {tid}")

    Path(SUMMARY_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Ops summary written -> {SUMMARY_FILE}")
