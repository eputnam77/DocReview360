import type { NextApiRequest, NextApiResponse } from "next";

type Data = { suggestion: string } | { error: string };

const DEFAULT_MODEL = process.env.OPENROUTER_MODEL || "openrouter/auto"; // Prefer free/auto models on OpenRouter

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data>
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    const { text, instruction } = req.body || {};
    if (!text || typeof text !== "string") {
      return res.status(400).json({ error: "Missing or invalid 'text'" });
    }

    const apiKey = process.env.OPENROUTER_API_KEY;
    if (!apiKey) {
      // Clear, actionable error to configure OpenRouter for local usage
      return res.status(500).json({
        error:
          "OPENROUTER_API_KEY not set. Add it to frontend/.env.local to enable AI suggestions.",
      });
    }

    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

    const prompt = buildRewritePrompt(text, instruction);

    const orRes = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        "HTTP-Referer": siteUrl,
        "X-Title": "DocReview360",
      },
      body: JSON.stringify({
        model: DEFAULT_MODEL,
        messages: [
          {
            role: "system",
            content:
              "You are a concise, helpful writing assistant for technical documentation. Keep meaning, improve clarity, and return only the rewritten text with no extra commentary.",
          },
          { role: "user", content: prompt },
        ],
        temperature: 0.2,
        max_tokens: 600,
      }),
    });

    if (!orRes.ok) {
      const body = await orRes.text();
      return res.status(orRes.status).json({ error: body || "OpenRouter error" });
    }

    const data = (await orRes.json()) as any;
    const suggestion: string =
      data?.choices?.[0]?.message?.content?.trim?.() || "";

    if (!suggestion) {
      return res.status(502).json({ error: "Empty response from model" });
    }

    return res.status(200).json({ suggestion });
  } catch (err: any) {
    return res
      .status(500)
      .json({ error: err?.message || "AI suggest failed unexpectedly" });
  }
}

function buildRewritePrompt(text: string, instruction?: string) {
  const baseInstruction =
    instruction && typeof instruction === "string"
      ? instruction
      : "Rewrite for clarity and concision, preserving meaning and tone.";
  return `${baseInstruction}\n\nText:\n${text}`;
}

