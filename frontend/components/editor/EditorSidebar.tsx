import React from "react";
import dynamic from "next/dynamic";
import ExtensionsPanel, { ExtensionItem, ExtensionStatus } from "../ExtensionsPanel";

const XIcon = dynamic(() => import("lucide-react").then((m) => m.X));

export interface EditorSidebarProps {
  show: boolean;
  onClose: () => void;
  onTemplateLoad: (filename: string) => void;
  onStartBlank: () => void;
  templates: any[];
  formattingLocked: boolean;
  activeTemplateLabel: string | null;
  onToggleLint: () => void;
  lintEnabled: boolean;
  lintStatus: ExtensionStatus;
  onToggleCollab: () => void;
  collabEnabled: boolean;
  onToggleAiSuggest: () => void;
  aiSuggestEnabled: boolean;
  onToggleHeadingLock: () => void;
  headingLockEnabled: boolean;
  headingLockStatus: ExtensionStatus;
  onToggleIndentation: () => void;
  indentationEnabled: boolean;
  indentationStatus: ExtensionStatus;
  onToggleSectionNode: () => void;
  sectionNodeEnabled: boolean;
  sectionNodeStatus: ExtensionStatus;
  onToggleMarkReview: () => void;
  markReviewEnabled: boolean;
  markReviewStatus: ExtensionStatus;
  onToggleWatermark: () => void;
  watermarkEnabled: boolean;
  watermarkStatus: ExtensionStatus;
  watermarkText: string;
  onWatermarkText: (text: string) => void;
  suggestions: any[];
  acceptSuggestion: (id: number) => void;
  rejectSuggestion: (id: number) => void;
  clearSuggestions: () => void;
  history: any[];
  onRestore: (id: string) => void;
  onCompare: (id: string) => void;
  validationSummary?: { score?: number; grade?: string; issue_count?: number; source?: string } | null;
}

export default function EditorSidebar(props: EditorSidebarProps) {
  const {
    show,
    onClose,
    onTemplateLoad,
    onStartBlank,
    templates,
    formattingLocked,
    activeTemplateLabel,
    onToggleLint,
    lintEnabled,
    lintStatus,
    onToggleCollab,
    collabEnabled,
    onToggleAiSuggest,
    aiSuggestEnabled,
    onToggleHeadingLock,
    headingLockEnabled,
    headingLockStatus,
    onToggleIndentation,
    indentationEnabled,
    indentationStatus,
    onToggleSectionNode,
    sectionNodeEnabled,
    sectionNodeStatus,
    onToggleMarkReview,
    markReviewEnabled,
    markReviewStatus,
    onToggleWatermark,
    watermarkEnabled,
    watermarkStatus,
    watermarkText,
    onWatermarkText,
    suggestions,
    acceptSuggestion,
    rejectSuggestion,
    clearSuggestions,
    history,
    onRestore,
    onCompare,
    validationSummary,
  } = props;

  const extensionItems: ExtensionItem[] = [
    {
      id: "lint",
      label: "Validation (Lint)",
      enabled: lintEnabled,
      status: lintStatus,
      onToggle: onToggleLint,
    },
    {
      id: "heading-lock",
      label: "Heading Lock",
      enabled: headingLockEnabled,
      status: headingLockStatus,
      onToggle: onToggleHeadingLock,
    },
    {
      id: "indentation",
      label: "Indentation",
      enabled: indentationEnabled,
      status: indentationStatus,
      onToggle: onToggleIndentation,
    },
    {
      id: "section-node",
      label: "Section Node",
      enabled: sectionNodeEnabled,
      status: sectionNodeStatus,
      onToggle: onToggleSectionNode,
      seldomUsed: true,
    },
    {
      id: "mark-review",
      label: "Mark Review",
      enabled: markReviewEnabled,
      status: markReviewStatus,
      onToggle: onToggleMarkReview,
      seldomUsed: true,
    },
    {
      id: "watermark",
      label: "Watermark",
      enabled: watermarkEnabled,
      status: watermarkStatus,
      onToggle: onToggleWatermark,
      watermarkText,
      onWatermarkText,
      seldomUsed: true,
    },
  ];

  return (
    <aside
      className={`fixed top-0 right-0 h-full w-80 bg-gray-100 border-l z-50 shadow-lg transform transition-transform duration-200 flex flex-col ${
        show ? "translate-x-0" : "translate-x-full"
      }`}
      style={{ minWidth: "18rem" }}
    >
      <div className="flex-shrink-0 flex justify-between items-center px-4 py-3 border-b bg-white">
        <span className="font-bold text-lg">Tools & Extensions</span>
        <button
          onClick={onClose}
          className="hover:bg-gray-200 rounded p-1"
          aria-label="Close sidebar"
        >
          <XIcon className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-5">
        {/* Templates */}
        <section>
          <div className="font-semibold mb-1">Templates</div>
          <div className="text-xs text-gray-500 mb-2">
            {activeTemplateLabel ? (
              <>
                Active: <span className="font-semibold">{activeTemplateLabel}</span>
                {formattingLocked ? " (formatting locked)" : ""}
              </>
            ) : (
              "Choose a template or start with a blank document."
            )}
          </div>
          <ul className="space-y-1 text-sm">
            <li>
              <button
                className="text-indigo-700 underline"
                onClick={onStartBlank}
              >
                Blank document
              </button>
            </li>
            {templates
              .filter(t => !t.type || t.type === "tiptap" || t.type === "both")
              .map(tpl => (
                <li key={tpl.id || tpl.name}>
                  <button
                    className="text-indigo-700 underline"
                    onClick={() => onTemplateLoad(tpl.id || tpl.name)}
                  >
                    {tpl.label || tpl.name || tpl.id}
                  </button>
                </li>
              ))}
          </ul>
        </section>

        {/* AI Suggest */}
        <section>
          <div className="font-semibold mb-1 flex items-center gap-1">
            AI Suggest
            {/* Optional info icon, if you have one */}
            {/* <InfoIcon className="w-4 h-4 text-blue-500" /> */}
          </div>
          <button
            className={`px-2 py-1 rounded w-full ${
              aiSuggestEnabled ? "bg-blue-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleAiSuggest}
          >
            {aiSuggestEnabled ? "Disable AI Suggest" : "Enable AI Suggest"}
          </button>
          {aiSuggestEnabled && (
            <div className="mt-2 space-y-2">
              <div className="text-xs text-gray-500 mb-1">
                Select text in the editor and press "AI Suggest" in the toolbar
                to get suggestions.
              </div>
              {suggestions.length === 0 ? (
                <div className="text-xs text-gray-400">
                  No AI suggestions yet.
                </div>
              ) : (
                <div className="space-y-2">
                  {suggestions.map((s) => (
                    <div
                      key={s.id}
                      className="border rounded bg-white px-2 py-1 text-sm"
                    >
                      <div className="mb-1 text-xs text-gray-600">
                        For: <em>{s.original.slice(0, 40)}...</em>
                      </div>
                      <div className="mb-2">{s.suggestion}</div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => acceptSuggestion(s.id)}
                          className="px-2 py-1 rounded bg-green-500 text-white text-xs"
                        >
                          Accept
                        </button>
                        <button
                          onClick={() => rejectSuggestion(s.id)}
                          className="px-2 py-1 rounded bg-red-500 text-white text-xs"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                  <button
                    onClick={clearSuggestions}
                    className="mt-2 text-xs underline text-gray-500"
                  >
                    Clear all suggestions
                  </button>
                </div>
              )}
            </div>
          )}
        </section>

        <ExtensionsPanel items={extensionItems} />

        {/* Collaboration */}
        <section>
          <div className="font-semibold mb-1">Collaboration</div>
          <button
            className={`px-2 py-1 rounded w-full ${
              collabEnabled ? "bg-green-500 text-white" : "bg-gray-200"
            }`}
            onClick={onToggleCollab}
          >
            {collabEnabled ? "Disconnect" : "Connect"}
          </button>
        </section>

        {/* Validation Summary */}
        <section>
          <div className="font-semibold mb-1">Validation Summary</div>
          {validationSummary ? (
            <div className="text-sm space-y-1">
              {validationSummary.score != null && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-600">Quality score:</span>
                  <span
                    className={`font-semibold ${
                      validationSummary.score >= 0.8
                        ? "text-green-600"
                        : validationSummary.score >= 0.5
                        ? "text-amber-600"
                        : "text-red-600"
                    }`}
                  >
                    {Math.round(validationSummary.score * 100)}%
                  </span>
                </div>
              )}
              {validationSummary.grade && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-600">Grade level:</span>
                  <span className="font-semibold">{validationSummary.grade}</span>
                </div>
              )}
              {validationSummary.issue_count != null && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-600">Issues found:</span>
                  <span
                    className={`font-semibold ${
                      validationSummary.issue_count === 0 ? "text-green-600" : "text-amber-600"
                    }`}
                  >
                    {validationSummary.issue_count}
                  </span>
                </div>
              )}
              {validationSummary.source && (
                <div className="text-xs text-gray-400">via {validationSummary.source}</div>
              )}
            </div>
          ) : (
            <div className="text-xs text-gray-400">Save the document to run validation.</div>
          )}
        </section>

        {/* History */}
        <section>
          <div className="font-semibold mb-1">History</div>
          <ul className="text-xs text-gray-700 space-y-1">
            {history.map((h: any) => (
              <li key={h.id} className="flex items-center gap-2">
                <button
                  onClick={() => onRestore(h.id)}
                  className="underline"
                >
                  {new Date(h.timestamp).toLocaleString()}
                </button>
                <button
                  onClick={() => onCompare(h.id)}
                  className="underline text-blue-600"
                >
                  Compare
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </aside>
  );
}
