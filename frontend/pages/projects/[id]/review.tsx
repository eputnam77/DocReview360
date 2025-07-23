import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea"; // create a textarea component if you don't have one
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { API } from "@/lib/api";

interface Review {
  id: string;
  reviewer: string;
  status: "pending" | "approved" | "rejected";
  comment: string;
  created: string;
}

export default function ProjectReviewPage() {
  const router = useRouter();
  const { id } = router.query;
  const [reviews, setReviews] = useState<Review[]>([]);
  const [newComment, setNewComment] = useState("");
  const [newStatus, setNewStatus] = useState<
    "pending" | "approved" | "rejected"
  >("pending");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch review history for this project
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`${API}/projects/${id}/reviews`)
      .then((r) => r.json())
      .then((data) => setReviews(data))
      .catch(() => setReviews([]))
      .finally(() => setLoading(false));
  }, [id]);

  // Submit a new review/comment
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!newComment.trim()) {
      setError("Comment is required.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API}/projects/${id}/reviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          comment: newComment,
          status: newStatus,
          // reviewer: "current user", // Add current user if available
        }),
      });
      if (!res.ok) throw new Error("Failed to submit review");
      const data = await res.json();
      setReviews([data, ...reviews]);
      setNewComment("");
      setNewStatus("pending");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto space-y-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-bold">Project Review</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <Label htmlFor="review-comment">Add Comment</Label>
                <Textarea
                  id="review-comment"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Your feedback or question"
                  rows={3}
                  required
                />
              </div>
              <div>
                <Label htmlFor="status">Status</Label>
                <select
                  id="status"
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value as any)}
                  className="border rounded px-2 py-1"
                >
                  <option value="pending">Pending</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              {error && <div className="text-red-600 text-sm">{error}</div>}
              <Button type="submit" disabled={loading}>
                {loading ? "Submitting..." : "Add Review"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">
              Review History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reviewer</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Comment</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reviews.map((review) => (
                  <TableRow key={review.id}>
                    <TableCell>{review.reviewer}</TableCell>
                    <TableCell className="capitalize">
                      {review.status}
                    </TableCell>
                    <TableCell>{review.comment}</TableCell>
                    <TableCell>{review.created.slice(0, 10)}</TableCell>
                  </TableRow>
                ))}
                {reviews.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={4}
                      className="text-center text-muted-foreground"
                    >
                      No reviews yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
