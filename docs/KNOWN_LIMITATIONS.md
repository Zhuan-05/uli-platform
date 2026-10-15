# Known Limitations (MVP)

These are deliberate, documented boundaries — not hidden defects. Where a feature
could not be implemented safely, it was disabled rather than approximated
insecurely.

## Security & isolation

1. **`local-python` is process isolation, not a sandbox.** A trusted app runs as
   the same OS user and can access anything that user can. Only register
   reviewed code as `trusted`.
2. **`in-process` runtime is not sandboxed at all** and is refused through the
   public registration API; it exists for Core-internal providers and tests.
3. **No authentication on the Core HTTP API.** It binds to `127.0.0.1` only.
   Do not expose it to a network without adding auth/TLS (future work).
4. **Bearer tokens are per-run and in-memory.** They are not persisted and are
   regenerated on each start. If Core restarts, previously spawned children are
   untracked (see #9).

## Compatibility

5. **Hosting ≠ functional integration.** Imported websites can be served as-is.
   They do not automatically gain capabilities, events, or theme support.
6. **No structural JSON-Schema subtyping.** Ports connect only on identical
   contract identifiers (or `*`). Translation requires an Adapter.
7. **External embedding is subject to the remote server** (`X-Frame-Options`,
   `CSP frame-ancestors`, cookies). ULI reports feasibility but cannot override
   browsers.
8. **Theme inheritance is opt-in for native apps and impossible for imported
   sites.** Third-party sites are not restyled.

## Runtime & operations

9. **Process tracking is in-memory.** If ULI Core is killed ungracefully,
   spawned child processes may be orphaned and are no longer tracked. Restart the
   platform and stop them via the OS if needed.
10. **`local-node`, server, and container runtimes are extension points only.**
    They are documented but not implemented.
11. **Single Core instance.** No clustering, multi-tenancy, or distributed
    event delivery.
12. **No OS service / auto-start.** Launch manually via the scripts.
13. **SQLite is the only store.** Fine for local use, not for concurrent
    multi-writer scale-out.
14. **No per-app resource limits** (CPU/memory). A runaway trusted app affects
    the machine.

## Functional scope

15. **Blueprint execution is linear/DAG-based.** Cycles are rejected. There is no
    branching, mapping, retry, or compensation logic yet.
16. **Upgrades do not migrate application data.** Major-version data migration is
    the application's responsibility.
17. **Uninstall does not remove application-owned external data** unless the app
    provides that behavior; platform-imported source deletion is explicit opt-in.
18. **Secrets** are not stored by the platform. `config.fields` of type `secret`
    are a declaration only; wiring a secret store is future work.
19. **Windows scripts were not executed on Windows** during this build (authored
    and validated in WSL2). The manual commands are the fallback.
20. **No public marketplace, licensing, Kubernetes, or advanced container
    orchestration.** Explicitly out of MVP scope.
