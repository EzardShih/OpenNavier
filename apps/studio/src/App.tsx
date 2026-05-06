const commands = [
  "opennavier doctor ./examples/cavity",
  "opennavier report ./examples/cavity --output report.md",
  "blockMesh -case ./examples/cavity",
  "simpleFoam -case ./examples/cavity",
];

const caseFiles = ["blockMeshDict", "controlDict", "fvSchemes", "fvSolution"];

const assumptions = [
  "Local OpenFOAM command execution only",
  "Case paths stay on this workstation",
  "Reports include reproducibility manifests",
  "Diagnostics must be inspectable before run actions",
];

const checks = [
  { label: "Case structure", state: "Pass" },
  { label: "Dictionary headers", state: "Pass" },
  { label: "Optional solver logs", state: "Warn" },
  { label: "Mesh quality", state: "Pending" },
];

function App() {
  return (
    <main className="studio-shell">
      <aside className="project-rail" aria-label="Project navigation">
        <div>
          <p className="eyebrow">OpenNavier Studio</p>
          <h1>Project Dashboard</h1>
          <p className="local-note">Local-first, engineer-verifiable CFD workspace. No cloud upload.</p>
        </div>
        <nav>
          <a href="#run-monitor">Run Monitor</a>
          <a href="#diagnostics">Diagnostics</a>
          <a href="#report-viewer">Report Viewer</a>
        </nav>
      </aside>

      <section className="workbench" aria-label="OpenNavier Studio workbench">
        <section className="status-strip" aria-label="Check Status">
          <h2>Check Status</h2>
          <div className="checks">
            {checks.map((check) => (
              <span className={`check check-${check.state.toLowerCase()}`} key={check.label}>
                {check.label}: {check.state}
              </span>
            ))}
          </div>
        </section>

        <section className="panel-grid">
          <article className="panel" id="run-monitor">
            <h2>Run Monitor</h2>
            <p>Local OpenFOAM command queue with visible inputs, states, and outputs.</p>
            <ol className="command-list" aria-label="Visible Commands">
              {commands.map((command) => (
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
              <strong>report.md</strong>
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
        </section>
      </section>
    </main>
  );
}

export default App;
