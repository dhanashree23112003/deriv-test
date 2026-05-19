# Validation Report

**Result:** ALL CHECKS PASSED
**Passed:** 17  **Failed:** 0

| Check | Status | Detail |
|---|---|---|
| Required artifacts exist | ✅ PASS |  |
| All JSON files are valid | ✅ PASS |  |
| All tickets in preprocessed_tickets.json | ✅ PASS |  |
| All tickets in classified_tickets.json | ✅ PASS |  |
| All tickets in retrieval_results.json | ✅ PASS |  |
| All tickets in priority_scores.json | ✅ PASS |  |
| All tickets in routing_decisions.json | ✅ PASS |  |
| Non-English tickets translated | ✅ PASS |  |
| Classified outputs use controlled vocabularies | ✅ PASS |  |
| Retrieval references valid KB article IDs | ✅ PASS |  |
| Each ticket has exactly 2 retrieved articles | ✅ PASS |  |
| Priority scores match deterministic formula | ✅ PASS |  |
| Top-5 expedited tickets are highest-scored | ✅ PASS |  |
| Routing queues and safety labels use controlled vocabularies | ✅ PASS |  |
| Reply drafts exist for all top-5 tickets | ✅ PASS |  |
| Reply draft citations reference valid KB articles | ✅ PASS |  |
| LLM call log has required stage records | ✅ PASS | Found: {'reply_drafting', 'handoff_memory', 'ticket_classification', 'preprocessing_translation', 'queue_routing'} |
