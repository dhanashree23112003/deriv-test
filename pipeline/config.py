import os
from enum import Enum


class PipelineStage(str, Enum):
    INIT = "INIT"
    TICKETS_LOADED = "TICKETS_LOADED"
    PREPROCESSING_COMPLETE = "PREPROCESSING_COMPLETE"
    TICKETS_CLASSIFIED = "TICKETS_CLASSIFIED"
    KB_RETRIEVAL_COMPLETE = "KB_RETRIEVAL_COMPLETE"
    PRIORITY_SCORES_COMPUTED = "PRIORITY_SCORES_COMPUTED"
    ROUTING_COMPLETE = "ROUTING_COMPLETE"
    REPLY_DRAFTS_GENERATED = "REPLY_DRAFTS_GENERATED"
    VALIDATION_COMPLETE = "VALIDATION_COMPLETE"
    RESULTS_FINALISED = "RESULTS_FINALISED"


INTENT_VALUES = {
    "withdrawal_issue",
    "deposit_issue",
    "login_access",
    "verification_kyc",
    "account_restriction",
    "product_behavior",
    "privacy_request",
    "statement_export",
    "api_support",
    "other",
}

URGENCY_VALUES = {"critical", "high", "medium", "low"}

SENTIMENT_VALUES = {"calm", "frustrated", "angry", "neutral"}

QUEUE_VALUES = {
    "General Support",
    "Payments",
    "Compliance",
    "Risk",
    "Engineering",
    "Product",
    "Privacy",
    "Developer Support",
}

REPLY_SAFETY_LABELS = {
    "safe_to_send_after_review",
    "needs_specialist_review",
    "needs_legal_or_compliance_review",
}

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

RETRIEVAL_WEAKNESS_THRESHOLD = 0.55
TOP_N_EXPEDITED = 5
