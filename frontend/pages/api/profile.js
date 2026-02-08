let profile = {
    username: "user",
    email: "",
    phone: "",
    picture: "",
    shorthand: "",
    dashboards: ["main"],
};
export default function handler(req, res) {
    if (req.method === "GET") {
        res.status(200).json(profile);
    }
    else if (req.method === "PUT") {
        profile = { ...profile, ...req.body };
        res.status(200).json(profile);
    }
    else {
        res.status(405).end();
    }
}
