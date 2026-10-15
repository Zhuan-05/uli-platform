import copy

import pytest

from compatibility.validator import ManifestValidationError, validate_manifest_dict
from core import ULI_PROTOCOL_VERSION
from tests.conftest import make_manifest


def test_valid_manifest_parses():
    m = validate_manifest_dict(make_manifest("uli.test.valid"), source="<t>")
    assert m.id == "uli.test.valid"
    assert m.runtime.type == "in-process"


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda d: d.update({"id": "Bad ID!"}), "id"),
        (lambda d: d.update({"version": "not-semver"}), "version"),
        (lambda d: d.update({"uli": {"protocol": ">=x"}}), "protocol"),
        (lambda d: d.update({"runtime": {"type": "teleport"}}), "teleport"),
        (lambda d: d.update({"permissions": ["root.everything"]}), "permissions"),
    ],
)
def test_invalid_manifests_rejected(mutate, needle):
    raw = make_manifest("uli.test.invalid")
    mutate(raw)
    with pytest.raises(ManifestValidationError) as exc:
        validate_manifest_dict(raw, source="<t>")
    assert any(needle in e for e in exc.value.errors), exc.value.errors


def test_protocol_range_rejected_at_registration(services):
    raw = make_manifest("uli.test.proto")
    raw["uli"]["protocol"] = ">=9.0.0"  # Core is 1.0.0
    m = validate_manifest_dict(raw, source="<t>")
    from core.registry import RegistryError

    with pytest.raises(RegistryError):
        services.registry.register(m, ".", is_builtin=True)


def test_registration_via_api(client, tmp_path):
    # static app has no protocol/version friction
    resp = client.post(
        "/api/apps/register-external",
        json={"name": "Example", "url": "https://example.com"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["app"]["runtimeType"] == "external-url"
    assert resp.json()["app"]["trust"] == "untrusted"
