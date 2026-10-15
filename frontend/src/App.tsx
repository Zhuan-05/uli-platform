import { useCallback, useEffect, useState } from "react";
import { api, type AppSummary, type Blueprint, type CapabilityDescriptor } from "./api";
import { applyTheme } from "./theme";
import Builder from "./Builder";

type View = "apps" | "capabilities" | "builder" | "blueprints" | "themes" | "activity";

const STATE_CLASS: Record<string, string> = {
  running: "pill ok",
  enabled: "pill info",
  registered: "pill",
  stopped: "pill warn",
  disabled: "pill",
  error: "pill danger",
  incompatible: "pill danger",
  starting: "pill warn",
};

export default function App() {
  const [view, setView] = useState<View>("apps");
  const [apps, setApps] = useState<AppSummary[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityDescriptor[]>([]);
  const [themes, setThemes] = useState<any[]>([]);
  const [activeTheme, setActiveTheme] = useState<string>("");
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [blueprintToLoad, setBlueprintToLoad] = useState<Blueprint | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [guarantees, setGuarantees] = useState<any>(null);
  const [toast, setToast] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<any>(null);
  const [importPath, setImportPath] = useState("");
  const [importName, setImportName] = useState("");
  const [externalName, setExternalName] = useState("");
  const [externalUrl, setExternalUrl] = useState("");

  const notify = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(""), 5000);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, a, c, t, b] = await Promise.all([
        api.health(),
        api.listApps(),
        api.listCapabilities(),
        api.listThemes(),
        api.listBlueprints(),
      ]);
      setHealth(h);
      setApps(a);
      setCapabilities(c);
      setThemes(t.themes);
      setActiveTheme(t.active);
      setBlueprints(b);
    } catch (e) {
      notify("Failed to load platform state: " + e);
    }
  }, [notify]);

  useEffect(() => {
    refresh();
    api.guarantees().then(setGuarantees).catch(() => {});
  }, [refresh]);

  useEffect(() => {
    if (!activeTheme) return;
    api.getTheme(activeTheme).then(applyTheme).catch(() => {});
  }, [activeTheme]);

  useEffect(() => {
    if (view === "activity") api.events(80).then(setEvents).catch(() => {});
  }, [view]);

  const run = async (op: () => Promise<any>, success: string) => {
    setBusy(true);
    try {
      await op();
      notify(success);
      await refresh();
    } catch (e) {
      notify("⚠️ " + String(e));
    } finally {
      setBusy(false);
    }
  };

  const loadBlueprint = async (id: string) => {
    try {
      const bp = await api.getBlueprint(id);
      setBlueprintToLoad(bp);
      setView("builder");
    } catch (e) {
      notify(String(e));
    }
  };

  const activateTheme = async (id: string) => {
    try {
      const res = await api.activateTheme(id);
      setActiveTheme(res.theme.id);
      notify(`Theme switched to ${res.theme.name}`);
    } catch (e) {
      notify(String(e));
    }
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">ULI</div>
          <div>
            <div className="brand-title">Universal LEGO Interface</div>
            <div className="brand-sub">v1.0 · {health?.protocolVersion ?? "…"}</div>
          </div>
        </div>
        <nav>
          {(
            [
              ["apps", "Applications"],
              ["capabilities", "Capabilities"],
              ["builder", "Visual Builder"],
              ["blueprints", "Blueprints"],
              ["themes", "Themes"],
              ["activity", "Activity"],
            ] as [View, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              className={`nav-item ${view === key ? "active" : ""}`}
              onClick={() => setView(key)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="stat">
            <span>{health?.applications ?? 0}</span> apps
          </div>
          <div className="stat">
            <span>{health?.running ?? 0}</span> running
          </div>
          <div className="stat">
            <span>{health?.capabilities ?? 0}</span> capabilities
          </div>
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <h1>{view.charAt(0).toUpperCase() + view.slice(1)}</h1>
          <div className="topbar-actions">
            <button className="btn ghost" onClick={() => refresh()}>
              Refresh
            </button>
          </div>
        </header>

        {view === "apps" && (
          <section className="stack">
            <div className="grid-cards">
              {apps.map((app) => (
                <div className="card app-card" key={app.id}>
                  <div className="card-head">
                    <div>
                      <h3>{app.name}</h3>
                      <code className="muted">{app.id}</code>
                    </div>
                    <span className={STATE_CLASS[app.state] ?? "pill"}>{app.state}</span>
                  </div>
                  <p className="muted small">{app.description || app.runtimeType}</p>
                  <div className="chips">
                    <span className="chip">{app.runtimeType}</span>
                    <span className="chip">{app.trust}</span>
                    {app.port ? <span className="chip">:{app.port}</span> : null}
                    {app.isBuiltin ? <span className="chip accent">built-in</span> : null}
                  </div>
                  {app.lastError && <div className="error-text">{app.lastError}</div>}
                  <div className="row wrap">
                    {app.state !== "running" ? (
                      <button className="btn accent" disabled={busy} onClick={() => run(() => api.start(app.id), `Started ${app.name}`)}>
                        Start
                      </button>
                    ) : (
                      <button className="btn" disabled={busy} onClick={() => run(() => api.stop(app.id), `Stopped ${app.name}`)}>
                        Stop
                      </button>
                    )}
                    <button className="btn ghost" disabled={busy} onClick={() => run(() => api.enable(app.id), `Enabled ${app.name}`)}>
                      Enable
                    </button>
                    <button className="btn ghost" disabled={busy} onClick={() => run(() => api.disable(app.id), `Disabled ${app.name}`)}>
                      Disable
                    </button>
                    <button className="btn ghost" onClick={() => api.getApp(app.id).then(setSelected)}>
                      Details
                    </button>
                    <a className="btn ghost" href={app.runtimeType === "external-url" && app.url ? app.url : `/host/${app.id}/`} target="_blank" rel="noreferrer">
                      Open
                    </a>
                    <button className="btn danger" disabled={busy} onClick={() => run(() => api.uninstall(app.id), `Removed ${app.name} (data preserved)`)}>
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="card">
              <h3>Import a prebuilt static website</h3>
              <p className="muted small">
                Copies the folder unchanged and generates a manifest. Source is never rewritten; deep
                integration needs an Adapter.
              </p>
              <div className="row wrap">
                <input placeholder="Display name" value={importName} onChange={(e) => setImportName(e.target.value)} />
                <input placeholder="Server-side folder path" value={importPath} onChange={(e) => setImportPath(e.target.value)} />
                <button
                  className="btn accent"
                  disabled={busy || !importName || !importPath}
                  onClick={() => run(() => api.importStatic(importName, importPath), `Imported ${importName}`)}
                >
                  Import folder
                </button>
              </div>
            </div>

            <div className="card">
              <h3>Register an external web app</h3>
              <div className="row wrap">
                <input placeholder="Display name" value={externalName} onChange={(e) => setExternalName(e.target.value)} />
                <input placeholder="https://example.com" value={externalUrl} onChange={(e) => setExternalUrl(e.target.value)} />
                <button
                  className="btn"
                  disabled={busy || !externalName || !externalUrl}
                  onClick={() => run(() => api.registerExternal(externalName, externalUrl), `Registered ${externalName}`)}
                >
                  Register URL
                </button>
              </div>
            </div>
          </section>
        )}

        {view === "capabilities" && (
          <section className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>Capability</th>
                  <th>Version</th>
                  <th>Provider</th>
                  <th>Input contract</th>
                  <th>Output contract</th>
                </tr>
              </thead>
              <tbody>
                {capabilities.map((c) => (
                  <tr key={c.appId + c.id}>
                    <td><strong>{c.id}</strong></td>
                    <td>{c.version}</td>
                    <td>{c.appName} <span className={STATE_CLASS[c.appState] ?? "pill"}>{c.appState}</span></td>
                    <td><code>{c.inputType}</code></td>
                    <td><code>{c.outputType}</code></td>
                  </tr>
                ))}
                {capabilities.length === 0 && (
                  <tr><td colSpan={5} className="muted">No capabilities yet. Start an application to publish them.</td></tr>
                )}
              </tbody>
            </table>
          </section>
        )}

        {view === "builder" && (
          <Builder
            capabilities={capabilities}
            blueprintToLoad={blueprintToLoad}
            onSaved={refresh}
            onError={notify}
          />
        )}

        {view === "blueprints" && (
          <section className="stack">
            <div className="grid-cards">
              {blueprints.map((bp) => (
                <div className="card" key={bp.id}>
                  <h3>{bp.name}</h3>
                  <code className="muted">{bp.id}</code>
                  <p className="muted small">
                    {bp.nodes.length} nodes · {bp.edges.length} connections
                  </p>
                  <div className="row wrap">
                    <button className="btn accent" onClick={() => loadBlueprint(bp.id)}>Open</button>
                    <button className="btn ghost" onClick={() => api.executeBlueprint(bp.id, {}).then((r) => notify("Executed: " + JSON.stringify(r.result).slice(0, 120))).catch((e) => notify(String(e)))}>
                      Execute
                    </button>
                    <button className="btn danger" onClick={() => run(() => api.deleteBlueprint(bp.id), "Deleted blueprint")}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {blueprints.length === 0 && <p className="muted">No saved blueprints yet. Build one in the Visual Builder.</p>}
            </div>
          </section>
        )}

        {view === "themes" && (
          <section className="stack">
            <div className="grid-cards">
              {themes.map((t) => (
                <div className={`card theme-card ${t.id === activeTheme ? "selected" : ""}`} key={t.id}>
                  <h3>{t.name}</h3>
                  <p className="muted small">{t.mode} · {t.builtin ? "built-in" : "imported"}</p>
                  <button className="btn" onClick={() => activateTheme(t.id)} disabled={t.id === activeTheme}>
                    {t.id === activeTheme ? "Active" : "Activate"}
                  </button>
                </div>
              ))}
            </div>
            {guarantees && (
              <div className="card">
                <h3>Compatibility guarantees</h3>
                <div className="two-col">
                  <div>
                    <h4 className="ok-text">Enforceable by the platform</h4>
                    <ul>{guarantees.enforceable.map((g: string) => <li key={g}>{g}</li>)}</ul>
                  </div>
                  <div>
                    <h4 className="warn-text">Requires developer cooperation</h4>
                    <ul>{guarantees.requires_developer_cooperation.map((g: string) => <li key={g}>{g}</li>)}</ul>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {view === "activity" && (
          <section className="card">
            <table className="table">
              <thead>
                <tr><th>Time</th><th>Event</th><th>Version</th><th>Source</th><th>Payload</th></tr>
              </thead>
              <tbody>
                {events.map((e, i) => (
                  <tr key={i}>
                    <td className="muted small">{e.timestamp}</td>
                    <td><strong>{e.name}</strong></td>
                    <td>{e.version}</td>
                    <td>{e.source}</td>
                    <td><code className="small">{JSON.stringify(e.payload)}</code></td>
                  </tr>
                ))}
                {events.length === 0 && <tr><td colSpan={5} className="muted">No events recorded yet.</td></tr>}
              </tbody>
            </table>
          </section>
        )}

        {selected && (
          <div className="modal-backdrop" onClick={() => setSelected(null)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="card-head">
                <h3>{selected.name} manifest</h3>
                <button className="btn ghost" onClick={() => setSelected(null)}>Close</button>
              </div>
              <pre className="result-box">{JSON.stringify(selected.manifest, null, 2)}</pre>
            </div>
          </div>
        )}
      </main>

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
