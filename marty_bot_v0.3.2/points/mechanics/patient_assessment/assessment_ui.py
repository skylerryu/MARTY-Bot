import random

from data.patient_assessment_db import (
    create_assessment_scenario,
    get_recent_scenario_types,
    record_assessment_llm_usage,
)
from points.mechanics.patient_assessment.assessment_config import (
    ASSESSMENT_ENABLED_SCENARIO_TYPES,
    ASSESSMENT_RECENT_TYPE_AVOID_COUNT,
    ASSESSMENT_SCENARIO_MODEL,
)
from points.mechanics.patient_assessment.assessment_rubrics import (
    RUBRIC_ITEM_BY_KEY,
    TRAUMA_REGION_RUBRICS,
    get_conditional_rubric_prompt_text,
    get_scenario_type_catalog,
    get_scenario_type_catalog_text,
)
from services.assessment_llm import (
    generate_daily_assessment_scenario,
)


# ==================================================
# TYPE SELECTION
# ==================================================


async def choose_daily_scenario_type(
    guild_id: int,
) -> str:
    enabled = list(
        ASSESSMENT_ENABLED_SCENARIO_TYPES
    )

    if not enabled:
        raise RuntimeError(
            "No patient-assessment scenario types are enabled."
        )

    recent = await get_recent_scenario_types(
        guild_id=guild_id,
        limit=ASSESSMENT_RECENT_TYPE_AVOID_COUNT,
    )

    recent_set = set(recent)

    candidates = [
        scenario_type
        for scenario_type in enabled
        if scenario_type not in recent_set
    ]

    if not candidates:
        candidates = enabled

    return random.choice(candidates)


# ==================================================
# VALIDATE GENERATED SCENARIO
# ==================================================


def _normalize_generated_scenario(
    expected_type: str,
    generated: dict,
) -> dict:
    generated["scenario_type"] = expected_type

    # Remove duplicate fact keys while preserving the
    # first occurrence. Duplicate facts would make the
    # patient state ambiguous.
    seen_fact_keys = set()
    cleaned_facts = []

    for fact in generated.get("facts", []):
        key = str(fact.get("key", "")).strip()

        if not key or key in seen_fact_keys:
            continue

        seen_fact_keys.add(key)
        cleaned_facts.append(
            {
                "key": key,
                "value": str(
                    fact.get("value", "")
                ).strip(),
                "source": fact.get(
                    "source",
                    "proctor",
                ),
            }
        )

    generated["facts"] = cleaned_facts

    if expected_type == "trauma":
        valid_regions = set(
            TRAUMA_REGION_RUBRICS.keys()
        )

        regions = []

        for region in generated.get(
            "trauma_regions",
            [],
        ):
            if (
                region in valid_regions
                and region not in regions
            ):
                regions.append(region)

        if not regions:
            regions = ["chest"]

        generated["trauma_regions"] = (
            regions[:3]
        )
    else:
        generated["trauma_regions"] = []

    catalog = get_scenario_type_catalog(
        expected_type
    )

    allowed_keys = {
        item.key
        for item in catalog
    }

    conditional_keys = {
        item.key
        for item in catalog
        if item.conditional
    }

    cleaned_conditionals = []

    for key in generated.get(
        "applicable_conditional_keys",
        [],
    ):
        if (
            key in conditional_keys
            and key not in cleaned_conditionals
        ):
            cleaned_conditionals.append(key)

    # Keep the model's conditional list internally consistent
    # with the explicit scenario booleans.
    if not generated.get("airway_obstruction_present", False):
        cleaned_conditionals = [
            key
            for key in cleaned_conditionals
            if key != "medical_airway_management"
        ]

    if not generated.get("shock_present", False):
        cleaned_conditionals = [
            key
            for key in cleaned_conditionals
            if key != "medical_shock_treatment"
        ]

    if not generated.get("pregnancy_questions_applicable", False):
        cleaned_conditionals = [
            key
            for key in cleaned_conditionals
            if key not in {"abd_vaginal", "abd_pregnancy"}
        ]

    generated[
        "applicable_conditional_keys"
    ] = cleaned_conditionals

    cleaned_critical = []

    for key in generated.get(
        "critical_required_actions",
        [],
    ):
        if (
            key in allowed_keys
            and key not in cleaned_critical
        ):
            cleaned_critical.append(key)

    generated[
        "critical_required_actions"
    ] = cleaned_critical

    # Treatment effects may only reference known rubric
    # keys. Unknown model-generated keys are discarded.
    cleaned_effects = []

    for effect in generated.get(
        "treatment_effects",
        [],
    ):
        key = effect.get("treatment_key")

        if key not in allowed_keys:
            continue

        cleaned_effects.append(effect)

    generated["treatment_effects"] = (
        cleaned_effects
    )

    return generated


# ==================================================
# GENERATE + SAVE
# ==================================================


async def generate_and_save_daily_scenario(
    guild_id: int,
    channel_id: int,
    scenario_date: str,
    expires_at: str,
    scenario_type: str | None = None,
) -> dict:
    if scenario_type is None:
        scenario_type = (
            await choose_daily_scenario_type(
                guild_id
            )
        )

    rubric_text = (
        get_scenario_type_catalog_text(
            scenario_type
        )
    )

    conditional_text = (
        get_conditional_rubric_prompt_text(
            scenario_type
        )
    )

    generated, usage = (
        await generate_daily_assessment_scenario(
            scenario_type=scenario_type,
            rubric_text=rubric_text,
            conditional_rubric_text=(
                conditional_text
            ),
        )
    )

    scenario_data = (
        generated.model_dump()
    )

    scenario_data = (
        _normalize_generated_scenario(
            expected_type=scenario_type,
            generated=scenario_data,
        )
    )

    scenario = await create_assessment_scenario(
        guild_id=guild_id,
        channel_id=channel_id,
        scenario_date=scenario_date,
        expires_at=expires_at,
        scenario=scenario_data,
    )

    await record_assessment_llm_usage(
        scenario_id=scenario["id"],
        purpose="scenario_generation",
        model=ASSESSMENT_SCENARIO_MODEL,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        total_tokens=usage["total_tokens"],
    )

    return scenario
