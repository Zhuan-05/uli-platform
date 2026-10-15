"""Version/protocol compatibility rules (enforceable vs. cooperation-based).

ULI separates three version axes:

* **application version** - the app's own SemVer (``manifest.version``)
* **ULI protocol version** - the platform contract (``manifest.uli.protocol``)
* **capability contract version** - each provided capability's own SemVer

This module only enforces what the platform can actually observe. Everything
that requires the application author's cooperation (e.g. whether a handler
really honours a schema it declared) is reported as a *warning*, never a pass.
"""
from __future__ import annotations

from dataclasses import dataclass

from core import ULI_PROTOCOL_VERSION
from core.models import CapabilitySpec, Manifest, RequirementSpec
from core.version import VersionError, parse_version, satisfies_range


@dataclass
class CompatibilityResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def check_protocol_range(protocol_range: str, core_version: str = ULI_PROTOCOL_VERSION) -> CompatibilityResult:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        if not satisfies_range(core_version, protocol_range):
            errors.append(
                f"ULI protocol {core_version} does not satisfy the application's "
                f"required range {protocol_range!r}"
            )
    except VersionError as exc:
        errors.append(f"Invalid ULI protocol range {protocol_range!r}: {exc}")
    return CompatibilityResult(ok=not errors, errors=errors, warnings=warnings)


def resolve_requirements(
    manifest: Manifest,
    available: dict[str, list[tuple[str, CapabilitySpec]]],
) -> CompatibilityResult:
    """Check every declared requirement against currently available providers.

    ``available`` maps capability id -> list of ``(app_id, CapabilitySpec)``.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for req in manifest.requires:
        candidates = available.get(req.id, [])
        compatible = [
            (app_id, cap)
            for app_id, cap in candidates
            if _satisfies(req, cap)
        ]
        if compatible:
            continue
        if candidates:
            provided = ", ".join(f"{a}:{c.version}" for a, c in candidates)
            msg = (
                f"Requirement {req.id!r} {req.version_range} has providers but no "
                f"compatible version (found: {provided})"
            )
        else:
            msg = f"Requirement {req.id!r} {req.version_range} has no provider"
        if req.optional:
            warnings.append("OPTIONAL " + msg)
        else:
            errors.append(msg)

    return CompatibilityResult(ok=not errors, errors=errors, warnings=warnings)


def _satisfies(req: RequirementSpec, cap: CapabilitySpec) -> bool:
    try:
        return satisfies_range(cap.version, req.version_range)
    except VersionError:
        return False


def capability_interface_id(cap: CapabilitySpec, side: str) -> str:
    """Stable identifier for one side of a capability's interface.

    Used by the visual builder to decide whether two ports may connect. The
    ``side`` must be ``"input"`` or ``"output"``.
    """
    if side == "input":
        return cap.input_type
    if side == "output":
        return cap.output_type
    raise ValueError(f"side must be 'input' or 'output', got {side!r}")


def port_types_compatible(source_output_type: str, target_input_type: str) -> tuple[bool, str]:
    """Decide whether an output port may feed an input port.

    ``*`` is the wildcard/any contract. Exact string equality is required
    otherwise; ULI deliberately does *not* attempt structural JSON-Schema
    subtyping in the MVP (documented limitation).
    """
    if source_output_type == "*" or target_input_type == "*":
        return True, "wildcard contract accepts any payload"
    if source_output_type == target_input_type:
        return True, f"identical contract {source_output_type}"
    return (
        False,
        f"contract mismatch: output provides {source_output_type!r} "
        f"but input requires {target_input_type!r}",
    )


def compatibility_summary() -> dict[str, list[str]]:
    """Documents what the platform can and cannot guarantee."""
    return {
        "enforceable": [
            "ULI protocol range matches the running Core protocol version",
            "Declared capability requirements are satisfied by a running provider",
            "Capability contract versions satisfy declared SemVer ranges",
            "Inputs/outputs validate against the JSON Schemas in the manifest",
            "Port type equality for blueprint connections",
            "Manifest structural validity",
        ],
        "requires_developer_cooperation": [
            "That a handler truly implements the semantics its schema implies",
            "That an application does not mutate data it does not own",
            "That third-party websites permit iframe embedding (browser/CSP enforced)",
            "That a native app opts into the theme SDK rather than hard-coding styles",
            "Data migration correctness across major versions",
        ],
    }
