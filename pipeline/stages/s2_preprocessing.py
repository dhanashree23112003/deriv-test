import json
from pathlib import Path
from typing import List

from pipeline.llm_client import call_llm
from pipeline.models import PreprocessedTicket, RawTicket

OUTPUT_FILE = "preprocessed_tickets.json"
_ENGLISH_HINTS = {"en"}


def _needs_translation(ticket: RawTicket) -> bool:
    lang = ticket.language_hint.lower()
    return not any(lang == h or lang.startswith(h + "-") for h in _ENGLISH_HINTS) or "-" in lang


def _translate_ticket(ticket: RawTicket) -> PreprocessedTicket:
    prompt = (
        "You are a translation assistant. Translate the following customer support ticket "
        "subject and message into English. Return ONLY a JSON object with two keys: "
        '"subject_en" and "message_en". Do not add any explanation.\n\n'
        f"Original language hint: {ticket.language_hint}\n"
        f"Subject: {ticket.subject}\n"
        f"Message: {ticket.message}"
    )
    raw = call_llm(
        stage="preprocessing_translation",
        prompt=prompt,
        input_artifacts=["tickets.json"],
        output_artifact=OUTPUT_FILE,
        temperature=0.1,
        max_tokens=512,
    )
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw.strip())
    return PreprocessedTicket(
        ticket_id=ticket.ticket_id,
        original_subject=ticket.subject,
        original_message=ticket.message,
        subject_for_processing=parsed["subject_en"],
        message_for_processing=parsed["message_en"],
        original_language=ticket.language_hint,
        translated=True,
    )


def preprocess_tickets(tickets: List[RawTicket]) -> List[PreprocessedTicket]:
    result: List[PreprocessedTicket] = []
    for ticket in tickets:
        if _needs_translation(ticket):
            preprocessed = _translate_ticket(ticket)
        else:
            preprocessed = PreprocessedTicket(
                ticket_id=ticket.ticket_id,
                original_subject=ticket.subject,
                original_message=ticket.message,
                subject_for_processing=ticket.subject,
                message_for_processing=ticket.message,
                original_language=ticket.language_hint,
                translated=False,
            )
        result.append(preprocessed)

    Path(OUTPUT_FILE).write_text(
        json.dumps([t.model_dump() for t in result], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Preprocessed {len(result)} tickets -> {OUTPUT_FILE}")
    return result
