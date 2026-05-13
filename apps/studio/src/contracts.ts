export type ModelProvider = "codex" | "claude" | "gemini";

export type RunStatus = "idle" | "needs_approval" | "running" | "completed" | "failed";

export interface StudioWorkspaceContext {
  workspaceRoot: string;
  selectedCasePath: string;
  visibleCommands: string[];
  diagnosticsArtifactPath: string;
  reportPath: string;
  manifestPath: string;
  logPath: string;
}

export interface StudioChatRequest {
  requestText: string;
  workspace: StudioWorkspaceContext;
  selectedProvider: ModelProvider;
  localOnly: true;
  approvalRequired: true;
  source: "studio.chat";
}

export interface StudioChatRequestInput {
  requestText: string;
  workspaceRoot: string;
  selectedCasePath?: string;
  selectedProvider: ModelProvider;
  visibleCommands?: string[];
  diagnosticsArtifactPath?: string;
  reportPath?: string;
  manifestPath?: string;
  logPath?: string;
}

export interface StudioDiagnosticState {
  code: string;
  status: "PASS" | "WARN" | "FAIL" | "PENDING";
  message: string;
}

export interface StudioApprovalPrompt {
  code: string;
  message: string;
  required: true;
}

export interface StudioNextAction {
  id: string;
  label: string;
  status: "available" | "blocked" | "needs_approval";
}

export interface StudioRuntimeState {
  workspaceRoot: string;
  selectedCasePath: string;
  runStatus: RunStatus;
  visibleCommands: string[];
  diagnostics: StudioDiagnosticState[];
  diagnosticsArtifactPath: string;
  reportPath: string;
  manifestPath: string;
  logPath: string;
  approvalPrompts: StudioApprovalPrompt[];
  nextActions: StudioNextAction[];
  validationErrors: string[];
  clarifyingQuestions: string[];
  localOnly: true;
}

export function buildStudioChatRequest(input: StudioChatRequestInput): StudioChatRequest {
  const requestText = input.requestText.trim();
  if (requestText.length === 0) {
    throw new Error("requestText is required");
  }

  return {
    requestText,
    workspace: {
      workspaceRoot: input.workspaceRoot,
      selectedCasePath: input.selectedCasePath ?? "./examples/cavity",
      visibleCommands: input.visibleCommands ?? [],
      diagnosticsArtifactPath: input.diagnosticsArtifactPath ?? "diagnostics.json",
      reportPath: input.reportPath ?? "report.md",
      manifestPath: input.manifestPath ?? "manifest.json",
      logPath: input.logPath ?? "log.simpleFoam",
    },
    selectedProvider: input.selectedProvider,
    localOnly: true,
    approvalRequired: true,
    source: "studio.chat",
  };
}

export const defaultRuntimeState: StudioRuntimeState = {
  workspaceRoot: ".",
  selectedCasePath: "./examples/cavity",
  runStatus: "needs_approval",
  visibleCommands: [
    "opennavier doctor ./examples/cavity --diagnostics-output diagnostics.json",
    "opennavier report ./examples/cavity --output report.md --manifest-output manifest.json",
    "blockMesh -case ./examples/cavity",
    "simpleFoam -case ./examples/cavity",
  ],
  diagnostics: [
    {
      code: "openfoam.required_directory.system",
      status: "PASS",
      message: "Case structure is ready.",
    },
    {
      code: "openfoam.mesh_quality.incomplete",
      status: "PENDING",
      message: "Mesh-quality evidence is pending.",
    },
  ],
  diagnosticsArtifactPath: "diagnostics.json",
  reportPath: "report.md",
  manifestPath: "manifest.json",
  logPath: "log.simpleFoam",
  approvalPrompts: [
    {
      code: "approve_solver_execution",
      message: "Explicit approval required before writes or reruns",
      required: true,
    },
  ],
  nextActions: [
    {
      id: "review-plan",
      label: "Review plan artifact",
      status: "available",
    },
    {
      id: "approve-run",
      label: "Approve local solver command",
      status: "needs_approval",
    },
  ],
  validationErrors: [],
  clarifyingQuestions: ["Confirm whether the objective is convergence_check or pressure_drop."],
  localOnly: true,
};
