"""Blueprint validation + execution engine.

Connection compatibility is checked with the *same* rule the UI uses, so the
visual builder and the runtime can never disagree about what is valid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from blueprints.schema import validate_blueprint_structure
from core.capabilities import CapabilityRegistry
from core.compatibility import port_types_compatible
from module_manager import ModuleManager


@dataclass
class ConnectionIssue:
    edge_id: str
    source: str
    target: str
    ok: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "edgeId": self.edge_id,
            "source": self.source,
            "target": self.target,
            "ok": self.ok,
            "reason": self.reason,
        }


@dataclass
class ExecutionStep:
    node_id: str
    capability: str | None
    ok: bool
    input: Any = None
    output: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodeId": self.node_id,
            "capability": self.capability,
            "ok": self.ok,
            "input": self.input,
            "output": self.output,
            "error": self.error,
        }


class BlueprintExecutionError(Exception):
    pass


class BlueprintEngine:
    def __init__(self, capabilities: CapabilityRegistry, manager: ModuleManager) -> None:
        self.capabilities = capabilities
        self.manager = manager

    # ------------------------------------------------------------------ #
    # Port typing
    # ------------------------------------------------------------------ #
    def _capability_types(self, capability_id: str) -> tuple[str, str] | None:
        providers = self.capabilities.providers(capability_id)
        if not providers:
            return None
        # highest version already deterministic via registry ordering
        best = sorted(providers, key=lambda d: d.version, reverse=True)[0]
        return best.input_type, best.output_type

    def _node_input_type(self, node: dict) -> tuple[str | None, str | None]:
        kind = node["kind"]
        if kind == "input":
            return None, node.get("outputType", "*")
        if kind == "output":
            return node.get("inputType", "*"), None
        types = self._capability_types(node.get("capability", ""))
        if types is None:
            return None, None
        return types

    def _node_output_type(self, node: dict) -> tuple[str | None, str | None]:
        kind = node["kind"]
        if kind == "input":
            return node.get("outputType", "*"), None
        if kind == "output":
            return None, None
        types = self._capability_types(node.get("capability", ""))
        if types is None:
            return None, None
        return types[1], None

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self, blueprint: dict) -> dict[str, Any]:
        try:
            validate_blueprint_structure(blueprint)
            structural_ok = True
        except ValueError as exc:
            errors = getattr(exc, "errors", [str(exc)])
            return {"valid": False, "errors": errors, "issues": []}

        nodes = {n["id"]: n for n in blueprint["nodes"]}
        issues: list[ConnectionIssue] = []
        for edge in blueprint["edges"]:
            source = nodes[edge["source"]]
            target = nodes[edge["target"]]
            src_type = self._node_output_type(source)[0]
            tgt_type = self._node_input_type(target)[0]

            if src_type is None and source["kind"] == "capability":
                reason = f"capability {source.get('capability')!r} has no installed provider"
                issues.append(ConnectionIssue(edge["id"], edge["source"], edge["target"], False, reason))
                continue
            if tgt_type is None and target["kind"] == "capability":
                reason = f"capability {target.get('capability')!r} has no installed provider"
                issues.append(ConnectionIssue(edge["id"], edge["source"], edge["target"], False, reason))
                continue

            ok, reason = port_types_compatible(src_type or "*", tgt_type or "*")
            issues.append(ConnectionIssue(edge["id"], edge["source"], edge["target"], ok, reason))

        # Every capability node must have an incoming edge (except isolated output/input).
        incoming = {e["target"] for e in blueprint["edges"]}
        for node in blueprint["nodes"]:
            if node["kind"] == "capability" and node["id"] not in incoming:
                issues.append(
                    ConnectionIssue("", node["id"], node["id"], False, "capability node has no input")
                )

        valid = structural_ok and all(i.ok for i in issues)
        return {
            "valid": valid,
            "errors": [],
            "issues": [i.to_dict() for i in issues],
        }

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #
    async def execute(
        self,
        blueprint: dict,
        input_payload: dict[str, Any] | None = None,
        *,
        caller_app_id: str | None = None,
    ) -> dict[str, Any]:
        report = self.validate(blueprint)
        if not report["valid"]:
            raise BlueprintExecutionError(
                "Blueprint is not executable: "
                + "; ".join(i["reason"] for i in report["issues"] if not i["ok"] or i["reason"])
            )

        nodes = {n["id"]: n for n in blueprint["nodes"]}
        order = self._topological_order(nodes, blueprint["edges"])

        incoming: dict[str, list[tuple[str, str]]] = {}
        for edge in blueprint["edges"]:
            incoming.setdefault(edge["target"], []).append(
                (edge["source"], edge.get("sourcePort", "out"))
            )

        values: dict[str, Any] = {}
        steps: list[ExecutionStep] = []
        result: Any = None

        for node_id in order:
            node = nodes[node_id]
            kind = node["kind"]

            if kind == "input":
                sample = node.get("sample", {})
                if self._is_primary_input(node, nodes) and input_payload:
                    values[node_id] = input_payload
                else:
                    values[node_id] = sample
                continue

            upstream = [values.get(src) for src, _ in incoming.get(node_id, [])]
            node_input: Any
            if len(upstream) == 0:
                node_input = {}
            elif len(upstream) == 1:
                node_input = upstream[0]
            else:
                merged: dict[str, Any] = {}
                for item in upstream:
                    if isinstance(item, dict):
                        merged.update(item)
                node_input = merged

            if kind == "capability":
                capability_id = node["capability"]
                try:
                    outcome = await self.manager.invoke_capability(
                        capability_id,
                        node_input if isinstance(node_input, dict) else {"value": node_input},
                        version_range=node.get("config", {}).get("versionRange", "*"),
                        caller_app_id=caller_app_id,
                    )
                    values[node_id] = outcome["output"]
                    steps.append(
                        ExecutionStep(node_id, capability_id, True, node_input, outcome["output"])
                    )
                except Exception as exc:  # noqa: BLE001 - report step failure precisely
                    steps.append(
                        ExecutionStep(node_id, capability_id, False, node_input, None, str(exc))
                    )
                    raise BlueprintExecutionError(
                        f"step {node_id} ({capability_id}) failed: {exc}"
                    ) from exc
            elif kind == "output":
                values[node_id] = node_input
                result = node_input
                steps.append(ExecutionStep(node_id, None, True, node_input, node_input))

        return {
            "ok": True,
            "blueprintId": blueprint["id"],
            "result": result,
            "values": values,
            "steps": [s.to_dict() for s in steps],
        }

    @staticmethod
    def _is_primary_input(node: dict, nodes: dict) -> bool:
        # First input node by declaration order is the one bound to execute input.
        for n in nodes.values():
            if n["kind"] == "input":
                return n["id"] == node["id"]
        return False

    @staticmethod
    def _topological_order(nodes: dict, edges: list[dict]) -> list[str]:
        indegree = {nid: 0 for nid in nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in nodes}
        for edge in edges:
            adjacency[edge["source"]].append(edge["target"])
            indegree[edge["target"]] += 1

        queue = [nid for nid, deg in indegree.items() if deg == 0]
        order: list[str] = []
        while queue:
            queue.sort()  # deterministic
            nid = queue.pop(0)
            order.append(nid)
            for nxt in adjacency[nid]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if len(order) != len(nodes):
            raise BlueprintExecutionError("Blueprint contains a cycle")
        return order
