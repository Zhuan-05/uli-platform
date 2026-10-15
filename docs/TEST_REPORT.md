# Test Report — ULI Platform MVP

All results below are **actual**, produced by running the suite in this
repository. Nothing here is aspirational.

## Environment

| Item | Value |
|---|---|
| OS | Linux (WSL2), kernel 6.18 |
| Python | 3.14.4 (isolated venv) |
| Node / npm | 26.5.0 / 12.0.2 |
| FastAPI / Starlette | 0.143.2 / 1.8.0 |
| Pydantic | 2.14.1 |
| jsonschema | 4.26.0 |
| pytest | 9.1.1 |
| Vite / @xyflow/react | 8.3.4 / 12.12.0 |

## Command

```bash
~/.venvs/uli-platform/bin/python -m pytest tests -v
```

## Result

```
======================== 35 passed, 1 warning in 5.87s =========================
```

The single warning is a Starlette deprecation notice about `httpx` in its
`TestClient` shim; it does not affect behavior.

## Acceptance-criteria coverage

| # | Required test | Test(s) | Result |
|---|---|---|---|
| 1 | Valid application registration | `test_manifest.py::test_valid_manifest_parses`, `test_registration_via_api` | ✅ |
| 2 | Invalid manifest rejection | `test_manifest.py::test_invalid_manifests_rejected[5 cases]`, `test_protocol_range_rejected_at_registration` | ✅ |
| 3 | Static website import and serving | `test_static_import.py::test_import_static_website_and_serve` | ✅ |
| 4 | Application lifecycle operations | `test_lifecycle.py::test_lifecycle_operations` | ✅ |
| 5 | Capability discovery | `test_capabilities.py::test_capability_discovery` | ✅ |
| 6 | Compatible interface connection | `test_capabilities.py::test_connection_compatibility`, `test_validate_connection_api` | ✅ |
| 7 | Incompatible interface rejection | `test_capabilities.py::test_validate_connection_api`, `test_blueprints.py::test_incompatible_connection_rejected` | ✅ |
| 8 | Input/output schema validation | `test_capabilities.py::test_invoke_and_schema_validation`, `test_events.py::test_versioned_event_schema_validation` | ✅ |
| 9 | Event dispatch | `test_events.py::test_event_dispatch_to_subscriber`, `test_event_log_persisted` | ✅ |
| 10 | Order-to-Inventory communication | `test_end_to_end.py::test_order_to_inventory_cross_application_flow` | ✅ |
| 11 | Independent application removal | `test_lifecycle.py::test_uninstall_preserves_data_and_removes_registration` | ✅ |
| 12 | Version compatibility checks | `test_version.py::test_ranges`, `test_capabilities.py::test_version_incompatibility_blocks_enable` | ✅ |
| 13 | Blueprint save/load | `test_blueprints.py::test_blueprint_save_load_and_execute` | ✅ |
| 14 | Local port conflict handling | `test_local_runtime.py::test_port_conflict_falls_back_to_free_port` | ✅ |
| 15 | Safe handling of failed startup | `test_local_runtime.py::test_failed_startup_missing_entry_is_handled` | ✅ |
| + | Frontend-to-backend integration | `test_frontend.py::test_ui_is_served_when_built`, `test_end_to_end.py::test_blueprint_executes_real_order_workflow` | ✅ |

Additional security tests:
`test_lifecycle.py::test_in_process_runtime_cannot_be_registered_publicly`,
`test_local_runtime.py::test_untrusted_local_python_is_refused`,
`test_events.py::test_publish_permission_enforced`.

## What the end-to-end test proves

`test_order_to_inventory_cross_application_flow` boots a **real** ULI Core under
uvicorn and drives it over HTTP:

1. Starts the Inventory App (separate OS process) and the Order App (separate OS
   process).
2. Invokes `order.create` on the Order App.
3. The Order App calls **back into Core** to run `inventory.check`.
4. Core routes the call to the Inventory App, which returns real stock data.
5. The Order App returns `confirmed` / `backorder` based on that data.
6. Core's event log contains `uli.capability.invoked` and `order.created`.

`test_blueprint_executes_real_order_workflow` saves a Blueprint and executes it,
producing a real order whose availability came from the Inventory App.

## Reproduce from scratch

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests -v
```
