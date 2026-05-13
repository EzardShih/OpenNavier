import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { buildStudioChatRequest, defaultRuntimeState } from "./contracts";
import type { ModelProvider, StudioChatRequest } from "./contracts";

const caseFiles = ["blockMeshDict", "controlDict", "fvSchemes", "fvSolution"];

const studioRuntime = {
  ...defaultRuntimeState,
  visibleCommands: [
    "opennavier doctor ./examples/cavity --diagnostics-output diagnostics.json",
    "opennavier report ./examples/cavity --output report.md --manifest-output manifest.json",
    "blockMesh -case ./examples/cavity",
    "simpleFoam -case ./examples/cavity",
  ],
  diagnosticsArtifactPath: "diagnostics.json",
  reportPath: "report.md",
  manifestPath: "manifest.json",
  approvalPrompts: [
    {
      code: "approve_solver_execution",
      message: "Explicit approval required before writes or reruns",
      required: true,
    },
  ],
};

const assumptions = [
  "Local OpenFOAM command execution only",
  "Case paths stay on this workstation",
  "Reports include reproducibility manifests",
  "Diagnostics must be inspectable before run actions",
];

function App() {
  const [requestText, setRequestText] = useState(
    "Simulate the lid-driven cavity and report whether it converged.",
  );
  const [selectedProvider, setSelectedProvider] = useState<ModelProvider>("codex");
  const [submittedRequest, setSubmittedRequest] = useState<StudioChatRequest | null>(null);
  const [validationError, setValidationError] = useState("");
  const runtime = studioRuntime;
  const validationErrors = useMemo(
    () => (validationError ? [validationError] : runtime.validationErrors),
    [runtime.validationErrors, validationError],
  );

  function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const request = buildStudioChatRequest({
        requestText,
        workspaceRoot: runtime.workspaceRoot,
        selectedCasePath: runtime.selectedCasePath,
        selectedProvider,
        visibleCommands: runtime.visibleCommands,
        diagnosticsArtifactPath: runtime.diagnosticsArtifactPath,
        reportPath: runtime.reportPath,
        manifestPath: runtime.manifestPath,
        logPath: runtime.logPath,
      });
      setSubmittedRequest(request);
      setValidationError("");
    } catch (error) {
      setSubmittedRequest(null);
      setValidationError(error instanceof Error ? error.message : "Request validation failed");
    }
  }

  return (
    <main className="studio-shell">
      <aside className="project-rail" aria-label="Project navigation">
        <div>
          <p className="eyebrow">OpenNavier Studio</p>
          <h1>Project Dashboard</h1>
          <p className="local-note">
            Local-first, engineer-verifiable CFD workspace. No cloud upload.
          </p>
        </div>
        <nav>
          <a href="#engineering-request">Engineering Request</a>
          <a href="#run-monitor">Run Monitor</a>
          <a href="#diagnostics">Diagnostics</a>
          <a href="#report-viewer">Report Viewer</a>
        </nav>
      </aside>

      <section className="workbench" aria-label="OpenNavier Studio workbench">
        <section className="status-strip" aria-label="Check Status">
          <h2>Check Status</h2>
          <div className="checks">
            {runtime.diagnostics.map((check) => (
              <span className={`check check-${check.status.toLowerCase()}`} key={check.code}>
                {check.code}: {check.status}
              </span>
            ))}
          </div>
        </section>

        <section className="panel-grid">
          <article className="panel panel-wide" id="engineering-request">
            <div className="panel-heading">
              <h2>Engineering Request</h2>
              <span className="local-chip">No cloud upload</span>
            </div>
            <form className="request-form" onSubmit={submitRequest}>
              <label>
                Request
                <textarea
                  value={requestText}
                  onChange={(event) => setRequestText(event.currentTarget.value)}
                />
              </label>
              <label>
                Provider
                <select
                  value={selectedProvider}
                  onChange={(event) =>
                    setSelectedProvider(event.currentTarget.value as ModelProvider)
                  }
                >
                  <option value="codex">Codex</option>
                  <option value="claude">Claude</option>
                  <option value="gemini">Gemini</option>
                </select>
              </label>
              <button type="submit">Queue Local Request</button>
            </form>
            <div className="request-evidence" aria-label="Structured Request">
              <strong>Source</strong>
              <code>{submittedRequest?.source ?? "studio.chat"}</code>
              <strong>Workspace</strong>
              <code>{submittedRequest?.workspace.workspaceRoot ?? runtime.workspaceRoot}</code>
              <strong>Provider</strong>
              <code>{submittedRequest?.selectedProvider ?? selectedProvider}</code>
            </div>
          </article>

          <article className="panel" id="run-monitor">
            <div className="panel-heading">
              <h2>Run Monitor</h2>
              <span className="state-chip">{runtime.runStatus}</span>
            </div>
            <dl className="runtime-facts">
              <div>
                <dt>Run Status</dt>
                <dd>{runtime.runStatus}</dd>
              </div>
              <div>
                <dt>Log Path</dt>
                <dd>{runtime.logPath}</dd>
              </div>
            </dl>
            <p>Local OpenFOAM command queue with visible inputs, states, and outputs.</p>
            <ol className="command-list" aria-label="Visible Commands">
              {runtime.visibleCommands.map((command) => (
                <li key={command}>
                  <span>Visible Commands</span>
                  <code>{command}</code>
                </li>
              ))}
            </ol>
          </article>

          <article className="panel" id="diagnostics">
            <h2>Diagnostics</h2>
            <p>Deterministic validation signals before solver work starts.</p>
            <dl className="runtime-facts">
              <div>
                <dt>Artifact</dt>
                <dd>{runtime.diagnosticsArtifactPath}</dd>
              </div>
            </dl>
            <div className="file-grid" aria-label="Case Files">
              {caseFiles.map((fileName) => (
                <span key={fileName}>{fileName}</span>
              ))}
            </div>
          </article>

          <article className="panel" id="report-viewer">
            <h2>Report Viewer</h2>
            <p>Markdown report preview with manifest and diagnostic evidence links.</p>
            <div className="report-frame">
              <strong>{runtime.reportPath}</strong>
              <span>{runtime.manifestPath}</span>
              <span>Residual summary, mesh notes, command history, reproducibility manifest.</span>
            </div>
          </article>

          <article className="panel">
            <h2>Assumptions</h2>
            <ul>
              {assumptions.map((assumption) => (
                <li key={assumption}>{assumption}</li>
              ))}
            </ul>
          </article>

          <article className="panel">
            <h2>Approval Prompts</h2>
            <ul>
              {runtime.approvalPrompts.map((prompt) => (
                <li key={prompt.code}>{prompt.message}</li>
              ))}
            </ul>
          </article>

          <article className="panel">
            <h2>Structured Next Actions</h2>
            <ul>
              {runtime.nextActions.map((action) => (
                <li key={action.id}>
                  {action.label}: {action.status}
                </li>
              ))}
            </ul>
          </article>

          <article className="panel">
            <h2>Validation Errors</h2>
            <ul>
              {(validationErrors.length ? validationErrors : ["None"]).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="panel">
            <h2>Clarifying Questions</h2>
            <ul>
              {runtime.clarifyingQuestions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
          </article>
        </section>
      </section>
    </main>
  );
}

export default App;
