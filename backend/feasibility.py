from .db import now, uid
from .models import FeasibilityRequest


OPTIONS = [
    ("No AI", "Clearer labels, fewer choices, contextual UI", "Design and usability evidence", "Manual UI / previous design", "High: visible product behavior"),
    ("Rules", "Finite known constraints", "Maintained rule catalog", "Show rule or no recommendation", "High: rule trace"),
    ("Search", "Find existing information", "Indexed source documents", "Browse originals", "High: exact source"),
    ("Traditional ML", "Repeated classification", "Labeled representative examples", "Manual classification", "Depends on model and feature design"),
    ("LLM", "Bounded language transformation", "Task examples and output rubric", "Extractive draft / human writing", "Low without grounded context"),
    ("RAG", "Evidence-dependent language work", "Current retrievable documents", "Search originals / abstain", "Citations help; semantic claim review required"),
    ("Agent", "Iterative decisions requiring tools", "Tools, permissions and budgets", "Bounded workflow / manual steps", "Tool trace; reasoning alone is not proof"),
    ("Multimodal", "Task requires image or audio meaning", "Consented image/audio and evaluation labels", "Text-only / human review", "Requires inspection of source media"),
]


def assess(request: FeasibilityRequest, opportunity: dict) -> dict:
    selected = "No AI"
    reason = "The task can be addressed with product design before adding inference."
    if request.task_type == "rules":
        selected, reason = "Rules", "Known finite constraints favor explicit, testable rules."
    elif request.task_type == "lookup" and request.data_availability != "none":
        selected, reason = "Search", "The user needs existing evidence; generative interpretation is not required."
    elif request.task_type == "classification" and request.data_availability == "labeled":
        selected, reason = "Traditional ML", "A labeled recurring classification task should establish a small supervised baseline."
    elif request.task_type == "language" and request.data_availability == "documents":
        selected, reason = "RAG", "Evidence-dependent language work may benefit from retrieval, subject to comparison with search and rules."
    elif request.task_type == "language" and request.data_availability != "none":
        selected, reason = "LLM", "Bounded language transformation is a candidate; accuracy and costs remain unmeasured."
    elif request.task_type == "multimodal" and request.data_availability == "multimodal":
        selected, reason = "Multimodal", "The input requires perception; consent and a human-reviewed dataset are prerequisites."
    if request.tool_required and selected in ("LLM", "RAG"):
        selected, reason = "Agent", "A tool need was declared. Compare a bounded workflow before authorizing agentic tool selection."
    if request.data_availability == "none":
        selected, reason = "No AI", "Collect task evidence first. No data is not a reason to invent a model solution."
    if request.privacy == "local_only" and selected in ("LLM", "RAG", "Agent", "Multimodal"):
        selected, reason = "Search", "Remote evidence processing is not approved. Use local search/manual review until a private architecture is validated."
    if request.latency_budget_ms < 100 and selected in ("LLM", "RAG", "Agent", "Multimodal"):
        selected, reason = "Rules", "A strict sub-100 ms budget favors precomputed/rule outputs; live model latency is unmeasured."
    options = []
    for name, scope, data, fallback, explainability in OPTIONS:
        options.append({"architecture": name, "appropriate_for": scope, "expected_accuracy": "Unmeasured; needs task-specific evaluation",
                        "latency": "Measure against " + str(request.latency_budget_ms) + " ms budget", "cost": "Unknown until benchmark; no invented estimate",
                        "data_availability": data, "context_requirement": "Source/task context required" if name not in ("No AI", "Rules") else "Explicit product rules",
                        "personalization": "Not required by the current hypothesis", "tool_requirement": name == "Agent",
                        "risk": "Incorrect output requires review" if name not in ("No AI", "Rules", "Search") else "Coverage and maintenance",
                        "explainability": explainability, "privacy": request.privacy, "human_review": "Required for decisions", "fallback": fallback,
                        "recommended": name == selected})
    return {"id": uid("fea"), "opportunity_id": opportunity["id"], "created_at": now(), "inputs": request.model_dump(),
            "recommended_architecture": selected, "reasons": [reason, "Heuristic recommendation; human owner must confirm the architecture."],
            "known_failure_modes": ["Weak or unrepresentative evidence", "Citation presence mistaken for semantic support", "Unmeasured cost and latency"],
            "non_ai_alternative": "Improve labels, show a concise contextual rule explanation, or let the user inspect sources.",
            "mvp_scope": "One read-only task; no automatic decisions or external side effects", "options": options,
            "is_demo": opportunity["is_demo"], "human_decision": None, "recommendation_basis": "Deterministic planning heuristic; not model prediction"}
