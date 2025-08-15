"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useRouter } from "next/router";

const sample = [
  {
    id: "1",
    reviewer: "Alice",
    routing: "R1",
    pagePara: "1/1",
    comment: "Sample comment",
    change: "Update text",
    decision: "Accepted",
    disposition: "Fixed",
  },
];

export default function ReviewWorkspacePage() {
  const router = useRouter();
  const { reviewId } = router.query;

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-2xl font-semibold">Review {reviewId}</h1>
      <Card>
        <CardHeader>
          <CardTitle>Comments & Disposition</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reviewer</TableHead>
                <TableHead>Routing</TableHead>
                <TableHead>Page/Para</TableHead>
                <TableHead>Comment</TableHead>
                <TableHead>Change</TableHead>
                <TableHead>Decision</TableHead>
                <TableHead>Disposition</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sample.map((d) => (
                <TableRow key={d.id}>
                  <TableCell>{d.reviewer}</TableCell>
                  <TableCell>{d.routing}</TableCell>
                  <TableCell>{d.pagePara}</TableCell>
                  <TableCell className="max-w-xs truncate">{d.comment}</TableCell>
                  <TableCell className="max-w-xs truncate">{d.change}</TableCell>
                  <TableCell>{d.decision}</TableCell>
                  <TableCell>{d.disposition}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

