from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


SOURCE_TYPES = ("User Interview", "Survey", "User Feedback", "Support Ticket", "App Review", "Product Document", "Competitor Note", "Behavior/Event Data")


class ImportRequest(StrictModel):
    filename: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=1_000_000)
    type: str = "User Feedback"
    participant: str = Field(default="unattributed", max_length=200)
    segment: str = Field(default="unspecified", max_length=200)
    is_demo: bool = True
    consent_confirmed: bool = False
    redaction_terms: list[str] = Field(default_factory=list, max_length=30)
    privacy_review_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class RemoteReviewRequest(StrictModel):
    approved: bool
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    note: str = Field(min_length=10, max_length=2000)
    consent_confirmed: bool = False


class GenerateRequest(StrictModel):
    source_ids: list[str] = Field(min_length=1, max_length=100)
    query: str = Field(default="", max_length=2000)


class InsightReview(StrictModel):
    status: Literal["accepted", "rejected"]
    review_note: str = Field(min_length=3, max_length=3000)
    confidence: Literal["High", "Medium", "Low"] = "Low"


class OpportunityRequest(StrictModel):
    insight_ids: list[str] = Field(min_length=1, max_length=30)
    title: str = Field(min_length=3, max_length=200)
    problem: str = Field(min_length=3, max_length=3000)
    target_segment: str = "New players"
    frequency: str = "Not measured; qualitative hypothesis"
    severity: str = "Needs human assessment"
    business_impact: str = "Unknown; no product experiment"
    potential_solution: str = "Compare simpler UI and rules before AI"
    risks: list[str] = Field(default_factory=lambda: ["Small convenience sample; unsupported generalization"])
    reach: float = Field(default=1, ge=0, le=1_000_000)
    impact: float = Field(default=1, ge=0, le=10)
    confidence: float = Field(default=0.5, ge=0, le=1)
    effort: float = Field(default=1, gt=0, le=1000)
    moscow: Literal["Must", "Should", "Could", "Won't"] = "Could"


class DecisionRequest(StrictModel):
    decision: Literal["confirmed", "deferred", "rejected"]
    reason: str = Field(min_length=3, max_length=3000)


class FeasibilityRequest(StrictModel):
    opportunity_id: str
    task_type: Literal["ui", "rules", "lookup", "classification", "language", "multimodal"] = "ui"
    data_availability: Literal["none", "documents", "labeled", "multimodal"] = "documents"
    privacy: Literal["local_only", "approved_remote"] = "local_only"
    latency_budget_ms: int = Field(default=1000, ge=1, le=120000)
    tool_required: bool = False
    error_cost: Literal["low", "medium", "high"] = "medium"


class PromptRequest(StrictModel):
    goal: str = Field(min_length=3, max_length=1000)
    template: str = Field(min_length=10, max_length=15000)
    variables: list[str] = Field(default_factory=lambda: ["input", "context"])
    model: str = Field(default="deterministic-extractor", max_length=200)
    temperature: float = Field(default=0, ge=0, le=2)
    output_mode: Literal["text", "structured"] = "structured"


class RollbackRequest(StrictModel):
    version: int = Field(ge=1)


class Node(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    type: Literal["Input", "Prompt", "Retrieval", "LLM", "Condition", "Tool", "MCP", "Human Approval", "Structured Output"]
    label: str = Field(default="", max_length=200)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowRequest(StrictModel):
    name: str = Field(min_length=3, max_length=200)
    nodes: list[Node] = Field(min_length=1, max_length=20)
    prompt_id: str = "evidence-summary"
    prompt_version: int = Field(default=2, ge=1)
    description: str = Field(default="", max_length=2000)


class RunRequest(StrictModel):
    input: str = Field(min_length=1, max_length=10000)
    source_ids: list[str] | None = Field(default=None, max_length=100)
    prompt_version: int | None = Field(default=None, ge=1)
    workflow_version: int | None = Field(default=None, ge=1)


class ApprovalRequest(StrictModel):
    approved: bool
    note: str = Field(min_length=3, max_length=3000)


class EvaluationRequest(StrictModel):
    workflow_id: str = "evidence-workflow"
    prompt_versions: list[int] = Field(default_factory=lambda: [1, 2], min_length=1, max_length=5)


class HumanRatingRequest(StrictModel):
    case_id: str
    variant: str
    rating: int = Field(ge=1, le=5)
    note: str = Field(min_length=3, max_length=3000)


class ExperimentRequest(StrictModel):
    opportunity_id: str
    title: str = Field(min_length=3, max_length=200)
    hypothesis: str = Field(min_length=10, max_length=3000)
    primary_metric: str = Field(min_length=3, max_length=1000)
    decision_rule: str = Field(min_length=10, max_length=3000)
    secondary_metrics: list[str] = Field(default_factory=lambda: ["decision time", "understanding", "choice confidence"])
    guardrails: list[str] = Field(default_factory=lambda: ["incorrect advice", "lost user control", "latency"])
    variants: list[str] = Field(default_factory=lambda: ["Control", "Traditional solution", "AI solution only if justified"])
    sample_limitation: str = "PENDING REAL USER RESEARCH; qualitative pilot, no significance claim"
