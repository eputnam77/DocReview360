// frontend/components/SectionErrorBoundary.tsx
// Thin section-level error boundary.  Catches render exceptions in a subtree
// and shows an inline fallback instead of crashing the whole page.

import React from "react";

interface Props {
  children: React.ReactNode;
  /** Optional label shown in the fallback — defaults to "This section" */
  label?: string;
  /** Optional custom fallback rendered instead of the default message */
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

export class SectionErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const msg =
      error instanceof Error
        ? error.message
        : typeof error === "string"
        ? error
        : "An unexpected error occurred.";
    return { hasError: true, errorMessage: msg };
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("[SectionErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback !== undefined) {
        return <>{this.props.fallback}</>;
      }
      const label = this.props.label ?? "This section";
      return (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
        >
          <strong>{label} failed to load.</strong>{" "}
          <span className="opacity-75">{this.state.errorMessage}</span>
        </div>
      );
    }
    return <>{this.props.children}</>;
  }
}

export default SectionErrorBoundary;
