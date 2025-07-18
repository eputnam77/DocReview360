import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function ChatBot() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);

  async function ask() {
    if (!question.trim()) return;
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: question }),
    });
    const data = await resp.json();
    setAnswer(data.result);
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Project Chat Bot</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about a project..."
          />
          <Button onClick={ask}>Ask</Button>
        </div>
        {answer && <p className="text-sm">{answer}</p>}
      </CardContent>
    </Card>
  );
}
