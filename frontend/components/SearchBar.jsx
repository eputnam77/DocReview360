import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
export default function SearchBar() {
    const router = useRouter();
    const [query, setQuery] = useState("");
    function onSubmit(e) {
        e.preventDefault();
        if (query.trim()) {
            router.push(`/search?q=${encodeURIComponent(query.trim())}`);
        }
    }
    return (<form onSubmit={onSubmit} className="flex items-center gap-2 px-2 py-2">
      <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search..." className="h-8 text-sm"/>
      <button type="submit" aria-label="Search">
        <span className="w-4 h-4 text-gray-500">🔍</span>
      </button>
    </form>);
}
