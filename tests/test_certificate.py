from qfabric.certificate import issue_prediction_certificate
from qfabric.models import EntanglementRequest
from qfabric.planner import Allocation


def test_certificate_does_not_claim_physical_verification():
    req = EntanglementRequest("r", "u", "A", "B", 0.8, 10.0)
    allocation = Allocation("r", "u", True, ("A", "B"), 0.9, 5.0, 0, ())
    cert = issue_prediction_certificate(req, allocation)
    assert cert.status == "PREDICTED_FEASIBLE_NOT_PHYSICALLY_VERIFIED"
    assert cert.evidence.evidence_type == "simulation_prediction"
    assert len(cert.sha256) == 64


def test_certificate_verifier_accepts_valid_certificate():
    from qfabric.certificate import verify_prediction_certificate

    req = EntanglementRequest("r", "u", "A", "B", 0.8, 10.0)
    allocation = Allocation("r", "u", True, ("A", "B"), 0.9, 5.0, 0, ())
    cert = issue_prediction_certificate(req, allocation)
    assert verify_prediction_certificate(cert)


def test_certificate_verifier_rejects_modified_evidence():
    from dataclasses import replace
    from qfabric.certificate import verify_prediction_certificate

    req = EntanglementRequest("r", "u", "A", "B", 0.8, 10.0)
    allocation = Allocation("r", "u", True, ("A", "B"), 0.9, 5.0, 0, ())
    cert = issue_prediction_certificate(req, allocation)
    modified = replace(cert, evidence=replace(cert.evidence, fidelity_claim=0.99))
    assert not verify_prediction_certificate(modified)


def test_certificate_verifier_rejects_wrong_status():
    from dataclasses import replace
    from qfabric.certificate import verify_prediction_certificate

    req = EntanglementRequest("r", "u", "A", "B", 0.8, 10.0)
    allocation = Allocation("r", "u", True, ("A", "B"), 0.9, 5.0, 0, ())
    cert = issue_prediction_certificate(req, allocation)
    assert not verify_prediction_certificate(replace(cert, status="REJECTED_BY_PLANNER"))


def test_certificate_rejects_allocation_for_different_user():
    import pytest

    req = EntanglementRequest("r", "u", "A", "B", 0.8, 10.0)
    allocation = Allocation("r", "other-user", True, ("A", "B"), 0.9, 5.0, 0, ())
    with pytest.raises(ValueError, match="user_id"):
        issue_prediction_certificate(req, allocation)
