import json
from pathlib import Path
from typing import Dict, List

from pipeline.llm_client import call_llm
from pipeline.models import (
    KBArticle,
    PriorityScore,
    RawTicket,
    ReplyDraft,
    RoutingDecision,
    TicketRetrieval,
)

OUTPUT_FILE = "reply_drafts.json"


def _build_prompt(
    ticket: RawTicket,
    routing: RoutingDecision,
    retrieval: TicketRetrieval,
    kb_map: Dict[str, KBArticle],
) -> str:
    kb_sections = []
    for art in retrieval.retrieved_articles:
        article = kb_map.get(art.article_id)
        if article:
            kb_sections.append(
                f"[{article.article_id}] {article.title}\n{article.body}"
            )
    kb_text = "\n\n".join(kb_sections)
    citations = [art.article_id for art in retrieval.retrieved_articles]

    return f"""You are a customer support agent drafting a reply to a customer ticket.

RULES:
- Acknowledge the customer's issue clearly and empathetically.
- Do NOT speculate about internal review decisions or triggers.
- Do NOT promise specific timelines or outcomes not supported by the knowledge base.
- Do NOT disclose internal routing, queue names, or review logic.
- Use the knowledge base guidance below where relevant.
- Include a human review gate note indicating this draft must be reviewed before sending.
- The reply must be appropriate for the channel: {ticket.channel}.
- Be concise and professional.

TICKET:
ticket_id: {ticket.ticket_id}
channel: {ticket.channel}
subject: {ticket.subject}
message: {ticket.message}

RELEVANT KNOWLEDGE BASE ARTICLES:
{kb_text}

Return ONLY a JSON object with EXACTLY these fields:
- ticket_id: "{ticket.ticket_id}"
- channel: "{ticket.channel}"
- draft_reply: the full reply text
- citations: {json.dumps(citations)}
- review_gate_note: a one-sentence note for the human reviewer

No explanation, no markdown wrapper."""


def draft_replies(
    priority_scores: List[PriorityScore],
    raw_tickets: List[RawTicket],
    retrieval_results: List[TicketRetrieval],
    routing_decisions: List[RoutingDecision],
    kb_articles: List[KBArticle],
) -> List[ReplyDraft]:
    top5_ids = {s.ticket_id for s in priority_scores if s.expedited}
    raw_map: Dict[str, RawTicket] = {t.ticket_id: t for t in raw_tickets}
    retrieval_map: Dict[str, TicketRetrieval] = {r.ticket_id: r for r in retrieval_results}
    routing_map: Dict[str, RoutingDecision] = {d.ticket_id: d for d in routing_decisions}
    kb_map: Dict[str, KBArticle] = {a.article_id: a for a in kb_articles}

    drafts: List[ReplyDraft] = []
    for ticket_id in top5_ids:
        ticket = raw_map[ticket_id]
        routing = routing_map[ticket_id]
        retrieval = retrieval_map[ticket_id]
        prompt = _build_prompt(ticket, routing, retrieval, kb_map)
        raw = call_llm(
            stage="reply_drafting",
            prompt=prompt,
            input_artifacts=["priority_scores.json", "routing_decisions.json", "retrieval_results.json"],
            output_artifact=OUTPUT_FILE,
            temperature=0.3,
            max_tokens=1024,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        drafts.append(ReplyDraft(**parsed))

    Path(OUTPUT_FILE).write_text(
        json.dumps([d.model_dump() for d in drafts], indent=2),
        encoding="utf-8",
    )
    print(f"  Drafted replies for {len(drafts)} top-priority tickets -> {OUTPUT_FILE}")
    return drafts
