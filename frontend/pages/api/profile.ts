import type { NextApiRequest, NextApiResponse } from "next";

interface Profile {
  username: string;
  email: string;
  phone: string;
  picture: string;
  shorthand: string;
  dashboards: string[];
}

  let profile: Profile = {
  username: "user",
  email: "",
  phone: "",
  picture: "",
  shorthand: "",
  dashboards: ["main"],
};

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    res.status(200).json(profile);
  } else if (req.method === "PUT") {
    profile = { ...profile, ...(req.body as Partial<Profile>) };
    res.status(200).json(profile);
  } else {
    res.status(405).end();
  }
}
