import json
from pathlib import Path
from typing import List

from pipeline.config import INTENT_VALUES, SENTIMENT_VALUES, URGENCY_VALUES
from pipeline.llm_client import call_llm
from pipeline.models import ClassifiedTicket, PreprocessedTicket

OUTPUT_FILE = "classified_tickets.json"


def _build_prompt(tickets: List[PreprocessedTicket]) -> str:
    tickets_json = json.dumps(
        [
            {
                "ticket_id": t.ticket_id,
                "subject": t.subject_for_processing,
                "message": t.message_for_processing,
                "original_language": t.original_language,
                "translated": t.translated,
            }
            for t in tickets
        ],
        indent=2,
    )

    return f"""You are a customer support classification engine. Classify each ticket below.

CONTROLLED VOCABULARIES — use ONLY these exact values:

intent: {sorted(INTENT_VALUES)}
urgency: {sorted(URGENCY_VALUES)}
sentiment: {sorted(SENTIMENT_VALUES)}

For each ticket output a JSON object with EXACTLY these fields:
- ticket_id: string
- intent: one of the allowed intent values
- urgency: one of the allowed urgency values
- sentiment: one of the allowed sentiment values
- mentions_funds_blocked: boolean — true if the customer mentions blocked funds, frozen balance, or inability to access money
- mentions_regulator_or_legal_threat: boolean — true if the customer mentions filing a complaint with a regulator, taking legal action, or similar threats
- requires_specialist_handling: boolean — true if the ticket involves compliance, legal risk, account restriction, or complex financial investigation

Return ONLY a JSON array of objects, one per ticket. No explanation, no markdown.

TICKETS:
{tickets_json}"""


def classify_tickets(tickets: List[PreprocessedTicket]) -> List[ClassifiedTicket]:
    prompt = _build_prompt(tickets)
    raw = call_llm(
        stage="ticket_classification",
        prompt=prompt,
        input_artifacts=["preprocessed_tickets.json"],
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

    preprocessed_map = {t.ticket_id: t for t in tickets}

    result: List[ClassifiedTicket] = []
    for item in parsed:
        intent = item["intent"]
        urgency = item["urgency"]
        sentiment = item["sentiment"]
        if intent not in INTENT_VALUES:
            raise ValueError(f"Invalid intent '{intent}' for ticket {item['ticket_id']}")
        if urgency not in URGENCY_VALUES:
            raise ValueError(f"Invalid urgency '{urgency}' for ticket {item['ticket_id']}")
        if sentiment not in SENTIMENT_VALUES:
            raise ValueError(f"Invalid sentiment '{sentiment}' for ticket {item['ticket_id']}")
        # Merge original_language and translated from preprocessed source
        pre = preprocessed_map.get(item["ticket_id"])
        if pre:
            item["original_language"] = pre.original_language
            item["translated"] = pre.translated
        result.append(ClassifiedTicket(**item))

    Path(OUTPUT_FILE).write_text(
        json.dumps([c.model_dump() for c in result], indent=2),
        encoding="utf-8",
    )
    print(f"  Classified {len(result)} tickets -> {OUTPUT_FILE}")
    return result
