# Detect OS for venv activation path
ifeq ($(OS),Windows_NT)
    PYTHON = .venv/Scripts/python
    PIP    = .venv/Scripts/pip
else
    PYTHON = .venv/bin/python
    PIP    = .venv/bin/pip
endif

.PHONY: install run validate clean

install:
	python -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) run.py

validate:
	$(PYTHON) validate.py

clean:
	rm -f preprocessed_tickets.json \
	      classified_tickets.json \
	      retrieval_results.json \
	      priority_scores.json \
	      routing_decisions.json \
	      reply_drafts.json \
	      retrieval_quality.json \
	      ops_summary.md \
	      handoff_memory.json \
	      validation_report.md \
	      llm_calls.jsonl
