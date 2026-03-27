import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  BookOpen,
  Rocket,
  HelpCircle,
  Code2,
  FolderOpen,
  FileText,
  Repeat,
  Users2,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Keyboard,
  ShieldCheck,
  UserCog,
  Eye,
  CheckSquare,
} from "lucide-react";

// ---------------------------------------------------------------------------
// FAQ data
// ---------------------------------------------------------------------------

const FAQ_ITEMS: Array<{ q: string; a: React.ReactNode }> = [
  {
    q: "How do I create a project?",
    a: (
      <>
        Navigate to <strong>Projects</strong> in the sidebar and click{" "}
        <strong>New Project</strong>. Fill in the project name, document type,
        and workflow template. You can add reviewers and documents after the
        project is created.
      </>
    ),
  },
  {
    q: "How do I upload a document?",
    a: (
      <>
        Open a project, go to the <strong>Documents</strong> tab, and click{" "}
        <strong>Upload Document</strong>. Supported formats include DOCX, PDF,
        Markdown, and plain text. You can also create a new document directly in
        the TipTap editor by clicking <strong>New Document</strong>.
      </>
    ),
  },
  {
    q: "How do I assign reviewers to a project?",
    a: (
      <>
        Open the project and scroll to the <strong>Reviewers</strong> section.
        Use the user-picker search box to find a colleague by username, set an
        optional due date, and click <strong>Invite</strong>. The reviewer
        receives a notification and can start submitting feedback immediately.
      </>
    ),
  },
  {
    q: "What is a workflow phase?",
    a: (
      <>
        Phases represent the sequential stages a document must pass through
        before it is complete — for example, <em>Draft</em>, <em>Review</em>,{" "}
        <em>Approval</em>, and <em>Final</em>. Each phase can have its own set
        of required approvals and reviewers. Admins configure phases under{" "}
        <strong>Configuration &rarr; Phases</strong>.
      </>
    ),
  },
  {
    q: "How do I advance a project to the next phase?",
    a: (
      <>
        In the project view, open the <strong>Overview</strong> tab and click{" "}
        <strong>Advance Phase</strong>. All required approvals for the current
        phase must be complete before the button becomes active. When the phase
        advances, all open feedback is automatically archived for the record.
      </>
    ),
  },
  {
    q: "Where do I find the API reference?",
    a: (
      <>
        The interactive API reference is served directly by the backend at{" "}
        <Link href="/api-docs" className="text-indigo-600 underline">
          /api-docs
        </Link>{" "}
        (FastAPI Swagger UI). You can also access it from the sidebar under{" "}
        <strong>Help &amp; Support &rarr; API Reference</strong>.
      </>
    ),
  },
  {
    q: "How do I reset my password or enable MFA?",
    a: (
      <>
        Click your username in the sidebar to open your <strong>Profile</strong>{" "}
        page. From there you can change your password and enroll a TOTP
        authenticator app (Google Authenticator, Authy, etc.) for multi-factor
        authentication.
      </>
    ),
  },
];

// ---------------------------------------------------------------------------
// Key concepts data
// ---------------------------------------------------------------------------

const CONCEPTS = [
  {
    icon: <FolderOpen className="w-6 h-6 text-indigo-600" />,
    title: "Projects",
    body: `A project is the top-level container for a document review effort.
    It holds documents, reviewers, workflow state, feedback, and the audit
    history. Every project follows a workflow template that defines which
    phases it must pass through.`,
  },
  {
    icon: <FileText className="w-6 h-6 text-blue-600" />,
    title: "Documents",
    body: `Documents are the files under review. They can be uploaded
    (DOCX, PDF, Markdown, TXT) or authored directly in the TipTap
    rich-text editor. Documents support version history, freeze/unfreeze,
    and restore from any prior revision.`,
  },
  {
    icon: <Repeat className="w-6 h-6 text-cyan-600" />,
    title: "Phases",
    body: `Phases are the sequential stages of a workflow (e.g., Draft →
    Review → Approval → Final). Each phase may require specific approvals
    before the project can advance. Admins define phase lists per workflow
    template or per document type.`,
  },
  {
    icon: <Users2 className="w-6 h-6 text-orange-600" />,
    title: "Reviewers",
    body: `Reviewers are colleagues assigned to examine documents in a project.
    Each assignment tracks invitation date, due date, and lifecycle status
    (invited → in-progress → submitted → concurred). Reviewers can submit
    comments, questions, and formal concurrences.`,
  },
  {
    icon: <MessageSquare className="w-6 h-6 text-emerald-600" />,
    title: "Feedback",
    body: `Feedback is the structured record of reviewer input. It includes
    comments, questions answered by the SME, and formal concurrences. Every
    feedback item can be accepted, resolved, or rejected, and all dispositions
    are preserved in the review record for records-retention compliance.`,
  },
];

// ---------------------------------------------------------------------------
// Keyboard shortcuts data
// ---------------------------------------------------------------------------

const SHORTCUTS: Array<{ keys: string[]; desc: string }> = [
  { keys: ["Ctrl", "S"], desc: "Save document (TipTap editor)" },
  { keys: ["Ctrl", "Z"], desc: "Undo last change (editor)" },
  { keys: ["Ctrl", "Shift", "Z"], desc: "Redo (editor)" },
  { keys: ["Ctrl", "B"], desc: "Bold selection (editor)" },
  { keys: ["Ctrl", "I"], desc: "Italic selection (editor)" },
  { keys: ["Ctrl", "K"], desc: "Insert or edit a link (editor)" },
  { keys: ["Ctrl", "/"], desc: "Open command palette (editor)" },
  { keys: ["?"], desc: "Show keyboard shortcuts (this page)" },
];

// ---------------------------------------------------------------------------
// Quick-start steps
// ---------------------------------------------------------------------------

const QUICK_START_STEPS = [
  {
    step: 1,
    title: "Configure your workspace",
    body: "Go to Configuration → Permissions, then Users to set up roles and team members.",
    href: "/configuration",
  },
  {
    step: 2,
    title: "Create a workflow template",
    body: "Under Configuration → Workflows, define the phases documents must pass through.",
    href: "/configuration/workflows",
  },
  {
    step: 3,
    title: "Create a project",
    body: "Click Projects in the sidebar and then New Project. Choose a document type and workflow template.",
    href: "/projects",
  },
  {
    step: 4,
    title: "Upload or create a document",
    body: "Open your project, go to the Documents tab, and upload a file or open the TipTap editor.",
    href: "/projects",
  },
  {
    step: 5,
    title: "Invite reviewers",
    body: "Scroll to the Reviewers section in the project view. Search for team members and set due dates.",
    href: "/projects",
  },
  {
    step: 6,
    title: "Collect feedback and advance phases",
    body: "Monitor the Feedback tab as reviewers submit input. Disposition each item and advance the phase when ready.",
    href: "/projects",
  },
];

// ---------------------------------------------------------------------------
// Role-based guidance data
// ---------------------------------------------------------------------------

const ROLE_SECTIONS: Array<{
  value: string;
  label: string;
  icon: React.ReactNode;
  subtitle: string;
  tasks: string[];
}> = [
  {
    value: "administrator",
    label: "Administrator",
    icon: <ShieldCheck className="w-4 h-4 mr-1.5" />,
    subtitle:
      "Administrators configure the workspace, manage users, and maintain the system.",
    tasks: [
      "Configure role-based permissions under Configuration → Permissions.",
      "Create and manage user accounts via Configuration → User Management.",
      "Define workflow templates and phases that projects will follow.",
      "Set up document types to control which workflow applies to each project.",
      "Connect external integrations such as Documenso or DocuSign for electronic signatures.",
      "Review audit logs and system activity from Configuration → Audit Logs.",
      "Customize branding (logo, product name) under Configuration → Branding.",
    ],
  },
  {
    value: "project-owner",
    label: "Project Owner",
    icon: <UserCog className="w-4 h-4 mr-1.5" />,
    subtitle:
      "Project owners create projects, invite team members, and drive the review process forward.",
    tasks: [
      "Create a project from Projects → New Project; select a document type and workflow template.",
      "Upload or create documents in the project's Documents tab.",
      "Invite reviewers using the Reviewers section and set optional due dates.",
      "Add formal approval rows in the Approvals section for phases that require sign-off.",
      "Monitor the Feedback Ledger to track reviewer input and disposition comments.",
      "Advance the project phase once all required approvals and feedback are addressed.",
      "Download approval summaries and send reminder notifications to pending approvers.",
    ],
  },
  {
    value: "reviewer",
    label: "Reviewer",
    icon: <Eye className="w-4 h-4 mr-1.5" />,
    subtitle:
      "Reviewers examine documents and provide structured feedback for the project owner to address.",
    tasks: [
      "Access your assigned projects from the Projects list or the dashboard.",
      "Open a document and read it in the viewer or TipTap editor.",
      "Submit feedback items (comment, question, suggestion, non-concurrence) from the Feedback tab.",
      "Add anchored comments directly in the TipTap editor to pin notes to specific locations.",
      "Mark a question as satisfied once the project owner has answered it.",
      "Concur with the document — optionally with comments — to record your sign-off.",
      "Respond to disposition decisions made by the project owner on your feedback items.",
    ],
  },
  {
    value: "approver",
    label: "Approver",
    icon: <CheckSquare className="w-4 h-4 mr-1.5" />,
    subtitle:
      "Approvers provide formal sign-off using a configured signature method, creating a legal record.",
    tasks: [
      "You receive a notification when you are added to the Approvals table for a project.",
      "Open the project and navigate to the Approvals section.",
      "Click the Approve button next to your approval row.",
      "Select your signature method: in-app initials, Documenso, or DocuSign (as configured).",
      "Confirm your approval — this creates a cryptographically linked audit record.",
      "Contact the project owner if you need the approval reset due to a document change.",
      "Download your signed approval PDF from the Approvals section for your own records.",
    ],
  },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function FaqItem({ q, a }: { q: string; a: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>{q}</span>
        {open ? (
          <ChevronUp className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
        )}
      </button>
      {open && (
        <div className="px-4 pb-4 pt-2 text-sm text-muted-foreground leading-relaxed border-t border-border">
          {a}
        </div>
      )}
    </div>
  );
}

function KbdKey({ children }: { children: string }) {
  return (
    <kbd className="inline-block rounded bg-muted border border-border px-1.5 py-0.5 text-xs font-mono">
      {children}
    </kbd>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HelpPage() {
  const [activeTab, setActiveTab] = useState("getting-started");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (e.key === "?" && tag !== "INPUT" && tag !== "TEXTAREA") {
        setActiveTab("shortcuts");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="p-8 space-y-6 max-w-5xl">
      {/* Page header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-indigo-600" />
          Help &amp; Documentation
        </h1>
        <p className="text-sm text-muted-foreground">
          Everything you need to get started and make the most of DocReview360.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="getting-started">
            <Rocket className="w-4 h-4 mr-1.5" />
            Getting Started
          </TabsTrigger>
          {ROLE_SECTIONS.map((role) => (
            <TabsTrigger key={role.value} value={role.value}>
              {role.icon}
              {role.label}
            </TabsTrigger>
          ))}
          <TabsTrigger value="concepts">
            <BookOpen className="w-4 h-4 mr-1.5" />
            Key Concepts
          </TabsTrigger>
          <TabsTrigger value="faq">
            <HelpCircle className="w-4 h-4 mr-1.5" />
            FAQ
          </TabsTrigger>
          <TabsTrigger value="shortcuts" id="shortcuts">
            <Keyboard className="w-4 h-4 mr-1.5" />
            Shortcuts
          </TabsTrigger>
          <TabsTrigger value="api">
            <Code2 className="w-4 h-4 mr-1.5" />
            API Reference
          </TabsTrigger>
        </TabsList>

        {/* ---- Getting Started ------------------------------------------ */}
        <TabsContent value="getting-started" id="getting-started" className="mt-6 space-y-4">
          <p className="text-sm text-muted-foreground">
            Follow these steps to set up DocReview360 and complete your first
            document review cycle.
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {QUICK_START_STEPS.map((s) => (
              <Link key={s.step} href={s.href} className="group">
                <Card className="h-full transition-shadow group-hover:shadow-md cursor-pointer">
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-sm font-bold">
                        {s.step}
                      </span>
                      <CardTitle className="text-base font-semibold">{s.title}</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{s.body}</p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          <Card className="bg-indigo-50 dark:bg-indigo-950 border-indigo-200 dark:border-indigo-800">
            <CardContent className="py-4 flex items-start gap-3">
              <HelpCircle className="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-indigo-800 dark:text-indigo-200">
                Need more help? Check the{" "}
                <button
                  type="button"
                  className="underline font-medium"
                  onClick={() => {
                    const el = document.querySelector('[data-value="faq"]') as HTMLElement | null;
                    el?.click();
                  }}
                >
                  FAQ tab
                </button>{" "}
                for answers to common questions, or visit the{" "}
                <Link href="/api-docs" className="underline font-medium">
                  API Reference
                </Link>{" "}
                for integration details.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---- Role-based sections -------------------------------------- */}
        {ROLE_SECTIONS.map((role) => (
          <TabsContent key={role.value} value={role.value} className="mt-6 space-y-4">
            <p className="text-sm text-muted-foreground">{role.subtitle}</p>
            <Card>
              <CardContent className="pt-4">
                <ul className="space-y-2">
                  {role.tasks.map((task, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                      <span className="flex-shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold mt-0.5">
                        {i + 1}
                      </span>
                      <span>{task}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
        ))}

        {/* ---- Key Concepts --------------------------------------------- */}
        <TabsContent value="concepts" className="mt-6 space-y-4">
          <p className="text-sm text-muted-foreground">
            Understanding these core concepts will help you navigate DocReview360
            effectively.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {CONCEPTS.map((c) => (
              <Card key={c.title}>
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  {c.icon}
                  <CardTitle className="text-base font-semibold">{c.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">{c.body}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* ---- FAQ ------------------------------------------------------ */}
        <TabsContent value="faq" className="mt-6 space-y-3">
          <p className="text-sm text-muted-foreground mb-4">
            Frequently asked questions. Click a question to expand the answer.
          </p>
          {FAQ_ITEMS.map((item) => (
            <FaqItem key={item.q} q={item.q} a={item.a} />
          ))}
        </TabsContent>

        {/* ---- Keyboard Shortcuts --------------------------------------- */}
        <TabsContent value="shortcuts" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-indigo-600" />
                Keyboard Shortcuts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left pb-2 font-medium text-muted-foreground">Keys</th>
                    <th className="text-left pb-2 font-medium text-muted-foreground">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {SHORTCUTS.map((s) => (
                    <tr key={s.desc} className="border-b border-border last:border-none">
                      <td className="py-2 pr-6">
                        <span className="flex flex-wrap gap-1">
                          {s.keys.map((k, i) => (
                            <React.Fragment key={k}>
                              <KbdKey>{k}</KbdKey>
                              {i < s.keys.length - 1 && (
                                <span className="text-muted-foreground self-center">+</span>
                              )}
                            </React.Fragment>
                          ))}
                        </span>
                      </td>
                      <td className="py-2 text-foreground">{s.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---- API Reference -------------------------------------------- */}
        <TabsContent value="api" className="mt-6 space-y-4">
          <p className="text-sm text-muted-foreground">
            DocReview360 exposes a full REST API documented with OpenAPI /
            Swagger. Use it to build integrations, automate workflows, or query
            project data programmatically.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader className="flex flex-row items-center gap-3 pb-2">
                <Code2 className="w-6 h-6 text-indigo-600" />
                <CardTitle className="text-base font-semibold">Swagger UI</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Interactive API explorer. Browse every endpoint, view request
                  and response schemas, and send test requests directly from your
                  browser.
                </p>
                <Link
                  href="/api-docs"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:underline"
                >
                  Open Swagger UI
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center gap-3 pb-2">
                <Code2 className="w-6 h-6 text-cyan-600" />
                <CardTitle className="text-base font-semibold">ReDoc</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Alternative three-panel API reference. Easier to read when
                  reviewing schema details or sharing documentation with
                  stakeholders.
                </p>
                <a
                  href="http://localhost:8000/redoc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-cyan-600 hover:underline"
                >
                  Open ReDoc
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </CardContent>
            </Card>

            <Card className="sm:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Authentication</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  All API endpoints (except <code className="font-mono text-xs">/health</code> and{" "}
                  <code className="font-mono text-xs">/branding</code>) require a Bearer JWT token.
                  Obtain a token by posting to{" "}
                  <code className="font-mono text-xs bg-muted px-1 rounded">/auth/token</code>{" "}
                  with your username and password. Include the token in the{" "}
                  <code className="font-mono text-xs">Authorization: Bearer &lt;token&gt;</code>{" "}
                  header on subsequent requests.
                </p>
                <p className="text-sm text-muted-foreground">
                  Tokens expire after one hour. Refresh by re-authenticating or
                  by calling{" "}
                  <code className="font-mono text-xs bg-muted px-1 rounded">/auth/refresh</code>.
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
