import React, { useState } from "react";

export type ExtensionStatus = "idle" | "loading" | "loaded" | "error";

export interface ExtensionItem {
  id: string;
  label: string;
  enabled: boolean;
  status: ExtensionStatus;
  onToggle: () => void;
  watermarkText?: string;
  onWatermarkText?: (text: string) => void;
  seldomUsed?: boolean;
}

interface Props {
  items: ExtensionItem[];
}

export default function ExtensionsPanel({ items }: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const basic = items.filter((i) => !i.seldomUsed);
  const advanced = items.filter((i) => i.seldomUsed);

  const renderItem = (item: ExtensionItem) => (
    <div key={item.id} className="mb-4">
      <div className="flex items-center justify-between">
        <button
          onClick={item.onToggle}
          className={`px-2 py-1 rounded ${
            item.enabled ? "bg-green-500 text-white" : "bg-gray-200"
          }`}
        >
          {item.enabled ? "Disable" : "Enable"} {item.label}
        </button>
        {item.status === "loaded" && (
          <span className="text-xs bg-green-100 text-green-800 px-2 rounded">
            OK
          </span>
        )}
        {item.status === "error" && (
          <span className="text-xs bg-red-100 text-red-800 px-2 rounded">
            Failed
          </span>
        )}
        {item.status === "loading" && (
          <span className="text-xs bg-yellow-100 text-yellow-800 px-2 rounded">
            Loading
          </span>
        )}
      </div>
      {item.id === "watermark" && item.enabled && (
        <input
          className="mt-2 w-full border rounded px-2 py-1 text-sm"
          value={item.watermarkText}
          onChange={(e) => item.onWatermarkText?.(e.target.value)}
          placeholder="Watermark text"
        />
      )}
    </div>
  );

  return (
    <section className="mt-4">
      <div className="font-semibold mb-2">Extensions</div>
      {basic.map(renderItem)}
      {advanced.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs underline"
          >
            {showAdvanced ? "Hide" : "Show"} advanced
          </button>
          {showAdvanced && <div className="mt-2">{advanced.map(renderItem)}</div>}
        </div>
      )}
    </section>
  );
}

