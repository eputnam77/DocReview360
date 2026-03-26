import React, { useState } from "react";
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
  User,
  Eye,
  Stamp,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Role definitions
// ---------------------------------------------------------------------------

type UserRole = "administrator" | "project-owner" | "reviewer" | "approver";

interface RoleTab {
  value: UserRole;
  label: string;
  icon: React.ReactNode;
  color: string;
}

const ROLE_TABS: RoleTab[] = [
  {
    value: "administrator",
    label: "Administrator",
    icon: <ShieldCheck className="w-4 h-4" />,
    color: "text-red-700",
  },
  {
    value: "project-owner",
    label: "Project Owner",
    icon: <User className="w-4 h-4" />,
    color: "text-indigo-700",
  },
  {
    value: "reviewer",
    label: "Reviewer",
    icon: <Eye className="w-4 h-4" />,
    color: "text-emerald-700",
  },
  {
    value: "approver",
    label: "Approver",
    icon: <Stamp className="w-4 h-4" />,
    color: "text-amber-700",
  },
];

// ---------------------------------------------------------------------------
// FAQ data — tagged by role
// ---------------------------------------------------------------------------

const FAQ_ITEMS: Array<{ q: string; a: React.ReactNode; roles: UserRole[] }> = [
  {
    q: "How do I create a project?",
    roles: ["project-owner", "administrator"],
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
    roles: ["project-owner", "administrator"],
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
    roles: ["project-owner", "administrator"],
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
    roles: ["administrator", "project-owner", "reviewer", "approver"],
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
    roles: ["project-owner", "administrator"],
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
    roles: ["administrator"],
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
    roles: ["administrator", "project-owner", "reviewer", "approver"],
    a: (
      <>
        Click your username in the sidebar to open your <strong>Profile</strong>{" "}
        page. From there you can change your password and enroll a TOTP
        authenticator app (Google Authenticator, Authy, etc.) for multi-factor
        authentication.
      </>
    ),
  },
  {
    q: "How do I submit my review?",
    roles: ["reviewer"],
    a: (
      <>
        Open the project you were invited to review. Go to the{" "}
        <strong>Feedback</strong> tab and use <strong>Post Feedback</strong> to
        add comments or questions. When you have finished, click{" "}
        <strong>Submit Review</strong>. Your concurrence is then recorded and
        the project owner is notified.
      </>
    ),
  },
  {
    q: "How do I approve a document?",
    roles: ["approver"],
    a: (
      <>
        Open the project and go to the <strong>Approvals</strong> tab. Find
        your approval row and follow the configured approval method — this may
        be an electronic signature via Documenso, an initials field, or another
        method set by your administrator. The approval date is recorded and
        visible in the audit history.
      </>
    ),
  },
  {
    q: "How do I configure user roles and permissions?",
    roles: ["administrator"],
    a: (
      <>
        Go to <strong>Configuration &rarr; Permissions</strong> to define roles
        and their capabilities. Then go to{" "}
        <strong>Configuration &rarr; User Management</strong> to assign roles to
        individual users. Complete the Setup sequence in order: Permissions
        first, then Users, Workflows, Phases, and Document Types.
      </>
    ),
  },
  {
    q: "How do I monitor system activity as an admin?",
    roles: ["administrator"],
    a: (
      <>
        Go to <strong>Configuration &rarr; Audit Logs</strong> to review
        system-wide activity. The Admin Dashboard also shows a live audit
        timeline and recently active users. Individual project audit histories
        are visible in each project&apos;s <strong>History</strong> tab.
      </>
    ),
  },
];

// ---------------------------------------------------------------------------
// Role guide content
// ---------------------------------------------------------------------------

const ROLE_GUIDES: Record<UserRole, { heading: string; tasks: string[]; quickLinks: Array<{ label: string; href: string }> }> = {
  administrator: {
    heading: "Administrator Guide",
    tasks: [
      "Complete the Setup sequence: Permissions → Users → Workflows → Phases → Document Types.",
      "Manage user accounts, roles, and MFA enrollment.",
      "Configure workflow templates and phase requirements.",
      "Enable or disable built-in tools and install plugins from the Plugin Marketplace.",
      "Monitor system activity via Audit Logs and the Admin Dashboard.",
      "Customize branding, templates, and integrations for your organization.",
    ],
    quickLinks: [
      { label: "Configuration", href: "/configuration" },
      { label: "User Management", href: "/configuration/user-management" },
      { label: "Permissions", href: "/configuration/permissions" },
      { label: "Workflows", href: "/configuration/workflows" },
      { label: "Audit Logs", href: "/configuration/audit-logs" },
      { label: "Plugin Marketplace", href: "/configuration/plugin-marketplace" },
    ],
  },
  "project-owner": {
    heading: "Project Owner Guide",
    tasks: [
      "Create a new project: choose a document type and workflow template.",
      "Upload documents or create them in the TipTap editor.",
      "Invite reviewers and set due dates.",
      "Monitor the Feedback tab and disposition each reviewer comment.",
      "Advance the project through phases once required approvals are complete.",
      "Export the final document and review record for records retention.",
    ],
    quickLinks: [
      { label: "My Projects", href: "/projects" },
      { label: "New Project", href: "/projects/new" },
      { label: "TipTap Editor", href: "/editors/tiptap" },
      { label: "Document Quality Checker", href: "/tools/document-quality" },
    ],
  },
  reviewer: {
    heading: "Reviewer Guide",
    tasks: [
      "Open a project you have been invited to review.",
      "Read the documents in the Documents tab.",
      "Use the Feedback tab to post comments, questions, and concerns.",
      "Open the TipTap editor to add inline comments or suggestions.",
      "Click Submit Review when you have finished providing feedback.",
      "Your concurrence is recorded and the project owner is notified automatically.",
    ],
    quickLinks: [
      { label: "My Projects", href: "/projects" },
      { label: "TipTap Editor", href: "/editors/tiptap" },
    ],
  },
  approver: {
    heading: "Approver Guide",
    tasks: [
      "Open the project assigned to you for approval.",
      "Review the documents and feedback history.",
      "Go to the Approvals tab and find your approval row.",
      "Complete the approval using the configured signature or initials method.",
      "Your approval date is recorded in the project audit history.",
      "If you have questions, post feedback in the Feedback tab before approving.",
    ],
    quickLinks: [
      { label: "My Projects", href: "/projects" },
    ],
  },
};

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
  const [activeRole, setActiveRole] = useState<UserRole>("administrator");

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

      <Tabs defaultValue="getting-started">
        <TabsList className="flex-wrap">
          <TabsTrigger value="getting-started">
            <Rocket className="w-4 h-4 mr-1.5" />
            Getting Started
          </TabsTrigger>
          <TabsTrigger value="concepts">
            <BookOpen className="w-4 h-4 mr-1.5" />
            Key Concepts
          </TabsTrigger>
          <TabsTrigger value="by-role">
            <Users2 className="w-4 h-4 mr-1.5" />
            By Role
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

        {/* ---- By Role -------------------------------------------------- */}
        <TabsContent value="by-role" className="mt-6 space-y-6">
          <p className="text-sm text-muted-foreground">
            Select your role to see the tasks and guidance most relevant to you.
          </p>

          {/* Role selector */}
          <div className="flex flex-wrap gap-2">
            {ROLE_TABS.map((role) => (
              <button
                key={role.value}
                type="button"
                onClick={() => setActiveRole(role.value)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                  activeRole === role.value
                    ? "bg-indigo-600 border-indigo-600 text-white"
                    : "border-gray-200 text-gray-600 hover:border-indigo-300 hover:text-indigo-700"
                }`}
              >
                {role.icon}
                {role.label}
              </button>
            ))}
          </div>

          {/* Role content */}
          {ROLE_TABS.map((role) => {
            if (role.value !== activeRole) return null;
            const guide = ROLE_GUIDES[role.value];
            const roleFaqs = FAQ_ITEMS.filter((f) => f.roles.includes(role.value));
            return (
              <div key={role.value} className="space-y-6">
                {/* Task list */}
                <Card>
                  <CardHeader className="flex flex-row items-center gap-3 pb-2">
                    <span className={role.color}>{role.icon}</span>
                    <CardTitle className="text-base font-semibold">{guide.heading}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ol className="space-y-2 list-decimal list-inside">
                      {guide.tasks.map((task) => (
                        <li key={task} className="text-sm text-muted-foreground">
                          {task}
                        </li>
                      ))}
                    </ol>
                  </CardContent>
                </Card>

                {/* Quick links */}
                {guide.quickLinks.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-2">Quick Links</h3>
                    <div className="flex flex-wrap gap-2">
                      {guide.quickLinks.map((link) => (
                        <Link
                          key={link.href}
                          href={link.href}
                          className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
                        >
                          {link.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {/* Role-specific FAQ */}
                {roleFaqs.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-gray-700">
                      Common Questions for {role.label}
                    </h3>
                    {roleFaqs.map((item) => (
                      <FaqItem key={item.q} q={item.q} a={item.a} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
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
