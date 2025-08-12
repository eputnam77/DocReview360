import type { NextApiRequest, NextApiResponse } from "next";

const DEFAULT_WORKFLOWS = [
  {
    id: "branch-coordination",
    name: "branch-coordination",
    description:
      "Standard workflow with SME, Front Line Manager, Product Policy Manager, Technical Writer, Senior Technical Writer, and Technical Writing Manager steps",
    usage: 0,
    updated: new Date().toISOString().split("T")[0],
  },
];

export default function handler(_req: NextApiRequest, res: NextApiResponse) {
  res.status(200).json(DEFAULT_WORKFLOWS);
}

