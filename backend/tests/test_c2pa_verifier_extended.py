"""Extended C2PA verifier tests covering parse/signature/assertion branches."""

from __future__ import annotations

from app.services.c2pa_verifier import C2PAVerifier


def _verifier() -> C2PAVerifier:
    return C2PAVerifier()


# --- _parse_json_output --------------------------------------------------


class TestParseJsonOutput:
    def test_valid_json_string(self) -> None:
        v = _verifier()
        assert v._parse_json_output('{"status": "ok"}') == {"status": "ok"}

    def test_empty_string_returns_none(self) -> None:
        v = _verifier()
        assert v._parse_json_output("") is None

    def test_none_returns_none(self) -> None:
        v = _verifier()
        assert v._parse_json_output(None) is None

    def test_non_dict_json_returns_none(self) -> None:
        v = _verifier()
        assert v._parse_json_output("[1, 2, 3]") is None

    def test_json_with_leading_text(self) -> None:
        v = _verifier()
        result = v._parse_json_output('some noise {"key": "val"} trailing')
        assert result == {"key": "val"}

    def test_completely_invalid_json_returns_none(self) -> None:
        v = _verifier()
        assert v._parse_json_output("not json at all") is None


# --- _infer_signature_valid -----------------------------------------------


class TestInferSignatureValid:
    def test_bool_flag_true(self) -> None:
        v = _verifier()
        payload = {"validation_results": {"active_manifest": {"valid": True}}}
        assert v._infer_signature_valid(payload) is True

    def test_bool_flag_false(self) -> None:
        v = _verifier()
        payload = {"validation_results": {"active_manifest": {"valid": False}}}
        assert v._infer_signature_valid(payload) is False

    def test_status_string_valid(self) -> None:
        v = _verifier()
        payload = {"validation_results": {"active_manifest": {"status": "verified"}}}
        assert v._infer_signature_valid(payload) is True

    def test_status_string_invalid(self) -> None:
        v = _verifier()
        payload = {"validation_results": {"active_manifest": {"status": "failed"}}}
        assert v._infer_signature_valid(payload) is False

    def test_no_validation_info(self) -> None:
        v = _verifier()
        assert v._infer_signature_valid({}) is False


# --- _extract_assertions --------------------------------------------------


class TestExtractAssertions:
    def test_assertions_list_of_strings(self) -> None:
        v = _verifier()
        payload = {"assertions": ["c2pa.actions", "c2pa.hash.data"]}
        assert v._extract_assertions(payload) == ["c2pa.actions", "c2pa.hash.data"]

    def test_assertions_list_of_dicts(self) -> None:
        v = _verifier()
        payload = {"assertions": [{"label": "c2pa.actions"}, {"name": "c2pa.hash"}]}
        assert v._extract_assertions(payload) == ["c2pa.actions", "c2pa.hash"]

    def test_assertions_not_list(self) -> None:
        v = _verifier()
        assert v._extract_assertions({"assertions": "not-a-list"}) == []

    def test_assertions_mixed_entries(self) -> None:
        v = _verifier()
        payload = {"assertions": ["c2pa.actions", {"type": "sig"}, 42]}
        assert v._extract_assertions(payload) == ["c2pa.actions", "sig"]

    def test_assertions_nested_under_active_manifest(self) -> None:
        v = _verifier()
        payload = {"active_manifest": {"assertions": [{"label": "nested"}]}}
        assert v._extract_assertions(payload) == ["nested"]


# --- _parse_payload additional branches -----------------------------------


class TestParsePayload:
    def test_manifest_present_but_signature_invalid(self) -> None:
        v = _verifier()
        payload = {
            "active_manifest": {"label": "urn:123", "claim_generator": "Issuer"},
            "signature": {"valid": False},
        }
        result = v._parse_payload(payload)
        assert result.status == "unverified"
        assert result.manifest_present is True
        assert result.signature_valid is False

    def test_manifest_store_path(self) -> None:
        v = _verifier()
        payload = {
            "manifest_store": {
                "active_manifest": {
                    "label": "urn:456",
                    "claim_generator": "StoreIssuer",
                    "validation": {"valid": True},
                    "assertions": [{"label": "c2pa.hash.data"}],
                }
            }
        }
        result = v._parse_payload(payload)
        assert result.status == "verified"
        assert result.issuer == "StoreIssuer"
        assert result.manifest_id == "urn:456"
        assert "c2pa.hash.data" in result.assertions


# --- verify_bytes empty payload -------------------------------------------


def test_verify_bytes_empty_payload() -> None:
    v = _verifier()
    result = v.verify_bytes(b"")
    assert result.status == "unsupported"
    assert result.manifest_present is False


# --- _run_c2pa_tool with mock subprocess ----------------------------------


def test_run_c2pa_tool_all_commands_fail(monkeypatch) -> None:
    import subprocess as sp

    def mock_run(*_args, **_kwargs):
        result = sp.CompletedProcess(args=[], returncode=1, stdout="", stderr="parse error")
        return result

    monkeypatch.setattr("subprocess.run", mock_run)
    v = _verifier()
    payload, error = v._run_c2pa_tool("c2patool", __import__("pathlib").Path("/fake.jpg"))
    assert payload is None
    assert "c2patool command failed" in error


def test_run_c2pa_tool_success_on_first_attempt(monkeypatch) -> None:
    import subprocess as sp

    def mock_run(*_args, **_kwargs):
        return sp.CompletedProcess(args=[], returncode=0, stdout='{"status": "ok"}', stderr="")

    monkeypatch.setattr("subprocess.run", mock_run)
    v = _verifier()
    payload, error = v._run_c2pa_tool("c2patool", __import__("pathlib").Path("/fake.jpg"))
    assert payload == {"status": "ok"}
    assert error == ""


def test_run_c2pa_tool_exception(monkeypatch) -> None:
    def mock_run(*_args, **_kwargs):
        raise OSError("command not found")

    monkeypatch.setattr("subprocess.run", mock_run)
    v = _verifier()
    payload, error = v._run_c2pa_tool("c2patool", __import__("pathlib").Path("/fake.jpg"))
    assert payload is None
    assert "CLI execution error" in error
