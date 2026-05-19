from typing import List, Optional
from pydantic import BaseModel


class RawTicket(BaseModel):
    ticket_id: str
    channel: str
    customer_tier: str
    language_hint: str
    subject: str
    message: str
    created_at: str


class KBArticle(BaseModel):
    article_id: str
    title: str
    category: str
    body: str
    tags: List[str]


class PreprocessedTicket(BaseModel):
    ticket_id: str
    original_subject: str
    original_message: str
    subject_for_processing: str
    message_for_processing: str
    original_language: str
    translated: bool


class ClassifiedTicket(BaseModel):
    ticket_id: str
    intent: str
    urgency: str
    sentiment: str
    mentions_funds_blocked: bool
    mentions_regulator_or_legal_threat: bool
    requires_specialist_handling: bool
    original_language: str
    translated: bool


class RetrievedArticle(BaseModel):
    article_id: str
    title: str
    score: float


class TicketRetrieval(BaseModel):
    ticket_id: str
    retrieved_articles: List[RetrievedArticle]


class PriorityScore(BaseModel):
    ticket_id: str
    priority_score: int
    urgency: str
    customer_tier: str
    mentions_funds_blocked: bool
    mentions_regulator_or_legal_threat: bool
    requires_specialist_handling: bool
    retrieval_weakness: bool
    expedited: bool


class RoutingDecision(BaseModel):
    ticket_id: str
    queues: List[str]
    routing_rationale: str
    reply_safety_label: str


class ReplyDraft(BaseModel):
    ticket_id: str
    channel: str
    draft_reply: str
    citations: List[str]
    review_gate_note: str


class RetrievalQualityNote(BaseModel):
    ticket_id: str
    issue: str
    recommended_improvement: str


class HandoffMemory(BaseModel):
    ticket_id: str
    customer_problem_summary: str
    open_questions: List[str]
    do_not_say: List[str]
    recommended_next_action: str


class LLMCallLog(BaseModel):
    stage: str
    timestamp: str
    provider: str
    model: str
    prompt_hash: str
    input_artifacts: List[str]
    output_artifact: str
