from dataclasses import dataclass


# ==================================================
# RUBRIC ITEM
# ==================================================


@dataclass(frozen=True)
class RubricItem:
    key: str
    section: str
    label: str
    points: int = 1
    conditional: bool = False
    hidden: bool = False


def _items(
    section: str,
    rows: list[tuple],
) -> list[RubricItem]:
    result = []

    for row in rows:
        key = row[0]
        label = row[1]
        points = row[2] if len(row) >= 3 else 1
        conditional = row[3] if len(row) >= 4 else False
        hidden = row[4] if len(row) >= 5 else False

        result.append(
            RubricItem(
                key=key,
                section=section,
                label=label,
                points=points,
                conditional=conditional,
                hidden=hidden,
            )
        )

    return result


# ==================================================
# GENERAL MEDICAL
# ==================================================
#
# This follows the uploaded General Medical sheet.
# Two explicitly conditional lines are represented as
# conditional items:
#
#   - airway clearing/management when obstruction exists
#   - shock treatment when shock exists
#
# When neither condition is present, the applicable base
# rubric totals the sheet's printed 58 points.
# ==================================================


GENERAL_MEDICAL = (
    _items(
        "Scene Size-Up",
        [
            ("medical_bsi", "Takes/verbalizes appropriate BSI precautions"),
            ("medical_scene_safe", "Determines scene/situation is safe"),
            ("medical_noi", "Determines nature of illness / mechanism"),
            ("medical_patient_count", "Determines number of patients"),
            ("medical_resources", "Requests/considers additional resources"),
        ],
    )
    + _items(
        "General Impression",
        [
            ("medical_patient_description", "Identifies patient age and sex assigned at birth"),
            ("medical_chief_complaint", "Determines chief/observed complaint and apparent life threats"),
            ("medical_responsiveness", "Determines AVPU/orientation/LOC"),
            ("medical_spine", "Considers spinal stabilization/self-restriction"),
            ("medical_sick_not_sick", "Determines sick vs not sick appearance"),
        ],
    )
    + _items(
        "Primary Assessment - Exsanguination/Airway",
        [
            ("medical_major_bleeding", "Assesses/controls major bleeding"),
            ("medical_airway_obstruction", "Identifies whether airway obstruction is present"),
            (
                "medical_airway_management",
                "Correctly opens/clears airway when obstruction is present",
                1,
                True,
            ),
        ],
    )
    + _items(
        "Primary Assessment - Breathing",
        [
            ("medical_tidal_volume", "Assesses adequate tidal volume/chest rise"),
            ("medical_resp_rate_relative", "Assesses relative respiratory rate"),
            ("medical_resp_pattern", "Assesses respiratory pattern"),
            ("medical_accessory_muscles", "Assesses accessory muscle use"),
            ("medical_retractions", "Assesses retractions"),
            ("medical_tracheal_tugging", "Assesses tracheal tugging"),
            ("medical_spo2", "Assesses SpO2"),
            ("medical_lung_sounds", "Assesses lung sounds"),
            ("medical_work_of_breathing", "Determines respiratory distress/failure/arrest"),
            ("medical_oxygen", "Initiates appropriate oxygen/ventilatory management"),
        ],
    )
    + _items(
        "Primary Assessment - Circulation",
        [
            ("medical_skin_color", "Assesses skin color"),
            ("medical_skin_temperature", "Assesses skin temperature"),
            ("medical_skin_moisture", "Assesses skin moisture"),
            ("medical_pulse_strength", "Assesses pulse strength"),
            ("medical_pulse_rate_relative", "Assesses relative pulse rate"),
            ("medical_pulse_regularity", "Assesses pulse regularity"),
            ("medical_pulse_equality", "Assesses pulse equality"),
            ("medical_cap_refill", "Assesses capillary refill"),
            ("medical_shock", "Identifies whether patient is in shock"),
            (
                "medical_shock_treatment",
                "Initiates shock treatment when shock is present",
                1,
                True,
            ),
        ],
    )
    + _items(
        "Primary Assessment - Environment/Priority",
        [
            ("medical_environment", "Assesses probable hypothermia/hyperthermia"),
            ("medical_priority", "Identifies priority and treatment/transport decision"),
        ],
    )
    + _items(
        "History - OPQRST",
        [
            ("medical_opqrst_onset", "Obtains onset"),
            ("medical_opqrst_provocation", "Obtains provocation/palliation/position"),
            ("medical_opqrst_quality", "Obtains quality"),
            ("medical_opqrst_region", "Obtains region/radiation"),
            ("medical_opqrst_severity", "Obtains severity"),
            ("medical_opqrst_time", "Obtains time"),
        ],
    )
    + _items(
        "History - Associated Symptoms",
        [
            ("medical_associated_symptoms", "Obtains complaint-relevant associated symptoms"),
        ],
    )
    + _items(
        "History - SAMPLE",
        [
            ("medical_allergies", "Obtains allergies"),
            ("medical_medications", "Obtains medications"),
            ("medical_pmh", "Obtains pertinent medical history"),
            ("medical_last_intake", "Obtains last oral intake"),
            ("medical_events", "Obtains events leading to illness"),
        ],
    )
    + _items(
        "Vital Signs / Diagnostics",
        [
            ("medical_bp", "Assesses blood pressure"),
            ("medical_pulse_vital", "Obtains pulse rate and quality"),
            ("medical_resp_vital", "Obtains ventilatory rate and quality"),
            ("medical_pupils", "Assesses pupils"),
            ("medical_bgl", "Assesses blood glucose"),
            ("medical_secondary_spo2", "Obtains secondary SpO2"),
            ("medical_field_impression", "States field impression"),
        ],
    )
    + _items(
        "Reassessment / Handoff",
        [
            ("medical_reassess_timing", "Demonstrates when to reassess"),
            ("medical_repeat_primary", "Repeats primary assessment"),
            ("medical_repeat_vitals", "Repeats relevant vital signs"),
            ("medical_check_interventions", "Checks interventions"),
            ("medical_reassess_complaint", "Reassesses complaint/overall condition"),
            ("medical_report", "Provides accurate verbal transfer report"),
        ],
    )
)


# ==================================================
# RESPIRATORY - 17 POINTS
# ==================================================


RESPIRATORY = (
    _items(
        "Respiratory - History",
        [
            ("resp_associated_symptoms", "Asks about chest pain, weakness, fever, edema, or cough"),
            ("resp_infection", "Asks about respiratory infection/symptoms"),
            ("resp_cough_productive", "Asks about cough/productivity/sputum"),
            ("resp_position_night", "Asks about upright comfort and nocturnal worsening"),
        ],
    )
    + _items(
        "Respiratory - Focused Assessment",
        [
            ("resp_accessory_muscles", "Looks for accessory muscle use"),
            ("resp_tracheal_tugging", "Looks for tracheal tugging"),
            ("resp_jvd", "Looks for JVD"),
            ("resp_abnormal_position", "Looks for tripod/sniffing positioning"),
            ("resp_peripheral_edema", "Looks for peripheral edema"),
            ("resp_pursed_lips", "Looks for pursed-lip breathing"),
            ("resp_drooling", "Looks for drooling"),
            ("resp_secondary_skin", "Looks for secondary skin conditions"),
            ("resp_breath_sounds", "Listens to breath sounds"),
            ("resp_tracheal_deviation", "Assesses tracheal deviation"),
        ],
    )
    + _items(
        "Respiratory - Treatment",
        [
            ("resp_oxygen", "Places patient on proper oxygen therapy"),
            (
                "resp_albuterol_atrovent",
                "Administers 2.5 mg albuterol + 0.5 mg Atrovent when wheezing is present",
                1,
                True,
            ),
            ("resp_treatment_response", "Assesses response to treatment"),
        ],
    )
)


# ==================================================
# CARDIAC - 15 POINTS
# ==================================================


CARDIAC = (
    _items(
        "Cardiac - History",
        [
            ("cardiac_associated_symptoms", "Asks about SOB, weakness, dizziness, palpitations"),
            ("cardiac_infection", "Asks about respiratory infection/symptoms"),
            ("cardiac_cough_productive", "Asks about cough/productivity/sputum"),
            ("cardiac_ed_drugs", "Asks about erectile dysfunction drugs"),
            ("cardiac_movement_pleuritic", "Asks whether pain changes with movement/deep breath"),
        ],
    )
    + _items(
        "Cardiac - Focused Assessment",
        [
            ("cardiac_jvd", "Looks for JVD"),
            ("cardiac_peripheral_edema", "Looks for peripheral edema"),
            ("cardiac_pursed_lips", "Looks for pursed-lip breathing"),
            ("cardiac_pink_frothy", "Looks for pink frothy sputum"),
            ("cardiac_secondary_skin", "Looks for secondary skin conditions"),
            ("cardiac_breath_sounds", "Listens to breath sounds"),
        ],
    )
    + _items(
        "Cardiac - Treatment",
        [
            ("cardiac_oxygen", "Places patient on proper oxygen therapy"),
            ("cardiac_asa", "Administers 324 mg ASA when appropriate", 1, True),
            ("cardiac_ntg", "Assists with 0.4 mg SL NTG when relevant", 1, True),
            ("cardiac_treatment_response", "Assesses response to treatment"),
        ],
    )
)


# ==================================================
# NEUROLOGICAL - DECLARED 32 POINTS
# ==================================================
#
# The source sheet declares 6 points for the focused
# "Feel" subsection while five one-point actions are
# visibly enumerated. The hidden reconciliation item is
# automatically awarded when all five visible actions are
# completed. It preserves the declared total without
# inventing an extra student action.
# ==================================================


NEUROLOGICAL = (
    _items(
        "Neurological - Associated Symptoms",
        [
            ("neuro_headache", "Asks about headache"),
            ("neuro_blurred_vision", "Asks about blurred vision"),
            ("neuro_confusion", "Asks about cloudiness/confusion"),
            ("neuro_deficits", "Asks about other noticeable deficits"),
            ("neuro_head_injury", "Asks/assesses obvious head injury"),
            ("neuro_temperature_symptoms", "Asks/assesses hypothermia or hyperthermia"),
        ],
    )
    + _items(
        "Neurological - History",
        [
            ("neuro_psych", "Asks about hallucinations and self/other harm"),
            ("neuro_baseline_lkn", "Determines baseline/what changed/last known normal"),
            ("neuro_drugs_alcohol", "Asks about recent drugs/alcohol"),
            ("neuro_diabetes", "Asks about diabetes and recent blood sugars"),
            ("neuro_infection", "Asks about fever, wounds, indwelling catheters"),
        ],
    )
    + _items(
        "Neurological - Focused Look",
        [
            ("neuro_pearl", "Assesses pupils for PEARL"),
            ("neuro_paraphernalia", "Looks for drug/alcohol paraphernalia/signs"),
            ("neuro_active_seizure", "Assesses active seizure"),
            ("neuro_incontinence", "Assesses incontinence"),
            ("neuro_tongue_bite", "Assesses tongue biting"),
            ("neuro_obvious_head_injury", "Looks for obvious head injury"),
            ("neuro_abdominal_discoloration", "Looks for abdominal discoloration"),
        ],
    )
    + _items(
        "Neurological - Focused Feel",
        [
            ("neuro_head_palpation", "Palpates head for injury"),
            ("neuro_pms", "Assesses pulse/motor/sensory"),
            ("neuro_cincinnati", "Conducts Cincinnati stroke scale"),
            ("neuro_van", "Conducts VAN when indicated after failed FAST", 1, True),
            ("neuro_environment_skin", "Assesses skin findings suggesting environmental emergency"),
            (
                "neuro_feel_reconciliation",
                "Focused Feel subsection completion reconciliation",
                1,
                False,
                True,
            ),
        ],
    )
    + _items(
        "Neurological - Smell",
        [
            ("neuro_fruity_odor", "Assesses fruity/acetone breath odor"),
            ("neuro_alcohol_odor", "Assesses alcohol odor"),
        ],
    )
    + _items(
        "Neurological - Treatment",
        [
            ("neuro_oxygen", "Places patient on proper oxygen therapy"),
            ("neuro_oral_glucose", "Administers 15 g oral glucose for hypoglycemia", 1, True),
            ("neuro_glucagon", "Administers 1 mg glucagon IN/IM when oral glucose contraindicated", 1, True),
            ("neuro_narcan", "Administers 2 mg naloxone IN/IM for opiate overdose", 1, True),
            ("neuro_environment_treatment", "Removes/treats patient for environmental exposure", 1, True),
            ("neuro_treatment_response", "Assesses response to treatment"),
        ],
    )
)


# ==================================================
# ANAPHYLAXIS - 19 POINTS
# ==================================================


ANAPHYLAXIS = (
    _items(
        "Anaphylaxis - History",
        [
            ("ana_associated_symptoms", "Asks about weakness, SOB, itchiness, chest pain"),
            ("ana_known_allergen", "Asks about known allergen exposure"),
            ("ana_prior_treatment", "Asks about EpiPen/inhaler/Benadryl and timing"),
            ("ana_new_medications", "Asks about new medications"),
            ("ana_new_foods", "Asks about new foods"),
            ("ana_new_skin_products", "Asks about new skincare products"),
            ("ana_new_cleaning_products", "Asks about new cleaning products"),
        ],
    )
    + _items(
        "Anaphylaxis - Focused Assessment",
        [
            ("ana_accessory_muscles", "Looks for accessory muscle use"),
            ("ana_abnormal_position", "Looks for tripod/sniffing positioning"),
            ("ana_peripheral_edema", "Looks for peripheral edema"),
            ("ana_facial_swelling", "Looks for facial swelling"),
            ("ana_airway_swelling", "Looks for oropharyngeal/laryngopharyngeal swelling"),
            ("ana_urticaria", "Looks for urticaria"),
            ("ana_breath_sounds", "Listens to breath sounds"),
        ],
    )
    + _items(
        "Anaphylaxis - Treatment",
        [
            ("ana_oxygen", "Places patient on proper oxygen therapy"),
            ("ana_albuterol_atrovent", "Administers albuterol/Atrovent when wheezing is present", 1, True),
            ("ana_epinephrine", "Administers epinephrine when anaphylaxis is present", 1, True),
            ("ana_benadryl", "Administers 50 mg PO Benadryl for local allergic reaction", 1, True),
            ("ana_treatment_response", "Assesses response to treatment"),
        ],
    )
)


# ==================================================
# ACUTE ABDOMEN - DECLARED 23 POINTS
# ==================================================
#
# The vaginal/pregnancy questions are conditional exactly
# as indicated by the source sheet. When they are not
# applicable, the remaining listed items total 23.
# ==================================================


ACUTE_ABDOMEN = (
    _items(
        "Acute Abdomen - Associated Symptoms",
        [
            ("abd_weakness", "Asks about weakness"),
            ("abd_sob", "Asks about shortness of breath"),
            ("abd_nausea", "Asks about nausea"),
            ("abd_chest_pain", "Asks about chest pain"),
        ],
    )
    + _items(
        "Acute Abdomen - History",
        [
            ("abd_vomiting", "Asks about vomiting/description"),
            ("abd_coffee_ground", "Asks about coffee-ground emesis"),
            ("abd_bright_red_emesis", "Asks about bright-red blood in emesis"),
            ("abd_bowel", "Asks about bowel habits and GI bleeding findings"),
            ("abd_urinary", "Asks about urinary pain/problems/odor/appearance"),
            ("abd_vaginal", "Asks about vaginal discharge when applicable", 1, True),
            ("abd_pregnancy", "Asks pregnancy/LMP/prenatal questions when applicable", 1, True),
        ],
    )
    + _items(
        "Acute Abdomen - Focused Assessment",
        [
            ("abd_guarding", "Looks for guarding"),
            ("abd_discoloration", "Looks for discoloration"),
            ("abd_distention", "Looks for distention"),
            ("abd_obvious_injury", "Looks for obvious injury"),
            ("abd_swelling", "Looks for swelling"),
            ("abd_visible_masses", "Looks for visible masses"),
            ("abd_bowel_sounds", "Listens for bowel sounds"),
            ("abd_tenderness", "Palpates quadrants for tenderness"),
            ("abd_rebound", "Assesses rebound tenderness"),
            ("abd_rigidity", "Assesses rigidity"),
            ("abd_masses", "Assesses unusual masses"),
        ],
    )
    + _items(
        "Acute Abdomen - Treatment",
        [
            ("abd_oxygen", "Places patient on proper oxygen therapy"),
            ("abd_zofran", "Considers/administers 4 mg PO Zofran for nausea", 1, True),
            ("abd_treatment_response", "Assesses response to treatment"),
        ],
    )
)


# ==================================================
# OB IN LABOR - 20 POINTS
# ==================================================


OB_LABOR = (
    _items(
        "OB - Associated Symptoms",
        [
            ("ob_nausea_vomiting", "Asks about nausea/vomiting"),
            ("ob_headache_vision", "Asks about severe headache/visual changes"),
            ("ob_vaginal_bleeding", "Asks about vaginal bleeding"),
            ("ob_sob", "Asks about shortness of breath"),
        ],
    )
    + _items(
        "OB - History",
        [
            ("ob_gestational_age", "Determines gestational age"),
            ("ob_due_date", "Obtains estimated due date"),
            ("ob_gravida", "Obtains gravida"),
            ("ob_para", "Obtains para"),
            ("ob_urge_push", "Asks about urge to push"),
            ("ob_water_broke", "Asks whether membranes ruptured"),
            ("ob_previous_complications", "Asks about previous complications"),
            ("ob_prenatal_care", "Asks about prenatal care"),
            ("ob_contraction_frequency", "Determines contraction frequency"),
            ("ob_contraction_duration", "Determines contraction duration"),
        ],
    )
    + _items(
        "OB - Focused Assessment",
        [
            ("ob_crowning", "Looks for crowning/perineal bulge"),
            ("ob_grunting_bearing_down", "Listens for grunting/bearing down"),
        ],
    )
    + _items(
        "OB - Treatment",
        [
            ("ob_oxygen", "Places patient on proper oxygen therapy"),
            ("ob_zofran", "Considers/administers 4 mg PO Zofran for nausea", 1, True),
            ("ob_prepare_delivery", "Prepares OB kit when delivery is imminent", 1, True),
            ("ob_treatment_response", "Assesses response to treatment"),
        ],
    )
)


# ==================================================
# GENERAL TRAUMA - 57 POINTS
# ==================================================


GENERAL_TRAUMA = (
    _items(
        "Trauma - Scene Size-Up",
        [
            ("trauma_bsi", "Takes/verbalizes appropriate BSI precautions"),
            ("trauma_scene_safe", "Determines scene/situation is safe"),
            ("trauma_moi", "Determines mechanism of injury"),
            ("trauma_patient_count", "Determines number of patients"),
            ("trauma_resources", "Requests/considers additional resources"),
        ],
    )
    + _items(
        "Trauma - General Impression",
        [
            ("trauma_patient_description", "Identifies patient age/sex and medical vs trauma"),
            ("trauma_chief_complaint", "Determines chief complaint/apparent life threats"),
            ("trauma_responsiveness", "Determines AVPU/orientation/LOC"),
            ("trauma_spine", "Considers spinal stabilization/self-restriction"),
            ("trauma_sick_not_sick", "Determines sick vs not sick"),
            ("trauma_index_suspicion", "Forms initial index of suspicion"),
        ],
    )
    + _items(
        "Trauma - Primary Assessment",
        [
            ("trauma_major_bleeding", "Assesses/controls major bleeding"),
            ("trauma_airway_obstruction", "Identifies airway obstruction"),
            ("trauma_airway_management", "Correctly opens/clears airway if required"),
            ("trauma_tidal_volume", "Assesses tidal volume/chest rise"),
            ("trauma_resp_rate_relative", "Assesses relative respiratory rate"),
            ("trauma_resp_pattern", "Assesses respiratory pattern"),
            ("trauma_accessory", "Assesses accessory muscles/retractions/tracheal tugging"),
            ("trauma_spo2", "Assesses SpO2"),
            ("trauma_lung_sounds", "Assesses lung sounds"),
            ("trauma_work_of_breathing", "Determines respiratory distress/failure/arrest"),
            ("trauma_oxygen", "Initiates appropriate oxygen/ventilatory management"),
            ("trauma_skin", "Assesses skin color/temperature/moisture"),
            ("trauma_pulse_strength", "Assesses pulse strength"),
            ("trauma_pulse_rate_relative", "Assesses relative pulse rate"),
            ("trauma_pulse_regularity", "Assesses pulse regularity"),
            ("trauma_pulse_equality", "Assesses pulse equality"),
            ("trauma_cap_refill", "Assesses capillary refill"),
            ("trauma_shock", "Identifies shock"),
            ("trauma_shock_treatment", "Initiates shock treatment"),
            ("trauma_environment", "Assesses hypothermia/hyperthermia"),
            ("trauma_priority", "Identifies stable/unstable transport priority"),
            ("trauma_expose", "Exposes injured area when appropriate"),
        ],
    )
    + _items(
        "Trauma - History",
        [
            ("trauma_opqrst_onset", "Obtains onset"),
            ("trauma_opqrst_provocation", "Obtains provocation/palliation"),
            ("trauma_opqrst_quality", "Obtains quality"),
            ("trauma_opqrst_radiation", "Obtains radiation"),
            ("trauma_opqrst_severity", "Obtains severity"),
            ("trauma_opqrst_time", "Obtains time"),
            ("trauma_allergies", "Obtains allergies"),
            ("trauma_medications", "Obtains medications"),
            ("trauma_pmh", "Obtains pertinent medical history"),
            ("trauma_last_intake", "Obtains last oral intake"),
            ("trauma_events", "Obtains events leading to injury"),
        ],
    )
    + _items(
        "Trauma - Vitals / Diagnostics",
        [
            ("trauma_bp", "Assesses blood pressure"),
            ("trauma_pulse_vital", "Obtains pulse rate and quality"),
            ("trauma_resp_vital", "Obtains ventilatory rate and quality"),
            ("trauma_pupils", "Assesses pupils"),
            ("trauma_bgl", "Assesses blood glucose"),
            ("trauma_secondary_spo2", "Obtains secondary SpO2"),
            ("trauma_field_impression", "States field impression"),
        ],
    )
    + _items(
        "Trauma - Reassessment / Handoff",
        [
            ("trauma_reassess_timing", "Demonstrates when to reassess"),
            ("trauma_repeat_primary", "Repeats primary assessment"),
            ("trauma_repeat_vitals", "Repeats relevant vital signs"),
            ("trauma_check_interventions", "Checks interventions"),
            ("trauma_reassess_complaint", "Reassesses complaint/overall condition"),
            ("trauma_report", "Provides accurate verbal transfer report"),
        ],
    )
)


# ==================================================
# TRAUMA HEAD-TO-TOE REGIONAL SHEETS
# ==================================================


TRAUMA_HEAD = _items(
    "Trauma Secondary - Head",
    [
        ("head_dcap", "Inspects face/scalp for DCAP-BTLS"),
        ("head_bleeding", "Inspects face/scalp for bleeding"),
        ("head_raccoon", "Checks for raccoon eyes"),
        ("head_battle", "Checks for Battle's sign"),
        ("head_ears_nose", "Checks ears/nose for CSF or blood"),
        ("head_mouth", "Inspects mouth for teeth/injury/odors"),
        ("head_pupils", "Assesses PEARL and eye injury"),
        ("head_palpate", "Palpates facial structures"),
        ("head_control_bleeding", "Controls soft-tissue bleeding correctly", 1, True),
        ("head_bandage", "Bandages injury correctly", 1, True),
        ("head_immobilize", "Immobilizes when indicated", 1, True),
        ("head_reconciliation", "Head-section total reconciliation", 1, False, True),
    ],
)

TRAUMA_NECK = _items(
    "Trauma Secondary - Neck",
    [
        ("neck_dcap", "Inspects neck for DCAP-BTLS"),
        ("neck_bleeding", "Inspects neck for bleeding"),
        ("neck_jvd", "Inspects for JVD"),
        ("neck_subq", "Inspects for subcutaneous emphysema"),
        ("neck_trachea", "Palpates trachea for deviation"),
        ("neck_cspine", "Palpates cervical spine"),
        ("neck_control_bleeding", "Controls soft-tissue bleeding correctly", 1, True),
        ("neck_bandage", "Bandages neck injury correctly", 1, True),
        ("neck_collar", "Applies C-collar when indicated", 1, True),
        ("neck_reconciliation", "Neck-section total reconciliation", 1, False, True),
    ],
)

TRAUMA_CHEST = _items(
    "Trauma Secondary - Chest",
    [
        ("chest_dcap", "Inspects chest for DCAP-BTLS"),
        ("chest_bleeding", "Inspects chest for bleeding"),
        ("chest_sucking", "Inspects for sucking chest wound"),
        ("chest_subq", "Inspects for subcutaneous emphysema"),
        ("chest_paradoxical", "Inspects for paradoxical movement"),
        ("chest_breathing", "Assesses chest breathing rate/volume/rhythm/accessory use"),
        ("chest_palpate", "Palpates shoulders/clavicles/sternum/ribs"),
        ("chest_lung_sounds", "Listens to lung sounds"),
        ("chest_control_bleeding", "Controls soft-tissue bleeding correctly", 1, True),
        ("chest_seal", "Correctly seals sucking chest wound", 1, True),
        ("chest_flail", "Correctly treats flail chest", 1, True),
        ("chest_immobilize", "Immobilizes when indicated", 1, True),
    ],
)

TRAUMA_ABDOMEN = _items(
    "Trauma Secondary - Abdomen",
    [
        ("trauma_abd_dcap", "Inspects abdomen for DCAP-BTLS"),
        ("trauma_abd_bleeding", "Inspects abdomen for bleeding"),
        ("trauma_abd_evisceration", "Inspects for evisceration"),
        ("trauma_abd_cullen", "Inspects bruising around umbilicus"),
        ("trauma_abd_grey_turner", "Inspects flank bruising"),
        ("trauma_abd_palpate", "Palpates all quadrants"),
        ("trauma_abd_control_bleeding", "Controls soft-tissue bleeding correctly", 1, True),
        ("trauma_abd_bandage_evis", "Bandages evisceration correctly", 1, True),
        ("trauma_abd_immobilize", "Immobilizes when indicated", 1, True),
    ],
)

TRAUMA_PELVIS = _items(
    "Trauma Secondary - Pelvis",
    [
        ("pelvis_dcap", "Inspects pelvis for DCAP-BTLS"),
        ("pelvis_bleeding", "Inspects pelvis for bleeding"),
        ("pelvis_priapism", "Inspects for priapism"),
        ("pelvis_stability", "Assesses pelvic stability"),
        ("pelvis_control_bleeding", "Controls bleeding correctly", 1, True),
        ("pelvis_stabilize", "Stabilizes pelvic fracture", 1, True),
        ("pelvis_immobilize", "Immobilizes when indicated", 1, True),
    ],
)

TRAUMA_LOWER = _items(
    "Trauma Secondary - Lower Extremities",
    [
        ("lower_dcap", "Inspects lower extremities for DCAP-BTLS"),
        ("lower_bleeding", "Inspects lower extremities for bleeding"),
        ("lower_pms", "Assesses distal perfusion/PMS"),
        ("lower_palpate", "Palpates lower extremities"),
        ("lower_control_bleeding", "Controls bleeding correctly", 1, True),
        ("lower_splint", "Splints fracture and checks PMS before/after", 1, True),
        ("lower_immobilize", "Immobilizes when indicated", 1, True),
    ],
)

TRAUMA_UPPER = _items(
    "Trauma Secondary - Upper Extremities",
    [
        ("upper_dcap", "Inspects upper extremities for DCAP-BTLS"),
        ("upper_bleeding", "Inspects upper extremities for bleeding"),
        ("upper_pms", "Assesses distal perfusion/PMS"),
        ("upper_palpate", "Palpates upper extremities"),
        ("upper_control_bleeding", "Controls bleeding correctly", 1, True),
        ("upper_splint", "Splints fracture and checks PMS before/after", 1, True),
        ("upper_immobilize", "Immobilizes when indicated", 1, True),
    ],
)

TRAUMA_BACK = _items(
    "Trauma Secondary - Back/Posterior",
    [
        ("back_dcap", "Inspects back/posterior for DCAP-BTLS"),
        ("back_bleeding", "Inspects back/posterior for bleeding"),
        ("back_sucking", "Inspects posterior chest for sucking wound"),
        ("back_subq", "Inspects for subcutaneous emphysema"),
        ("back_palpate", "Palpates back for deformity/tenderness/crepitus"),
        ("back_control_bleeding", "Controls soft-tissue bleeding correctly", 1, True),
        ("back_seal", "Correctly seals posterior sucking chest wound", 1, True),
        ("back_immobilize", "Immobilizes when indicated", 1, True),
    ],
)

TRAUMA_REGION_RUBRICS = {
    "head": TRAUMA_HEAD,
    "neck": TRAUMA_NECK,
    "chest": TRAUMA_CHEST,
    "abdomen": TRAUMA_ABDOMEN,
    "pelvis": TRAUMA_PELVIS,
    "lower_extremities": TRAUMA_LOWER,
    "upper_extremities": TRAUMA_UPPER,
    "back": TRAUMA_BACK,
}


# ==================================================
# AIRWAY MANAGEMENT - 31 POINTS
# ==================================================


AIRWAY = _items(
    "Airway Management",
    [
        ("airway_scene_safe", "Considers scene safety"),
        ("airway_bsi", "Takes/verbalizes BSI precautions"),
        ("airway_responsiveness", "Checks responsiveness with sternal rub"),
        ("airway_resources", "Considers additional resources"),
        ("airway_carotid_pulse", "Checks carotid pulse no longer than 10 seconds"),
        ("airway_ramping", "Provides padding/ramping"),
        ("airway_check_breathing", "Checks breathing with head tilt-chin lift"),
        ("airway_suction_prepare", "Prepares rigid suction catheter"),
        ("airway_suction_test", "Turns on/tests suction"),
        ("airway_suction_insert", "Inserts catheter without suction"),
        ("airway_suction_15", "Suctions mouth/oropharynx no longer than 15 seconds"),
        ("airway_opa_measure", "Correctly measures OPA"),
        ("airway_opa_insert", "Uses scissor technique and inserts OPA"),
        ("airway_bvm_start", "Immediately initiates BVM ventilation"),
        ("airway_bvm_o2", "Attaches BVM to 15 LPM oxygen"),
        ("airway_bvm_volume", "Provides adequate chest rise/fall"),
        ("airway_bvm_rate", "Ventilates every 5-6 seconds"),
        ("airway_spo2_initial", "Applies pulse ox and obtains SpO2"),
        ("airway_partner_ventilate", "Requests partner continue ventilating"),
        ("airway_sga_size", "Prepares correct-size supraglottic airway"),
        ("airway_sga_lubricate", "Lubricates supraglottic airway"),
        ("airway_sga_position", "Positions head with head tilt-chin lift"),
        ("airway_sga_scissor", "Uses scissor technique to open airway"),
        ("airway_sga_insert", "Inserts supraglottic airway to proper depth"),
        ("airway_sga_ventilate", "Ventilates at proper rate/depth after placement"),
        ("airway_sga_confirm_sounds", "Confirms placement with epigastric/lung sounds"),
        ("airway_sga_condensation", "Identifies condensation in airway"),
        ("airway_sga_colorimetric", "Identifies gold color change in colorimetric device"),
        ("airway_spo2_reassess", "Reassesses pulse ox"),
        ("airway_skin_reassess", "Reassesses skin color"),
        ("airway_sga_secure", "Secures device to upper lip/cheek"),
    ],
)


# ==================================================
# SCENARIO RUBRIC MAP
# ==================================================


MEDICAL_FOCUSED = {
    "respiratory": RESPIRATORY,
    "cardiac": CARDIAC,
    "neurological": NEUROLOGICAL,
    "anaphylaxis": ANAPHYLAXIS,
    "acute_abdomen": ACUTE_ABDOMEN,
    "ob_labor": OB_LABOR,
}


ALL_RUBRICS = (
    GENERAL_MEDICAL
    + RESPIRATORY
    + CARDIAC
    + NEUROLOGICAL
    + ANAPHYLAXIS
    + ACUTE_ABDOMEN
    + OB_LABOR
    + GENERAL_TRAUMA
    + AIRWAY
    + sum(
        TRAUMA_REGION_RUBRICS.values(),
        [],
    )
)

RUBRIC_ITEM_BY_KEY = {
    item.key: item
    for item in ALL_RUBRICS
}


# ==================================================
# AUTOMATIC RECONCILIATION BONUSES
# ==================================================


AUTO_COMPLETION_BONUSES = {
    "neuro_feel_reconciliation": (
        "neuro_head_palpation",
        "neuro_pms",
        "neuro_cincinnati",
        "neuro_environment_skin",
    ),
    "head_reconciliation": (
        "head_dcap",
        "head_bleeding",
        "head_raccoon",
        "head_battle",
        "head_ears_nose",
        "head_mouth",
        "head_pupils",
        "head_palpate",
    ),
    "neck_reconciliation": (
        "neck_dcap",
        "neck_bleeding",
        "neck_jvd",
        "neck_subq",
        "neck_trachea",
        "neck_cspine",
    ),
}


# ==================================================
# RUBRIC SELECTION
# ==================================================


def get_applicable_rubric_items(
    scenario: dict,
) -> list[RubricItem]:
    scenario_type = scenario["scenario_type"]

    if scenario_type in MEDICAL_FOCUSED:
        items = list(GENERAL_MEDICAL)
        items.extend(MEDICAL_FOCUSED[scenario_type])

    elif scenario_type == "trauma":
        items = list(GENERAL_TRAUMA)

        for region in scenario.get(
            "trauma_regions",
            [],
        ):
            items.extend(
                TRAUMA_REGION_RUBRICS.get(
                    region,
                    [],
                )
            )

    elif scenario_type == "airway":
        items = list(AIRWAY)

    else:
        raise ValueError(
            "Unknown assessment scenario type: "
            f"{scenario_type}"
        )

    applicable_conditional = set(
        scenario.get(
            "applicable_conditional_keys",
            [],
        )
    )

    if scenario.get(
        "airway_obstruction_present",
        False,
    ):
        applicable_conditional.add(
            "medical_airway_management"
        )

    if scenario.get(
        "shock_present",
        False,
    ):
        applicable_conditional.add(
            "medical_shock_treatment"
        )

    if scenario.get(
        "pregnancy_questions_applicable",
        False,
    ):
        applicable_conditional.update(
            {
                "abd_vaginal",
                "abd_pregnancy",
            }
        )

    result = []

    for item in items:
        if (
            item.conditional
            and item.key not in applicable_conditional
        ):
            continue

        result.append(item)

    return result


def get_visible_rubric_items(
    scenario: dict,
) -> list[RubricItem]:
    return [
        item
        for item in get_applicable_rubric_items(
            scenario
        )
        if not item.hidden
    ]


def get_rubric_prompt_text(
    scenario: dict,
) -> str:
    items = get_visible_rubric_items(
        scenario
    )

    return "\n".join(
        f"- {item.key}: {item.label}"
        for item in items
    )


def get_conditional_rubric_prompt_text(
    scenario_type: str,
) -> str:
    if scenario_type in MEDICAL_FOCUSED:
        candidates = (
            list(GENERAL_MEDICAL)
            + list(MEDICAL_FOCUSED[scenario_type])
        )
    elif scenario_type == "trauma":
        candidates = list(GENERAL_TRAUMA)
        for region_items in TRAUMA_REGION_RUBRICS.values():
            candidates.extend(region_items)
    elif scenario_type == "airway":
        candidates = list(AIRWAY)
    else:
        candidates = []

    conditional = [
        item
        for item in candidates
        if item.conditional
    ]

    if not conditional:
        return "(none)"

    return "\n".join(
        f"- {item.key}: {item.label}"
        for item in conditional
    )


def get_max_points(
    scenario: dict,
) -> int:
    return sum(
        item.points
        for item in get_applicable_rubric_items(
            scenario
        )
    )


def get_section_max_points(
    scenario: dict,
) -> dict[str, int]:
    totals: dict[str, int] = {}

    for item in get_applicable_rubric_items(
        scenario
    ):
        totals[item.section] = (
            totals.get(item.section, 0)
            + item.points
        )

    return totals


# ==================================================
# GENERATOR CATALOG
# ==================================================


def get_scenario_type_catalog(
    scenario_type: str,
) -> list[RubricItem]:
    """Return every possible rubric item for generation."""

    if scenario_type in MEDICAL_FOCUSED:
        return (
            list(GENERAL_MEDICAL)
            + list(MEDICAL_FOCUSED[scenario_type])
        )

    if scenario_type == "trauma":
        items = list(GENERAL_TRAUMA)
        for region_items in TRAUMA_REGION_RUBRICS.values():
            items.extend(region_items)
        return items

    if scenario_type == "airway":
        return list(AIRWAY)

    raise ValueError(
        "Unknown assessment scenario type: "
        f"{scenario_type}"
    )


def get_scenario_type_catalog_text(
    scenario_type: str,
) -> str:
    return "\n".join(
        f"- {item.key}: {item.label}"
        for item in get_scenario_type_catalog(
            scenario_type
        )
        if not item.hidden
    )
