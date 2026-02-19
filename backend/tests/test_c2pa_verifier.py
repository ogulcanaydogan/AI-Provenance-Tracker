from __future__ import annotations

from app.services.c2pa_verifier import C2PAVerifier


def test_parse_payload_verified_manifest() -> None:
    verifier = C2PAVerifier()
    payload = {
        "active_manifest": {
            "label": "urn:manifest:123",
            "claim_generator": "ExampleIssuer",
            "assertions": [{"label": "c2pa.actions"}, {"label": "c2pa.hash.data"}],
            "validation_status": "valid",
        }
    }

    result = verifier._parse_payload(payload)

    assert result.status == "verified"
    assert result.manifest_present is True
    assert result.signature_valid is True
    assert result.issuer == "ExampleIssuer"
    assert result.manifest_id == "urn:manifest:123"
    assert "c2pa.actions" in result.assertions


def test_parse_payload_unverified_without_manifest() -> None:
    verifier = C2PAVerifier()
    payload = {"some": "value"}

    result = verifier._parse_payload(payload)

    assert result.status == "unverified"
    assert result.manifest_present is False
    assert result.signature_valid is False


def test_verify_bytes_returns_unavailable_when_tool_missing(monkeypatch) -> None:
    verifier = C2PAVerifier()
    monkeypatch.setattr("app.services.c2pa_verifier.shutil.which", lambda _tool: None)

    result = verifier.verify_bytes(b"fake-binary", filename="sample.jpg")

    assert result.status == "unavailable"
    assert result.signature_valid is False
