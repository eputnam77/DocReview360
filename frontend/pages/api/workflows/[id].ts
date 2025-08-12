import type { NextApiRequest, NextApiResponse } from "next";

const SYSTEM_WORKFLOW = {
  id: "branch-coordination",
  name: "branch-coordination",
  description:
    "Standard workflow with SME, Front Line Manager, Product Policy Manager, Technical Writer, Senior Technical Writer, and Technical Writing Manager steps",
  steps: [
    { id: "1", role: "Subject Matter Expert", user: "", required: true },
    { id: "2", role: "Front Line Manager", user: "", required: true },
    { id: "3", role: "Product Policy Manager", user: "", required: true },
    { id: "4", role: "Technical Writer", user: "", required: true },
    { id: "5", role: "Senior Technical Writer", user: "", required: true },
    { id: "6", role: "Technical Writing Manager", user: "", required: true },
  ],
  usage: 0,
  created: new Date().toISOString().split("T")[0],
  updated: new Date().toISOString().split("T")[0],
  logs: [
    { timestamp: new Date().toISOString().split("T")[0], action: "Workflow created" },
  ],
};

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query;
  if (id === "branch-coordination") {
    return res.status(200).json(SYSTEM_WORKFLOW);
  }
  return res.status(404).json({ error: "Workflow not found" });
}

