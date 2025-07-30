import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <Card className="max-w-2xl w-full shadow-lg">
        <CardHeader>
          <CardTitle className="text-3xl font-bold">About DocReview360</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <section>
            <p className="text-lg">
              <strong>DocReview360</strong> is a modern, collaborative document
              workflow and approval platform. Our mission is to streamline
              regulatory, policy, and technical documentation for teams of any
              size.
            </p>
          </section>
          <section>
            <h2 className="text-xl font-semibold mt-4 mb-1">Key Features</h2>
            <ul className="list-disc pl-6 space-y-1 text-base">
              <li>Flexible workflow and project management</li>
              <li>Embedded editors: TipTap and Microsoft Word</li>
              <li>Customizable approval routing and review cycles</li>
              <li>Full audit history and activity tracking</li>
              <li>Modern UI with accessibility and responsive design</li>
            </ul>
          </section>
          <section>
            <h2 className="text-xl font-semibold mt-4 mb-1">Tech Stack</h2>
            <ul className="list-disc pl-6 space-y-1 text-base">
              <li>React, Next.js, TypeScript, Tailwind CSS</li>
              <li>shadcn/ui, lucide-react for UI components and icons</li>
              <li>Integrations with open-source and Microsoft editing tools</li>
            </ul>
          </section>
          <section>
            <h2 className="text-xl font-semibold mt-4 mb-1">Credits</h2>
            <p>
              Built with ❤️ by the DocReview360 team and the open-source community.
            </p>
          </section>
          <section>
            <h2 className="text-xl font-semibold mt-4 mb-1">Contact</h2>
            <p>
              For questions, feedback, or support, please email{" "}
              <a
                href="mailto:support@docreview360.example.com"
                className="text-indigo-700 underline"
              >
                support@docreview360.example.com
              </a>
              .
            </p>
          </section>
        </CardContent>
      </Card>
    </div>
  );
}
