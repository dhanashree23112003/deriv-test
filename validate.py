"""
Validation script for the AI support-ops pipeline.
Checks all artifacts produced by run.py and writes validation_report.md.
Exits with code 1 if any check fails.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()

from pipeline.config import (
    INTENT_VALUES,
    QUEUE_VALUES,
    REPLY_SAFETY_LABELS,
    RETRIEVAL_WEAKNESS_THRESHOLD,
    SENTIMENT_VALUES,
    TOP_N_EXPEDITED,
    URGENCY_VALUES,
)
from pipeline.stages.s5_priority import _TIER_BONUS, _URGENCY_BASE

REPORT_FILE = "validation_report.md"

checks: List[Tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = "") -> bool:
    checks.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f": {detail}" if detail else ""))
    return passed


def load_json(path: str):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def validate() -> bool:
    print("Running validation checks...\n")
    all_ok = True

    # ── Check 1: Required artifacts exist ──────────────────────────────────
    required_files = [
        "preprocessed_tickets.json",
        "classified_tickets.json",
        "retrieval_results.json",
        "priority_scores.json",
        "routing_decisions.json",
        "reply_drafts.json",
        "llm_calls.jsonl",
    ]
    missing = [f for f in required_files if not Path(f).exists()]
    ok = record("Required artifacts exist", len(missing) == 0, f"Missing: {missing}" if missing else "")
    all_ok = all_ok and ok

    # ── Check 2: JSON files are valid ──────────────────────────────────────
    json_files = [f for f in required_files if f.endswith(".json")]
    invalid_json = []
    for f in json_files:
        if Path(f).exists():
            try:
                json.loads(Path(f).read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                invalid_json.append(f"{f}: {e}")
    ok = record("All JSON files are valid", len(invalid_json) == 0, str(invalid_json) if invalid_json else "")
    all_ok = all_ok and ok

    # Load data for subsequent checks
    raw_tickets = load_json("tickets.json") or []
    kb_data = load_json("kb_articles.json") or []
    preprocessed = load_json("preprocessed_tickets.json") or []
    classified = load_json("classified_tickets.json") or []
    retrieval = load_json("retrieval_results.json") or []
    priority = load_json("priority_scores.json") or []
    routing = load_json("routing_decisions.json") or []
    reply_drafts = load_json("reply_drafts.json") or []

    all_ticket_ids = {t["ticket_id"] for t in raw_tickets}
    kb_article_ids = {a["article_id"] for a in kb_data}

    # ── Check 3: All tickets processed in every artifact ──────────────────
    for artifact_name, data in [
        ("preprocessed_tickets.json", preprocessed),
        ("classified_tickets.json", classified),
        ("retrieval_results.json", retrieval),
        ("priority_scores.json", priority),
        ("routing_decisions.json", routing),
    ]:
        artifact_ids = {d["ticket_id"] for d in data}
        missing_ids = all_ticket_ids - artifact_ids
        ok = record(
            f"All tickets in {artifact_name}",
            len(missing_ids) == 0,
            f"Missing: {missing_ids}" if missing_ids else "",
        )
        all_ok = all_ok and ok

    # ── Check 4: Non-English tickets translated ────────────────────────────
    non_english_in_raw = {
        t["ticket_id"]
        for t in raw_tickets
        if not (t["language_hint"].lower() == "en" or
                (t["language_hint"].lower().startswith("en") and "-" not in t["language_hint"].lower()))
    }
    preprocessed_map = {p["ticket_id"]: p for p in preprocessed}
    translation_failures = []
    for tid in non_english_in_raw:
        p = preprocessed_map.get(tid)
        if p is None:
            translation_failures.append(f"{tid}: missing from preprocessed")
        elif not p.get("translated"):
            translation_failures.append(f"{tid}: translated=false")
        elif not p.get("message_for_processing", "").strip():
            translation_failures.append(f"{tid}: empty message_for_processing")
    ok = record(
        "Non-English tickets translated",
        len(translation_failures) == 0,
        str(translation_failures) if translation_failures else "",
    )
    all_ok = all_ok and ok

    # ── Check 5: Classified outputs use controlled vocabularies ───────────
    vocab_errors = []
    for c in classified:
        if c["intent"] not in INTENT_VALUES:
            vocab_errors.append(f"{c['ticket_id']}: invalid intent '{c['intent']}'")
        if c["urgency"] not in URGENCY_VALUES:
            vocab_errors.append(f"{c['ticket_id']}: invalid urgency '{c['urgency']}'")
        if c["sentiment"] not in SENTIMENT_VALUES:
            vocab_errors.append(f"{c['ticket_id']}: invalid sentiment '{c['sentiment']}'")
    ok = record(
        "Classified outputs use controlled vocabularies",
        len(vocab_errors) == 0,
        str(vocab_errors) if vocab_errors else "",
    )
    all_ok = all_ok and ok

    # ── Check 6: Retrieval references valid article IDs ───────────────────
    invalid_refs = []
    for r in retrieval:
        for art in r.get("retrieved_articles", []):
            if art["article_id"] not in kb_article_ids:
                invalid_refs.append(f"{r['ticket_id']}: unknown article {art['article_id']}")
    ok = record(
        "Retrieval references valid KB article IDs",
        len(invalid_refs) == 0,
        str(invalid_refs) if invalid_refs else "",
    )
    all_ok = all_ok and ok

    # ── Check 7: Each ticket has exactly 2 retrieved articles ─────────────
    wrong_count = [
        f"{r['ticket_id']}: {len(r.get('retrieved_articles', []))} articles"
        for r in retrieval
        if len(r.get("retrieved_articles", [])) != 2
    ]
    ok = record(
        "Each ticket has exactly 2 retrieved articles",
        len(wrong_count) == 0,
        str(wrong_count) if wrong_count else "",
    )
    all_ok = all_ok and ok

    # ── Check 8: Priority scores match deterministic re-computation ────────
    classified_map = {c["ticket_id"]: c for c in classified}
    raw_map = {t["ticket_id"]: t for t in raw_tickets}
    retrieval_map_val = {r["ticket_id"]: r for r in retrieval}
    score_errors = []
    for p in priority:
        tid = p["ticket_id"]
        c = classified_map.get(tid)
        t = raw_map.get(tid)
        r = retrieval_map_val.get(tid)
        if not (c and t and r):
            continue
        top_score = r["retrieved_articles"][0]["score"] if r["retrieved_articles"] else 0.0
        expected = (
            _URGENCY_BASE.get(c["urgency"], 3)
            + _TIER_BONUS.get(t["customer_tier"], 0)
            + (20 if c["mentions_funds_blocked"] else 0)
            + (25 if c["mentions_regulator_or_legal_threat"] else 0)
            + (10 if c["requires_specialist_handling"] else 0)
            + (8 if top_score < RETRIEVAL_WEAKNESS_THRESHOLD else 0)
        )
        if p["priority_score"] != expected:
            score_errors.append(
                f"{tid}: stored={p['priority_score']} expected={expected}"
            )
    ok = record(
        "Priority scores match deterministic formula",
        len(score_errors) == 0,
        str(score_errors) if score_errors else "",
    )
    all_ok = all_ok and ok

    # ── Check 9: Top-5 expedited tickets are highest-scored ───────────────
    sorted_priority = sorted(priority, key=lambda p: p["priority_score"], reverse=True)
    top5_expected = {p["ticket_id"] for p in sorted_priority[:TOP_N_EXPEDITED]}
    top5_stored = {p["ticket_id"] for p in priority if p.get("expedited")}
    expedited_mismatch = top5_expected.symmetric_difference(top5_stored)
    ok = record(
        "Top-5 expedited tickets are highest-scored",
        len(expedited_mismatch) == 0,
        f"Mismatch: {expedited_mismatch}" if expedited_mismatch else "",
    )
    all_ok = all_ok and ok

    # ── Check 10: Routing queues use controlled vocabulary ────────────────
    routing_errors = []
    for d in routing:
        for q in d.get("queues", []):
            if q not in QUEUE_VALUES:
                routing_errors.append(f"{d['ticket_id']}: invalid queue '{q}'")
        safety = d.get("reply_safety_label", "")
        if safety not in REPLY_SAFETY_LABELS:
            routing_errors.append(f"{d['ticket_id']}: invalid reply_safety_label '{safety}'")
    ok = record(
        "Routing queues and safety labels use controlled vocabularies",
        len(routing_errors) == 0,
        str(routing_errors) if routing_errors else "",
    )
    all_ok = all_ok and ok

    # ── Check 11: Reply drafts exist for all top-5 tickets ───────────────
    draft_ids = {d["ticket_id"] for d in reply_drafts}
    missing_drafts = top5_stored - draft_ids
    extra_drafts = draft_ids - top5_stored
    ok = record(
        "Reply drafts exist for all top-5 tickets",
        len(missing_drafts) == 0,
        f"Missing: {missing_drafts}" if missing_drafts else "",
    )
    all_ok = all_ok and ok
    if extra_drafts:
        record("No extra reply drafts outside top-5", False, f"Extra: {extra_drafts}")

    # ── Check 12: Reply draft citations reference valid KB articles ────────
    citation_errors = []
    for d in reply_drafts:
        for cit in d.get("citations", []):
            if cit not in kb_article_ids:
                citation_errors.append(f"{d['ticket_id']}: unknown citation {cit}")
    ok = record(
        "Reply draft citations reference valid KB articles",
        len(citation_errors) == 0,
        str(citation_errors) if citation_errors else "",
    )
    all_ok = all_ok and ok

    # ── Check 13: LLM call log has required stage records ─────────────────
    llm_log_path = Path("llm_calls.jsonl")
    required_stages = {"ticket_classification", "queue_routing", "reply_drafting"}
    found_stages = set()
    if llm_log_path.exists():
        for line in llm_log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    found_stages.add(rec.get("stage", ""))
                except json.JSONDecodeError:
                    pass
    missing_stages = required_stages - found_stages
    ok = record(
        "LLM call log has required stage records",
        len(missing_stages) == 0,
        f"Missing stages: {missing_stages}" if missing_stages else f"Found: {found_stages}",
    )
    all_ok = all_ok and ok

    # ── Write validation report ────────────────────────────────────────────
    lines = ["# Validation Report", ""]
    passed = sum(1 for _, p, _ in checks if p)
    failed = sum(1 for _, p, _ in checks if not p)
    lines.append(f"**Result:** {'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}")
    lines.append(f"**Passed:** {passed}  **Failed:** {failed}")
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("|---|---|---|")
    for name, passed_flag, detail in checks:
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        lines.append(f"| {name} | {status} | {detail} |")
    Path(REPORT_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nValidation report written -> {REPORT_FILE}")
    return all_ok


if __name__ == "__main__":
    ok = validate()
    sys.exit(0 if ok else 1)
