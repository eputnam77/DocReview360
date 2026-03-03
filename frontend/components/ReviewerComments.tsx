// frontend/components/ReviewerComments.tsx
"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useComments } from "@/lib/useComments";
import type { Comment } from "@/lib/useComments";

const AVAILABLE_TAGS = ["legal", "style", "technical", "policy"] as const;
type Tag = (typeof AVAILABLE_TAGS)[number];

const STATUS_COLORS: Record<Comment["status"], string> = {
  open: "bg-blue-100 text-blue-800",
  resolved: "bg-green-100 text-green-800",
  accepted: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
};

const TAG_COLORS: Record<Tag, string> = {
  legal: "bg-purple-100 text-purple-800",
  style: "bg-pink-100 text-pink-800",
  technical: "bg-amber-100 text-amber-800",
  policy: "bg-cyan-100 text-cyan-800",
};

interface ReviewerCommentsProps {
  docId: string;
  currentUser: string;
  canDispose?: boolean;
}

function CommentItem({
  comment,
  replies,
  onReply,
  onUpdateStatus,
  canDispose,
  currentUser,
}: {
  comment: Comment;
  replies: Comment[];
  onReply: (parentId: string) => void;
  onUpdateStatus: (id: string, status: Comment["status"]) => void;
  canDispose: boolean;
  currentUser: string;
}) {
  return (
    <div className="space-y-2">
      <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-sm font-semibold text-gray-800">{comment.user}</span>
          <span className="text-xs text-gray-400">
            {new Date(comment.created).toLocaleDateString()}
          </span>
        </div>

        {/* Body */}
        <p className="text-sm text-gray-700 whitespace-pre-wrap">{comment.raw_text || comment.text}</p>

        {/* Tags */}
        {comment.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {comment.tags.map((tag) => (
              <span
                key={tag}
                className={cn(
                  "px-1.5 py-0.5 rounded text-[11px] font-medium",
                  TAG_COLORS[tag as Tag] ?? "bg-gray-100 text-gray-700",
                )}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Status + actions */}
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span
            className={cn(
              "px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize",
              STATUS_COLORS[comment.status],
            )}
          >
            {comment.status}
          </span>

          {canDispose && comment.status === "open" && (
            <>
              <button
                onClick={() => onUpdateStatus(comment.id, "resolved")}
                className="text-xs text-green-700 underline hover:no-underline"
              >
                Resolve
              </button>
              <button
                onClick={() => onUpdateStatus(comment.id, "accepted")}
                className="text-xs text-emerald-700 underline hover:no-underline"
              >
                Accept
              </button>
              <button
                onClick={() => onUpdateStatus(comment.id, "rejected")}
                className="text-xs text-red-700 underline hover:no-underline"
              >
                Reject
              </button>
            </>
          )}

          <button
            onClick={() => onReply(comment.id)}
            className="text-xs text-blue-600 underline hover:no-underline ml-auto"
          >
            Reply
          </button>
        </div>
      </div>

      {/* Replies */}
      {replies.length > 0 && (
        <div className="ml-6 space-y-2">
          {replies.map((reply) => (
            <div key={reply.id} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-xs font-semibold text-gray-700">{reply.user}</span>
                <span className="text-xs text-gray-400">
                  {new Date(reply.created).toLocaleDateString()}
                </span>
              </div>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">
                {reply.raw_text || reply.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ReviewerComments({
  docId,
  currentUser,
  canDispose = false,
}: ReviewerCommentsProps) {
  const { comments, isLoading, postComment, updateComment, isPosting } = useComments(docId);

  const [newText, setNewText] = useState("");
  const [selectedTags, setSelectedTags] = useState<Tag[]>([]);
  const [replyingTo, setReplyingTo] = useState<string | null>(null);

  const parentComments = comments.filter((c) => !c.parent);
  const repliesByParent = comments.reduce<Record<string, Comment[]>>((acc, c) => {
    if (c.parent) {
      acc[c.parent] = acc[c.parent] ?? [];
      acc[c.parent].push(c);
    }
    return acc;
  }, {});

  const toggleTag = (tag: Tag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = newText.trim();
    if (!text) return;
    await postComment({
      user: currentUser,
      text,
      tags: selectedTags,
      parent: replyingTo ?? undefined,
    });
    setNewText("");
    setSelectedTags([]);
    setReplyingTo(null);
  };

  const handleUpdateStatus = async (commentId: string, status: Comment["status"]) => {
    await updateComment(commentId, { status });
  };

  if (isLoading) {
    return <div className="text-sm text-gray-400 py-4">Loading comments…</div>;
  }

  return (
    <div className="space-y-4">
      {/* Existing comment threads */}
      {parentComments.length === 0 ? (
        <p className="text-sm text-gray-400 py-2">No comments yet. Be the first to add one.</p>
      ) : (
        <div className="space-y-3">
          {parentComments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              replies={repliesByParent[comment.id] ?? []}
              onReply={(id) => setReplyingTo((prev) => (prev === id ? null : id))}
              onUpdateStatus={handleUpdateStatus}
              canDispose={canDispose}
              currentUser={currentUser}
            />
          ))}
        </div>
      )}

      {/* Add comment form */}
      <form onSubmit={handleSubmit} className="space-y-2 border-t pt-4">
        {replyingTo && (
          <div className="flex items-center gap-2 text-xs text-blue-600">
            <span>Replying to comment</span>
            <button
              type="button"
              onClick={() => setReplyingTo(null)}
              className="underline"
            >
              Cancel reply
            </button>
          </div>
        )}

        <textarea
          className="w-full rounded border border-gray-200 p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400"
          rows={3}
          placeholder={replyingTo ? "Write a reply…" : "Add a comment…"}
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
        />

        {/* Tag chips */}
        <div className="flex flex-wrap gap-1">
          {AVAILABLE_TAGS.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => toggleTag(tag)}
              className={cn(
                "px-2 py-0.5 rounded-full text-[11px] font-medium border transition-colors",
                selectedTags.includes(tag)
                  ? cn(TAG_COLORS[tag], "border-transparent")
                  : "bg-white border-gray-200 text-gray-500 hover:border-gray-400",
              )}
            >
              {tag}
            </button>
          ))}
        </div>

        <Button
          type="submit"
          size="sm"
          disabled={!newText.trim() || isPosting}
          className="bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          {isPosting ? "Posting…" : "Post"}
        </Button>
      </form>
    </div>
  );
}
