from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import hmac
import json
import math

from .models import EntanglementRequest
from .planner import Allocation


@dataclass(frozen=True)
class ServiceEvidence:
    request_id: str
    accepted: bool
    fidelity_claim: float | None
    required_fidelity: float
    completion_time_claim: float | None
    deadline: float
    path: tuple[str, ...] | None
    model_version: str
    evidence_type: str = "simulation_prediction"


@dataclass(frozen=True)
class ServiceCertificate:
    evidence: ServiceEvidence
    status: str
    sha256: str


def _payload(evidence: ServiceEvidence) -> str:
    return json.dumps(
        asdict(evidence),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _expected_status(evidence: ServiceEvidence) -> str:
    if not evidence.accepted:
        return "REJECTED_BY_PLANNER"

    if (
        evidence.fidelity_claim is None
        or evidence.completion_time_claim is None
        or evidence.path is None
        or len(evidence.path) < 2
    ):
        return "INCOMPLETE_EVIDENCE"

    if (
        not math.isfinite(evidence.fidelity_claim)
        or not math.isfinite(evidence.completion_time_claim)
        or not math.isfinite(evidence.required_fidelity)
        or not math.isfinite(evidence.deadline)
    ):
        return "INCOMPLETE_EVIDENCE"

    if (
        evidence.fidelity_claim >= evidence.required_fidelity
        and evidence.completion_time_claim <= evidence.deadline
    ):
        return "PREDICTED_FEASIBLE_NOT_PHYSICALLY_VERIFIED"

    return "PREDICTION_CONTRADICTS_QOS"


def issue_prediction_certificate(
    request: EntanglementRequest,
    allocation: Allocation,
) -> ServiceCertificate:
    if allocation.request_id != request.request_id:
        raise ValueError("allocation request_id does not match request")
    if allocation.user_id != request.user_id:
        raise ValueError("allocation user_id does not match request")

    evidence = ServiceEvidence(
        request_id=request.request_id,
        accepted=allocation.accepted,
        fidelity_claim=allocation.predicted_fidelity,
        required_fidelity=request.required_fidelity,
        completion_time_claim=allocation.expected_completion_time,
        deadline=request.deadline,
        path=allocation.path,
        model_version="qfabric-0.2.1",
    )

    status = _expected_status(evidence)
    digest = hashlib.sha256(_payload(evidence).encode("utf-8")).hexdigest()
    return ServiceCertificate(evidence, status, digest)


def verify_prediction_certificate(certificate: ServiceCertificate) -> bool:
    """Verify evidence integrity and internal QoS consistency.

    This does not authenticate the issuer. SHA-256 is not a digital signature.
    """
    try:
        evidence = certificate.evidence
        if not isinstance(evidence, ServiceEvidence):
            return False
        if not isinstance(certificate.status, str):
            return False
        if not isinstance(certificate.sha256, str):
            return False
        if evidence.evidence_type != "simulation_prediction":
            return False
        if not evidence.request_id or not evidence.model_version:
            return False

        expected_digest = hashlib.sha256(
            _payload(evidence).encode("utf-8")
        ).hexdigest()

        if not hmac.compare_digest(expected_digest, certificate.sha256):
            return False

        return certificate.status == _expected_status(evidence)
    except (TypeError, ValueError, AttributeError, OverflowError):
        return False
