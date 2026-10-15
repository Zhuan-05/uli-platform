import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  Handle,
  Position,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import type { Blueprint, CapabilityDescriptor } from "./api";
import { api } from "./api";

interface UliData extends Record<string, unknown> {
  kind: "input" | "capability" | "output";
  label: string;
  capability?: string;
  appId?: string;
  outputType?: string;
  inputType?: string;
  contract?: string;
}

type UliNode = Node<UliData>;

function UliNodeView({ data }: NodeProps) {
  const d = data as UliData;
  return (
    <div className={`uli-node uli-node-${d.kind}`}>
      {d.kind !== "input" && <Handle type="target" position={Position.Left} />}
      <div className="uli-node-kind">{d.kind}</div>
      <div className="uli-node-title">{d.label}</div>
      {d.contract && <div className="uli-node-contract">{d.contract}</div>}
      {d.kind !== "output" && <Handle type="source" position={Position.Right} />}
    </div>
  );
}

const nodeTypes = { uli: UliNodeView };

const EXAMPLE_INPUT = JSON.stringify(
  { customer: "Ada Lovelace", items: [{ sku: "SKU-001", quantity: 2 }] },
  null,
  2
);

interface Props {
  capabilities: CapabilityDescriptor[];
  blueprintToLoad: Blueprint | null;
  onSaved: () => void;
  onError: (msg: string) => void;
}

export default function Builder({ capabilities, blueprintToLoad, onSaved, onError }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<UliNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [bpId, setBpId] = useState("uli.blueprint.new");
  const [bpName, setBpName] = useState("New Blueprint");
  const [status, setStatus] = useState<string>("");
  const [execInput, setExecInput] = useState(EXAMPLE_INPUT);
  const [execResult, setExecResult] = useState<string>("");
  const counter = useRef(0);

  const capIndex = useMemo(() => {
    const m = new Map<string, CapabilityDescriptor>();
    for (const c of capabilities) if (!m.has(c.id)) m.set(c.id, c);
    return m;
  }, [capabilities]);

  const contractIn = useCallback(
    (node: UliNode | undefined): string => {
      if (!node) return "*";
      const d = node.data;
      if (d.kind === "output") return d.inputType || "*";
      if (d.kind === "capability") return capIndex.get(d.capability || "")?.inputType || "*";
      return "*";
    },
    [capIndex]
  );

  const contractOut = useCallback(
    (node: UliNode | undefined): string => {
      if (!node) return "*";
      const d = node.data;
      if (d.kind === "input") return d.outputType || "*";
      if (d.kind === "capability") return capIndex.get(d.capability || "")?.outputType || "*";
      return "*";
    },
    [capIndex]
  );

  const onConnect = useCallback(
    (conn: Connection) => {
      const src = nodes.find((n) => n.id === conn.source);
      const tgt = nodes.find((n) => n.id === conn.target);
      const a = contractOut(src);
      const b = contractIn(tgt);
      if (!(a === "*" || b === "*" || a === b)) {
        setStatus(`❌ Rejected: output ${a} cannot connect to input ${b}`);
        onError(`Incompatible connection: ${a} → ${b}`);
        return;
      }
      setEdges((eds) => addEdge(conn, eds));
      setStatus(`✅ Connected ${a} → ${b}`);
    },
    [nodes, contractOut, contractIn, setEdges, onError]
  );

  const addCapabilityNode = (cap: CapabilityDescriptor) => {
    counter.current += 1;
    const id = `cap_${counter.current}`;
    setNodes((ns) => [
      ...ns,
      {
        id,
        type: "uli",
        position: { x: 320 + (ns.length % 3) * 240, y: 120 + Math.floor(ns.length / 3) * 140 },
        data: {
          kind: "capability",
          label: cap.id,
          capability: cap.id,
          appId: cap.appId,
          contract: `${cap.inputType} → ${cap.outputType}`,
        },
      },
    ]);
  };

  const addNode = (kind: "input" | "output") => {
    counter.current += 1;
    const id = `${kind}_${counter.current}`;
    setNodes((ns) => [
      ...ns,
      {
        id,
        type: "uli",
        position: { x: kind === "input" ? 80 : 780, y: 200 },
        data: {
          kind,
          label: kind === "input" ? "Request" : "Result",
          outputType: "*",
          inputType: "*",
          contract: kind === "input" ? "source" : "sink",
        },
      },
    ]);
  };

  useEffect(() => {
    if (!blueprintToLoad) return;
    setBpId(blueprintToLoad.id);
    setBpName(blueprintToLoad.name);
    setNodes(
      blueprintToLoad.nodes.map((n, i) => {
        const cap = n.capability ? capIndex.get(n.capability) : undefined;
        return {
          id: n.id,
          type: "uli",
          position: n.position ?? { x: 120 + i * 220, y: 160 },
          data: {
            kind: n.kind,
            label: n.label || n.capability || n.kind,
            capability: n.capability,
            appId: n.appId,
            outputType: n.outputType || cap?.outputType || "*",
            inputType: n.inputType || cap?.inputType || "*",
            contract: n.capability
              ? `${cap?.inputType ?? "?"} → ${cap?.outputType ?? "?"}`
              : undefined,
          },
        } as UliNode;
      })
    );
    setEdges(
      blueprintToLoad.edges.map((e) => ({ id: e.id, source: e.source, target: e.target }))
    );
    setStatus(`Loaded ${blueprintToLoad.id}`);
  }, [blueprintToLoad, capIndex, setNodes, setEdges]);

  const toBlueprint = (): Blueprint => ({
    blueprintVersion: "1.0",
    id: bpId,
    name: bpName,
    version: "1.0.0",
    nodes: nodes.map((n) => {
      const d = n.data as UliData;
      return {
        id: n.id,
        kind: d.kind,
        label: d.label,
        position: n.position,
        capability: d.capability,
        appId: d.appId,
        inputType: d.inputType,
        outputType: d.outputType,
      };
    }),
    edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
  });

  const save = async () => {
    try {
      await api.saveBlueprint(toBlueprint());
      setStatus(`Saved ${bpId}`);
      onSaved();
    } catch (e) {
      onError(String(e));
    }
  };

  const validate = async () => {
    try {
      const report = await api.validateBlueprint(toBlueprint());
      setStatus(
        report.valid
          ? "✅ Blueprint is valid and executable"
          : "❌ " + report.issues.filter((i) => !i.ok).map((i) => i.reason).join("; ")
      );
    } catch (e) {
      onError(String(e));
    }
  };

  const execute = async () => {
    try {
      await api.saveBlueprint(toBlueprint());
      let input: Record<string, unknown> = {};
      try {
        input = execInput.trim() ? JSON.parse(execInput) : {};
      } catch {
        onError("Execution input is not valid JSON");
        return;
      }
      const started = Date.now();
      const result = await api.executeBlueprint(bpId, input);
      setExecResult(JSON.stringify(result, null, 2));
      setStatus(`✅ Executed in ${Date.now() - started}ms`);
    } catch (e) {
      onError(String(e));
      setStatus("❌ " + String(e));
    }
  };

  const loadExample = () => {
    setNodes([
      {
        id: "request",
        type: "uli",
        position: { x: 40, y: 160 },
        data: { kind: "input", label: "Order request", outputType: "uli.order.create.request@1", contract: "source" },
      },
      {
        id: "create",
        type: "uli",
        position: { x: 340, y: 160 },
        data: {
          kind: "capability",
          label: "order.create",
          capability: "order.create",
          contract: "uli.order.create.request@1 → uli.order.create.response@1",
        },
      },
      {
        id: "result",
        type: "uli",
        position: { x: 700, y: 160 },
        data: { kind: "output", label: "Order result", inputType: "*", contract: "sink" },
      },
    ]);
    setEdges([
      { id: "e1", source: "request", target: "create" },
      { id: "e2", source: "create", target: "result" },
    ]);
    setBpId("uli.blueprint.order-demo");
    setBpName("Order pipeline");
    setStatus("Loaded example: Order → Inventory (order.create internally calls inventory.check)");
  };

  return (
    <div className="builder">
      <div className="builder-palette">
        <h3>Apps &amp; Capabilities</h3>
        <button className="btn ghost" onClick={() => addNode("input")}>+ Request node</button>
        <button className="btn ghost" onClick={() => addNode("output")}>+ Result node</button>
        <button className="btn ghost" onClick={loadExample}>Load example flow</button>
        <div className="palette-list">
          {capabilities.map((c) => (
            <button
              key={c.appId + c.id}
              className="palette-item"
              onClick={() => addCapabilityNode(c)}
              title={`${c.inputType} → ${c.outputType}`}
            >
              <span className="palette-cap">{c.id}</span>
              <span className="palette-app">{c.appName}</span>
            </button>
          ))}
          {capabilities.length === 0 && <p className="muted">No capabilities registered yet.</p>}
        </div>
      </div>

      <div className="builder-canvas">
        <div className="builder-toolbar">
          <input value={bpId} onChange={(e) => setBpId(e.target.value)} placeholder="blueprint id" />
          <input value={bpName} onChange={(e) => setBpName(e.target.value)} placeholder="name" />
          <button className="btn" onClick={save}>Save</button>
          <button className="btn ghost" onClick={validate}>Validate</button>
          <button className="btn accent" onClick={execute}>Execute</button>
        </div>
        {status && <div className="builder-status">{status}</div>}
        <div className="flow-wrap">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
          >
            <Background gap={24} />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </div>
      </div>

      <div className="builder-inspector">
        <h3>Execute</h3>
        <label className="muted">Input JSON (overrides Request node sample)</label>
        <textarea value={execInput} onChange={(e) => setExecInput(e.target.value)} rows={8} />
        <h3>Result</h3>
        <pre className="result-box">{execResult || "(not executed yet)"}</pre>
      </div>
    </div>
  );
}
