import React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  FileCog,      // Icon for “Converter”
  SpellCheck,   // Icon for “Checker”
  Stamp         // Icon for “Special Conditions”
} from "lucide-react";

// List of tool items
const TOOLS_ITEMS = [
  {
    label: "Document Converter",
    href: "/tools/converter",
    icon: <FileCog className="w-6 h-6 text-indigo-600" />,
    desc: "Convert Word, Markdown, and TipTap between formats.",
  },
  {
    label: "Document Checker",
    href: "/tools/checker",
    icon: <SpellCheck className="w-6 h-6 text-green-600" />,
    desc: "Validate documents against FAA style and accessibility rules.",
  },
  {
    label: "Special Conditions Converter",
    href: "/tools/checker",
    icon: <Stamp className="w-6 h-6 text-rose-600" />,
    desc: "Generate legally formatted Special Conditions notices.",
  },
];

export default function ToolsPage() {
  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Tools</h1>
      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
        {TOOLS_ITEMS.map((item) => (
          <Link key={item.href} href={item.href} className="group">
            <Card className="transition-shadow group-hover:shadow-lg h-full cursor-pointer">
              <CardHeader className="flex flex-row items-center gap-3 pb-2">
                {item.icon}
                <CardTitle className="text-lg font-semibold">
                  {item.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-500">{item.desc}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
