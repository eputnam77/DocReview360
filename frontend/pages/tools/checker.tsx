// pages/tools/checker.tsx
//
// Federal Style Validator checks have been consolidated into the
// Document Quality Checker surface.  This page redirects there.
import { useEffect } from "react";
import { useRouter } from "next/router";

export default function CheckerRedirectPage() {
    const router = useRouter();

    useEffect(() => {
        router.replace("/tools/document-quality");
    }, [router]);

    return (
        <div className="flex items-center justify-center h-64">
            <p className="text-gray-500 text-sm">
                Redirecting to Document Quality Checker…
            </p>
        </div>
    );
}
