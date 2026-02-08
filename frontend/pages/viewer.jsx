import { useRouter } from "next/router";
import React from "react";
export default function DocumentViewer() {
    const router = useRouter();
    const { type, url } = router.query;
    if (!url || typeof url !== "string") {
        return <p className="p-4">No file specified.</p>;
    }
    const decoded = decodeURIComponent(url);
    const src = type === "docx"
        ? `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(decoded)}`
        : decoded;
    return (<div className="min-h-screen bg-gray-50 p-4">
      <iframe src={src} className="w-full h-[80vh] border rounded-md bg-white" title="Document Viewer"/>
    </div>);
}
