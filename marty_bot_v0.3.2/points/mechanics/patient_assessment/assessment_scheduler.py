from typing import Literal

from pydantic import BaseModel, Field


FactSource = Literal[
    "dispatch",
    "patient",
    "proctor",
    "monitor",
    "physical_exam",
    "partner",
]

ResponseRole = Literal[
    "patient",
    "proctor",
    "monitor",
    "dispatch",
    "mixed",
]

AssessmentPhase = Literal[
    "scene_size_up",
    "general_impression",
    "primary_assessment",
    "history",
    "focused_assessment",
    "vitals_diagnostics",
    "treatment",
    "reassessment",
    "transport_handoff",
]

PriorityDecision = Literal[
    "high",
    "low",
    "none",
]


class ScenarioFact(BaseModel):
    key: str
    value: str
    source: FactSource


class TreatmentEffect(BaseModel):
    treatment_key: str
    response_text: str
    updates: list[ScenarioFact] = Field(
        default_factory=list
    )


class GeneratedAssessmentScenario(BaseModel):
    scenario_type: str
    title: str
    dispatch_text: str
    opening_scene: str

    patient_age: int
    sex_assigned_at_birth: str
    chief_complaint: str
    field_impression: str

    expected_priority: Literal[
        "high",
        "low",
    ]

    # These control conditional items on the base
    # medical rubric.
    airway_obstruction_present: bool = False
    shock_present: bool = False
    pregnancy_questions_applicable: bool = False

    # Only used by trauma scenarios.
    trauma_regions: list[str] = Field(
        default_factory=list
    )

    # Conditional rubric items that are genuinely
    # applicable to this exact scenario.
    applicable_conditional_keys: list[str] = Field(
        default_factory=list
    )

    # Critical management actions that must be completed
    # in addition to the generic critical-fail checks.
    critical_required_actions: list[str] = Field(
        default_factory=list
    )

    # When true, failure to appropriately address oxygen /
    # ventilation is checked as a critical fail.
    requires_oxygen: bool = False

    # Complete hidden scenario truth. The turn LLM must
    # never invent facts outside this list.
    facts: list[ScenarioFact]

    # Deterministic patient-state changes when treatments
    # are performed.
    treatment_effects: list[TreatmentEffect] = Field(
        default_factory=list
    )


class AssessmentTurnResult(BaseModel):
    response_role: ResponseRole
    response_text: str

    # Rubric keys the student's statement actually
    # satisfies on this turn.
    rubric_keys: list[str] = Field(
        default_factory=list
    )

    # Treatment rubric keys that were actually performed.
    # Python uses these to apply deterministic patient-state
    # updates from the frozen scenario.
    treatment_keys: list[str] = Field(
        default_factory=list
    )

    phase: AssessmentPhase

    transport_called: bool = False
    handoff_report_given: bool = False
    priority_decision: PriorityDecision = "none"

    field_impression_text: str | None = None

    dangerous_action: bool = False
    dangerous_action_confidence: float = 0.0
    dangerous_reason: str = ""

    unacceptable_affect: bool = False
    unacceptable_affect_confidence: float = 0.0
    unacceptable_affect_reason: str = ""
