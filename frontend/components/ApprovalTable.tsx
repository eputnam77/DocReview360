// frontend/components/ApprovalTable.tsx
"use client";

import React, { useMemo, useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Menu, Transition } from "@headlessui/react";
import { Fragment } from "react";
import { toast } from "react-hot-toast";
import * as Icons from "lucide-react";
import { FixedSizeList as List } from "react-window";
const Icon = Icons as any;

export interface Approval {
  id: string;
  reviewer: string;
  email: string;
  state: "pending" | "approved" | "overdue" | "rejected";
  dueAt: string;
  signedAt?: string;
  description?: string;
  required?: boolean;
}

interface Props {
  approvals: Approval[];
  currentUser?: string;
  canEdit?: boolean;
  onSign: (id: string) => void;
  onReset: (id: string) => void;
  onRemove: (id: string) => void;
  onBulkReminder: (ids: string[]) => void;
}

function classNames(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

function RowMenu({ children }: { children: React.ReactNode }) {
  return (
    <Menu as="div" className="relative inline-block text-left">
      {({ close }) => (
        <>
          <Menu.Button
            aria-label="Row actions"
            aria-haspopup="menu"
            className="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity"
          >
            <span className="w-4 h-4 block">...</span>
          </Menu.Button>
          <Transition
            as={Fragment}
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items
              /* @ts-expect-error headlessui typing */
              role="menu"
              className="absolute right-0 z-20 mt-2 w-48 rounded-md bg-white dark:bg-gray-900 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
              onKeyDown={(e) => e.key === "Escape" && close()}
            >
              {children}
            </Menu.Items>
          </Transition>
        </>
      )}
    </Menu>
  );
}

function useDebounce<T>(value: T, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

export default function ApprovalTable({
  approvals,
  currentUser,
  canEdit,
  onSign,
  onReset,
  onRemove,
  onBulkReminder,
}: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [requiredOnly, setRequiredOnly] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);
  const pageSize = 50;
  const [page, setPage] = useState(0);

  const roles = useMemo(() => {
    const set = new Set<string>();
    approvals.forEach((a) => a.description && set.add(a.description));
    return Array.from(set);
  }, [approvals]);

  const filtered = useMemo(() => {
    return approvals.filter((a) => {
      if (statusFilter !== "all" && a.state !== statusFilter) return false;
      if (roleFilter !== "all" && a.description !== roleFilter) return false;
      if (requiredOnly && !a.required) return false;
      if (
        debouncedSearch &&
        !`${a.reviewer} ${a.email}`
          .toLowerCase()
          .includes(debouncedSearch.toLowerCase())
      )
        return false;
      return true;
    });
  }, [approvals, statusFilter, roleFilter, requiredOnly, debouncedSearch]);

  useEffect(() => {
    setPage(0);
  }, [statusFilter, roleFilter, requiredOnly, debouncedSearch]);

  const paged = useMemo(() => {
    const start = page * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, page, pageSize]);

  const pageCount = Math.ceil(filtered.length / pageSize);

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const a = paged[index];
    return (
      <TableRow key={a.id} id={`approval-${a.id}`} className="group" style={style}>
        <TableCell>
          <input
            type="checkbox"
            checked={selected.includes(a.id)}
            onChange={() => toggleSelect(a.id)}
          />
        </TableCell>
        <TableCell className="whitespace-nowrap">{a.reviewer}</TableCell>
        <TableCell className="max-w-xs truncate text-sm text-gray-600 dark:text-gray-400">
          {a.description || "—"}
        </TableCell>
        <TableCell>
          <span
            className={classNames(
              "px-2 py-0.5 rounded-full text-xs font-semibold capitalize flex items-center gap-1",
              a.state === "approved" &&
                "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
              a.state === "pending" &&
                "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
              a.state === "overdue" &&
                "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
              a.state === "rejected" &&
                "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
            )}
          >
            {a.state === "approved" && <Icon.CheckCircle2 className="w-3 h-3" />}
            {a.state === "pending" && <Icon.Clock className="w-3 h-3" />}
            {a.state === "overdue" && <Icon.AlertTriangle className="w-3 h-3" />}
            {a.state === "rejected" && <Icon.XCircle className="w-3 h-3" />}
            {a.state}
          </span>
        </TableCell>
        <TableCell>
          {a.dueAt ? new Date(a.dueAt).toLocaleDateString() : "—"}
        </TableCell>
        <TableCell>
          {a.signedAt ? new Date(a.signedAt).toLocaleString() : "—"}
        </TableCell>
        <TableCell>{a.required ? "Yes" : "No"}</TableCell>
        <TableCell className="text-right">
          {(canEdit || currentUser === a.reviewer) && (
            <RowMenu>
              {currentUser === a.reviewer && (
                <Menu.Item as={Fragment}>
                  {({ active, close }) => (
                    <button
                      role="menuitem"
                      className={classNames(
                        "w-full px-3 py-2 text-left text-sm",
                        active && "bg-indigo-50 dark:bg-gray-800",
                      )}
                      onClick={() => {
                        close();
                        onSign(a.id);
                      }}
                    >
                      Sign / Approve
                    </button>
                  )}
                </Menu.Item>
              )}
              {canEdit && (
                <Menu.Item>
                  {({ active }) => (
                    <button
                      role="menuitem"
                      className={classNames(
                        "w-full px-3 py-2 text-left text-sm",
                        active && "bg-indigo-50 dark:bg-gray-800",
                      )}
                      onClick={() => onReset(a.id)}
                    >
                      Reset
                    </button>
                  )}
                </Menu.Item>
              )}
              <Menu.Item>
                {({ active }) => (
                  <button
                    role="menuitem"
                    className={classNames(
                      "w-full px-3 py-2 text-left text-sm",
                      active && "bg-indigo-50 dark:bg-gray-800",
                    )}
                    onClick={() => toast("Email sent")}
                  >
                    Send email
                  </button>
                )}
              </Menu.Item>
              {canEdit && (
                <Menu.Item>
                  {({ active }) => (
                    <button
                      role="menuitem"
                      className={classNames(
                        "w-full px-3 py-2 text-left text-sm text-red-600",
                        active && "bg-indigo-50 dark:bg-gray-800",
                      )}
                      onClick={() => onRemove(a.id)}
                    >
                      Remove
                    </button>
                  )}
                </Menu.Item>
              )}
            </RowMenu>
          )}
        </TableCell>
      </TableRow>
    );
  };

  const toggleSelect = (id: string) =>
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );

  const toggleSelectAll = (checked: boolean) => {
    setSelected(checked ? paged.map((a) => a.id) : []);
  };

  const remindSelected = () => {
    if (selected.length === 0) return;
    onBulkReminder(selected);
    toast.success("Reminder sent");
    setSelected([]);
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="border rounded px-2 py-1 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="overdue">Overdue</option>
          <option value="rejected">Rejected</option>
        </select>
        <select
          className="border rounded px-2 py-1 text-sm"
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
        >
          <option value="all">All Roles</option>
          {roles.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1 text-sm">
          <input
            type="checkbox"
            checked={requiredOnly}
            onChange={(e) => setRequiredOnly(e.target.checked)}
          />
          Required only
        </label>
        <input
          type="text"
          placeholder="Search..."
          className="border rounded px-2 py-1 text-sm"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Bulk toolbar */}
      {selected.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-sm">{selected.length} selected</span>
          <Button size="sm" onClick={remindSelected}>Remind</Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => selected.forEach((id) => onReset(id))}
          >
            Reset
          </Button>
        </div>
      )}

      {/* Table */}
      <Table caption="Approvals">
        <TableHeader>
          <TableRow>
            <TableHead>
              <input
                type="checkbox"
                aria-label="Select all"
                checked={selected.length === paged.length && paged.length > 0}
                onChange={(e) => toggleSelectAll(e.target.checked)}
              />
            </TableHead>
            <TableHead>Reviewer</TableHead>
            <TableHead>Role/Step</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Due</TableHead>
            <TableHead>Signed</TableHead>
            <TableHead>Required?</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        {paged.length > 0 ? (
          <List
            height={Math.min(400, paged.length * 56)}
            itemCount={paged.length}
            itemSize={56}
            width="100%"
            outerElementType={TableBody as any}
          >
            {Row}
          </List>
        ) : (
          <TableBody>
            <TableRow>
              <TableCell colSpan={8} className="text-center py-8">
                <div className="text-gray-500 dark:text-gray-400">
                  <p className="text-sm font-medium">No approvals configured</p>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        )}
      </Table>
      {pageCount > 1 && (
        <div className="flex justify-end items-center gap-2 mt-2 text-sm">
          <Button
            size="sm"
            variant="outline"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span>
            Page {page + 1} of {pageCount}
          </span>
          <Button
            size="sm"
            variant="outline"
            disabled={page + 1 >= pageCount}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

