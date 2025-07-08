import { useRouter } from "next/router";
import { Button } from "@/components/ui/button";

export default function DocumensoSign() {
  const router = useRouter();
  const { sig } = router.query as { sig: string };
  const returnTo = (router.query.return as string) || "/";

  const complete = () => {
    fetch(`/sign/${sig}/complete`, { method: "POST" }).then(() => {
      router.push(returnTo);
    });
  };

  if (!sig) return <p className="p-4">Loading…</p>;
  return (
    <div className="p-8 space-y-4 text-center">
      <h1 className="text-2xl font-bold">Documenso Signature</h1>
      <p>Signature ID: {sig}</p>
      <Button onClick={complete}>Sign Document</Button>
    </div>
  );
}
