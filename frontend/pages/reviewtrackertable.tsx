import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Avatar } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowUpRight } from "lucide-react";

const DOCUMENTS = [
  {
    id: "DOC-001",
    subject: "Policy Update",
    type: "Memo",
    status: "New",
    progress: 10,
    assigned: { name: "Jane Doe", avatar: "/avatars/jane.jpg" },
    dueDate: "2025-09-19"
  },
  {
    id: "DOC-002",
    subject: "Compliance Review",
    type: "Report",
    status: "In-Progress",
    progress: 60,
    assigned: { name: "John Smith", avatar: "/avatars/john.jpg" },
    dueDate: "2025-09-19"
  },
  {
    id: "DOC-003",
    subject: "Legal Checklist",
    type: "Checklist",
    status: "In-Progress",
    progress: 30,
    assigned: { name: "Sarah Lee", avatar: "/avatars/sarah.jpg" },
    dueDate: "2025-09-19"
  },
  {
    id: "DOC-004",
    subject: "Annual Financials",
    type: "Report",
    status: "Completed",
    progress: 100,
    assigned: { name: "Mike West", avatar: "/avatars/mike.jpg" },
    dueDate: "2025-09-19"
  },
  // Add more docs as needed
];

const statusColor = {
  "New": "bg-green-100 text-green-700",
  "In-Progress": "bg-yellow-100 text-yellow-800",
  "Completed": "bg-blue-100 text-blue-700",
  "Blocked": "bg-red-100 text-red-700"
};

export default function ReviewTrackerTable() {
  const [data] = useState(DOCUMENTS);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Document Review Tracker</h1>
        <Button variant="outline">+ New Document</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Document ID</TableHead>
            <TableHead>Subject</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead>Assigned</TableHead>
            <TableHead>Due Date</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell>{doc.id}</TableCell>
              <TableCell className="max-w-xs truncate">{doc.subject}</TableCell>
              <TableCell>{doc.type}</TableCell>
              <TableCell>
                <span className={`rounded px-2 py-1 text-xs font-medium ${statusColor[doc.status] || "bg-gray-100 text-gray-800"}`}>
                  {doc.status}
                </span>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Progress value={doc.progress} className="w-24" />
                  <span className="text-xs">{doc.progress}%</span>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Avatar src={doc.assigned.avatar} alt={doc.assigned.name} className="w-6 h-6" />
                  <span className="text-sm">{doc.assigned.name}</span>
                </div>
              </TableCell>
              <TableCell>{doc.dueDate}</TableCell>
              <TableCell>
                <Button size="icon" variant="ghost">
                  <ArrowUpRight className="w-4 h-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {/* Pagination (simple example) */}
      <div className="flex justify-between items-center mt-4">
        <Button variant="ghost" disabled>Previous</Button>
        <div>Page 1 of 8</div>
        <Button variant="ghost">Next</Button>
      </div>
    </div>
  );
}
