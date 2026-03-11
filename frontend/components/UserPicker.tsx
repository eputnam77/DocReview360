// UserPicker — debounced typeahead for selecting users (Item 44 Phase 1)
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { authenticatedFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface UserOption {
  username: string;
  display_name?: string;
  active?: boolean;
}

interface UserPickerProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
}

export default function UserPicker({
  value,
  onChange,
  placeholder = "Search for a user…",
  disabled = false,
  className,
  id,
}: UserPickerProps) {
  const [inputValue, setInputValue] = useState(value);
  const [suggestions, setSuggestions] = useState<UserOption[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeIdx, setActiveIdx] = useState(-1);

  // Sync external value changes
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const res = await authenticatedFetch(`/users/search?q=${encodeURIComponent(q)}&limit=10`);
      if (res.ok) {
        const data: UserOption[] = await res.json();
        setSuggestions(data);
        setOpen(data.length > 0);
        setActiveIdx(-1);
      }
    } catch {
      // Ignore errors — just show no suggestions
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setInputValue(q);
    // If cleared, reset parent value
    if (!q.trim()) onChange("");
    // Debounce
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(q), 250);
  };

  const selectUser = (user: UserOption) => {
    onChange(user.username);
    setInputValue(user.username);
    setOpen(false);
    setSuggestions([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      selectUser(suggestions[activeIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <Input
        id={id}
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => { if (suggestions.length > 0) setOpen(true); }}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-haspopup="listbox"
      />
      {loading && (
        <span className="absolute right-2 top-2.5 text-xs text-gray-400">…</span>
      )}
      {open && suggestions.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-50 mt-1 w-full rounded-md border bg-white shadow-lg max-h-48 overflow-y-auto text-sm"
        >
          {suggestions.map((u, idx) => (
            <li
              key={u.username}
              role="option"
              aria-selected={idx === activeIdx}
              className={cn(
                "cursor-pointer px-3 py-2 hover:bg-indigo-50",
                idx === activeIdx && "bg-indigo-100",
              )}
              onMouseDown={() => selectUser(u)}
            >
              <span className="font-medium">{u.username}</span>
              {u.display_name && u.display_name !== u.username && (
                <span className="ml-2 text-gray-500">{u.display_name}</span>
              )}
              {u.active === false && (
                <span className="ml-2 text-xs text-amber-500">(inactive)</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
