from __future__ import annotations

from itertools import product
from typing import Any, Dict, List

POLICY_GRID_VALUES = tuple(index / 10 for index in range(11))


def policy_grid_cases() -> List[Dict[str, Any]]:
    cases = []
    for index, (detector, history, retrieval) in enumerate(
        product(POLICY_GRID_VALUES, repeat=3)
    ):
        score = 0.45 * detector + 0.35 * history + 0.20 * retrieval
        decision = "auto_act" if score >= 0.90 else "alert" if score >= 0.60 else "escalate"
        cases.append(
            {
                "id": f"M2-POLICY-GRID-{index:04d}",
                "detector_conf": detector,
                "history_risk": history,
                "retrieval_agreement": retrieval,
                "expected_score": score,
                "expected_decision": decision,
                "requirement": "POLICY_THRESHOLDS_AND_FUSION",
            }
        )
    return cases


POLICY_CASES = policy_grid_cases()
POLICY_CASE_BY_ID = {case["id"]: case for case in POLICY_CASES}
