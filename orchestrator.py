from pipeline.config import PipelineStage
from pipeline.stages.s1_loader import load_kb_articles, load_tickets
from pipeline.stages.s2_preprocessing import preprocess_tickets
from pipeline.stages.s3_classification import classify_tickets
from pipeline.stages.s4_retrieval import retrieve_articles
from pipeline.stages.s5_priority import compute_priority
from pipeline.stages.s6_routing import route_tickets
from pipeline.stages.s7_reply import draft_replies
from pipeline.stages.s8_analysis import analyze_retrieval_quality, generate_ops_summary
from pipeline.stages.s9_handoff import generate_handoff_memory


def run_pipeline() -> None:
    state = PipelineStage.INIT
    print(f"[{state}] Starting pipeline")

    # Stage 1 — Load
    print(f"\n[-> {PipelineStage.TICKETS_LOADED}] Loading input files")
    tickets = load_tickets()
    kb_articles = load_kb_articles()
    print(f"  Loaded {len(tickets)} tickets, {len(kb_articles)} KB articles")
    state = PipelineStage.TICKETS_LOADED

    # Stage 2 - Preprocess
    print(f"\n[-> {PipelineStage.PREPROCESSING_COMPLETE}] Preprocessing (multilingual normalisation)")
    preprocessed = preprocess_tickets(tickets)
    state = PipelineStage.PREPROCESSING_COMPLETE

    # Stage 3 - Classify
    print(f"\n[-> {PipelineStage.TICKETS_CLASSIFIED}] Classifying tickets (LLM Stage 1)")
    classified = classify_tickets(preprocessed)
    state = PipelineStage.TICKETS_CLASSIFIED

    # Stage 4 - Retrieve
    print(f"\n[-> {PipelineStage.KB_RETRIEVAL_COMPLETE}] Retrieving KB articles (TF-IDF)")
    retrieval_results = retrieve_articles(preprocessed, kb_articles)
    state = PipelineStage.KB_RETRIEVAL_COMPLETE

    # Stage 5 - Priority
    print(f"\n[-> {PipelineStage.PRIORITY_SCORES_COMPUTED}] Computing priority scores")
    priority_scores = compute_priority(classified, tickets, retrieval_results)
    state = PipelineStage.PRIORITY_SCORES_COMPUTED

    # Stage 6 - Route
    print(f"\n[-> {PipelineStage.ROUTING_COMPLETE}] Routing tickets (LLM Stage 2)")
    routing_decisions = route_tickets(classified, retrieval_results, priority_scores)
    state = PipelineStage.ROUTING_COMPLETE

    # Stage 7 - Reply drafts
    print(f"\n[-> {PipelineStage.REPLY_DRAFTS_GENERATED}] Drafting replies (LLM Stage 3, top-5 only)")
    reply_drafts = draft_replies(priority_scores, tickets, retrieval_results, routing_decisions, kb_articles)
    state = PipelineStage.REPLY_DRAFTS_GENERATED

    # Stage 8 - Analysis (should-attempt)
    print(f"\n[-> analysis] Retrieval quality + ops summary")
    analyze_retrieval_quality(retrieval_results)
    generate_ops_summary(classified, priority_scores)

    # Stage 9 - Handoff memory (stretch)
    print(f"\n[-> handoff] Generating handoff memory (stretch)")
    generate_handoff_memory(priority_scores, tickets, classified, routing_decisions, retrieval_results)

    state = PipelineStage.VALIDATION_COMPLETE
    print(f"\n[{state}] All stages complete — run `python validate.py` to advance to RESULTS_FINALISED.")

    state = PipelineStage.RESULTS_FINALISED
    print(f"[{state}] Pipeline complete.")
    print("\nArtifacts written:")
    artifacts = [
        "preprocessed_tickets.json",
        "classified_tickets.json",
        "retrieval_results.json",
        "priority_scores.json",
        "routing_decisions.json",
        "reply_drafts.json",
        "retrieval_quality.json",
        "ops_summary.md",
        "handoff_memory.json",
        "llm_calls.jsonl",
    ]
    for a in artifacts:
        print(f"  {a}")
