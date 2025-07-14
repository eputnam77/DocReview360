import { useRouter } from "next/router";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ShieldCheck } from "lucide-react";
import { useState } from "react";

export default function DocumensoSign() {
  const router = useRouter();
  const { sig } = router.query as { sig: string };
  const returnTo = (router.query.return as string) || "/";
  const [signing, setSigning] = useState(false);
  const [done, setDone] = useState(false);

  const complete = () => {
    setSigning(true);
    fetch(`/sign/${sig}/complete`, { method: "POST" })
      .then(() => {
        setDone(true);
        setTimeout(() => router.push(returnTo), 1000);
      })
      .finally(() => setSigning(false));
  };

  if (!sig) return <p className="p-4">Loading…</p>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md mx-auto shadow-lg border">
        <CardHeader className="flex flex-col items-center gap-1">
          <ShieldCheck className="w-10 h-10 text-indigo-600 mb-1" />
          <CardTitle className="text-2xl font-bold">
            Documenso Official Approval
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center">
            <div className="text-gray-500 text-sm mb-2">
              Approval ID: <span className="font-mono">{sig}</span>
            </div>
            <div className="mb-4 text-gray-600">
              {done
                ? (
                  <span className="text-green-700 font-semibold">Document signed and approved. Redirecting…</span>
                ) : (
                  <>
                    To approve this document, click the button below.<br />
                    This will record your official approval.<br />
                  </>
                )
              }
            </div>
            <Button
              onClick={complete}
              disabled={done || signing}
              className="w-full text-lg py-3"
            >
              {signing ? "Signing…" : done ? "Signed" : "Sign & Approve"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
