import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { getStoredAccessToken } from "@/lib/api";
import { toast } from "react-hot-toast";

export default function NewEmailTemplatePage() {
  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [task, setTask] = useState("");
  const token = getStoredAccessToken();

  const handleSave = async () => {
    const payload = { name, subject, body, task: task || undefined };
    try {
      await fetch("/api/email-templates", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      } catch {
        // ignore network errors in development mode
      }
    toast.success("Email template saved:\n" + JSON.stringify(payload, null, 2));
    setName("");
    setSubject("");
    setBody("");
    setTask("");
  };

  return (
    <div className="p-8 space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">Add Email Template</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-gray-600 text-sm">
            Use variables like {"{reviewer}"}, {"{document_number}"} and {"{document_title}"}.
          </div>
          <div className="space-y-4">
            <Input
              placeholder="Template Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              placeholder="Email Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
            />
            <Textarea
              className="h-40"
              placeholder="Email body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <Input
              placeholder="Workflow Task (optional)"
              value={task}
              onChange={(e) => setTask(e.target.value)}
            />
          </div>
          <Button
            size="lg"
            onClick={handleSave}
            disabled={!name || !subject || !body}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            Save Email Template
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
