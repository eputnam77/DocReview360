import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API } from "@/lib/api";
import { ShieldCheck } from "lucide-react";
import { useRouter } from "next/router";
import { useState } from "react";
export default function DocumensoSign() {
    const router = useRouter();
    const { sig } = router.query;
    const returnTo = router.query.return || "/";
    const safeReturnTo = (() => {
        try {
            const decoded = decodeURIComponent(returnTo);
            return typeof decoded === 'string' && decoded.startsWith('/') ? decoded : '/';
        }
        catch {
            return returnTo.startsWith('/') ? returnTo : '/';
        }
    })();
    const approvalId = router.query.approval;
    const [signing, setSigning] = useState(false);
    const [done, setDone] = useState(false);
    const [error, setError] = useState(null);
    const complete = () => {
        setSigning(true);
        setError(null);
        console.log(`Completing signature ${sig} for approval ${approvalId}`);
        // Call the backend to complete the signature
        fetch(`${API}/sign/${sig}/complete`, {
            method: "POST",
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then((r) => {
            console.log(`Signature completion response: ${r.status} ${r.statusText}`);
            if (!r.ok) {
                throw new Error(`HTTP ${r.status}: ${r.statusText}`);
            }
            return r.json();
        })
            .then(() => {
            console.log(`Signature completion successful`);
            // Store completion timestamp in localStorage for the approval
            if (approvalId) {
                const timestamp = new Date().toISOString();
                localStorage.setItem(`approval-${approvalId}`, timestamp);
                console.log(`Stored completion timestamp: ${timestamp}`);
                // Also sync with backend immediately
                fetch(`${API}/approvals/${approvalId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        state: 'approved',
                        signature: sig,
                    }),
                }).then(r => {
                    console.log(`Backend sync response: ${r.status} ${r.statusText}`);
                }).catch(err => {
                    console.error('Failed to sync approval with backend:', err);
                });
            }
            setDone(true);
            // Redirect back to the project page after a short delay
            setTimeout(() => {
                console.log(`Redirecting to: ${safeReturnTo}`);
                router.push(safeReturnTo);
            }, 1500);
        })
            .catch((err) => {
            console.error("Signature completion failed:", err);
            setError(err.message);
            setSigning(false);
        });
    };
    if (!sig)
        return <p className="p-4">Loading…</p>;
    return (<div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md mx-auto shadow-lg border">
        <CardHeader className="flex flex-col items-center gap-1">
          <ShieldCheck className="w-10 h-10 text-indigo-600 mb-1"/>
          <CardTitle className="text-2xl font-bold">
            Documenso Official Approval
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center">
            <div className="text-gray-500 text-sm mb-2">
              Approval ID: <span className="font-mono">{sig}</span>
            </div>
            {error && (<div className="mb-4 p-3 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
                Error: {error}
              </div>)}
            <div className="mb-4 text-gray-600">
              {done ? (<span className="text-green-700 font-semibold">Document signed and approved. Redirecting…</span>) : (<>
                  To approve this document, click the button below.<br />
                  This will record your official approval.<br />
                </>)}
            </div>
            <Button onClick={complete} disabled={done || signing} className="w-full text-lg py-3">
              {signing ? "Signing…" : done ? "Signed" : "Sign & Approve"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>);
}
