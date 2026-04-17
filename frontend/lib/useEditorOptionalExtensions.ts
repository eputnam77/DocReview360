import { useState } from "react";

import type { ExtensionStatus } from "@/components/ExtensionsPanel";

interface UseEditorOptionalExtensionsInput {
  persistPreferences: (overrides?: Partial<Record<string, boolean | string>>) => Promise<void>;
}

export function useEditorOptionalExtensions({
  persistPreferences,
}: UseEditorOptionalExtensionsInput) {
  const [headingLockEnabled, setHeadingLockEnabled] = useState(false);
  const [headingLockExtension, setHeadingLockExtension] = useState<any>(null);
  const [headingLockStatus, setHeadingLockStatus] = useState<ExtensionStatus>("idle");

  const [indentationEnabled, setIndentationEnabled] = useState(false);
  const [indentationExtension, setIndentationExtension] = useState<any>(null);
  const [indentationStatus, setIndentationStatus] = useState<ExtensionStatus>("idle");

  const [sectionNodeEnabled, setSectionNodeEnabled] = useState(false);
  const [sectionNodeExtension, setSectionNodeExtension] = useState<any>(null);
  const [sectionNodeStatus, setSectionNodeStatus] = useState<ExtensionStatus>("idle");

  const [markReviewEnabled, setMarkReviewEnabled] = useState(false);
  const [markReviewExtension, setMarkReviewExtension] = useState<any>(null);
  const [markReviewStatus, setMarkReviewStatus] = useState<ExtensionStatus>("idle");

  const [watermarkEnabled, setWatermarkEnabled] = useState(false);
  const [watermarkExtension, setWatermarkExtension] = useState<any>(null);
  const [watermarkStatus, setWatermarkStatus] = useState<ExtensionStatus>("idle");
  const [watermarkText, setWatermarkText] = useState("Sample");

  function handleToggleHeadingLock() {
    if (headingLockEnabled) {
      setHeadingLockEnabled(false);
      setHeadingLockExtension(null);
      setHeadingLockStatus("idle");
      void persistPreferences({ heading_lock: false });
      return;
    }
    setHeadingLockStatus("loading");
    import("../extensions/tiptapHeadingLock")
      .then((mod) => {
        setHeadingLockExtension(() => mod.tiptapHeadingLock);
        setHeadingLockEnabled(true);
        setHeadingLockStatus("loaded");
        void persistPreferences({ heading_lock: true });
      })
      .catch(() => setHeadingLockStatus("error"));
  }

  function handleToggleIndentation() {
    if (indentationEnabled) {
      setIndentationEnabled(false);
      setIndentationExtension(null);
      setIndentationStatus("idle");
      void persistPreferences({ indentation: false });
      return;
    }
    setIndentationStatus("loading");
    import("../extensions/tiptapIndentation")
      .then((mod) => {
        setIndentationExtension(() => mod.tiptapIndentation);
        setIndentationEnabled(true);
        setIndentationStatus("loaded");
        void persistPreferences({ indentation: true });
      })
      .catch(() => setIndentationStatus("error"));
  }

  function handleToggleSectionNode() {
    if (sectionNodeEnabled) {
      setSectionNodeEnabled(false);
      setSectionNodeExtension(null);
      setSectionNodeStatus("idle");
      void persistPreferences({ section_node: false });
      return;
    }
    setSectionNodeStatus("loading");
    import("../extensions/tiptapSectionNode")
      .then((mod) => {
        setSectionNodeExtension(() => mod.tiptapSectionNode);
        setSectionNodeEnabled(true);
        setSectionNodeStatus("loaded");
        void persistPreferences({ section_node: true });
      })
      .catch(() => setSectionNodeStatus("error"));
  }

  function handleToggleMarkReview() {
    if (markReviewEnabled) {
      setMarkReviewEnabled(false);
      setMarkReviewExtension(null);
      setMarkReviewStatus("idle");
      void persistPreferences({ mark_review: false });
      return;
    }
    setMarkReviewStatus("loading");
    import("../extensions/tiptapMarkReview")
      .then((mod) => {
        setMarkReviewExtension(() => mod.tiptapMarkReview);
        setMarkReviewEnabled(true);
        setMarkReviewStatus("loaded");
        void persistPreferences({ mark_review: true });
      })
      .catch(() => setMarkReviewStatus("error"));
  }

  function handleToggleWatermark() {
    if (watermarkEnabled) {
      setWatermarkEnabled(false);
      setWatermarkExtension(null);
      setWatermarkStatus("idle");
      void persistPreferences({ watermark: false });
      return;
    }
    setWatermarkStatus("loading");
    import("../extensions/tiptapWatermark")
      .then((mod) => {
        setWatermarkExtension(() => mod.tiptapWatermark);
        setWatermarkEnabled(true);
        setWatermarkStatus("loaded");
        void persistPreferences({ watermark: true, watermark_text: watermarkText });
      })
      .catch(() => setWatermarkStatus("error"));
  }

  function handleWatermarkText(text: string) {
    setWatermarkText(text);
    void persistPreferences({ watermark_text: text });
  }

  return {
    headingLockEnabled,
    headingLockExtension,
    headingLockStatus,
    setHeadingLockEnabled,
    indentationEnabled,
    indentationExtension,
    indentationStatus,
    setIndentationEnabled,
    sectionNodeEnabled,
    sectionNodeExtension,
    sectionNodeStatus,
    setSectionNodeEnabled,
    markReviewEnabled,
    markReviewExtension,
    markReviewStatus,
    setMarkReviewEnabled,
    watermarkEnabled,
    watermarkExtension,
    watermarkStatus,
    setWatermarkEnabled,
    watermarkText,
    setWatermarkText,
    handleToggleHeadingLock,
    handleToggleIndentation,
    handleToggleSectionNode,
    handleToggleMarkReview,
    handleToggleWatermark,
    handleWatermarkText,
  };
}
