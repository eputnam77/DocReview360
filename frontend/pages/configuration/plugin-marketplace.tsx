import React, { useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";

export default function PluginMarketplace() {
  const [items, setItems] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API}/plugin-marketplace`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setItems(Array.isArray(data) ? data : []))
      .catch(() => setItems(["grammar-plugin", "demo-extension"]));
  }, []);

  const install = async (name: string) => {
    try {
      await fetch(`${API}/plugin-marketplace/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      alert(`Installed ${name}`);
    } catch {
      alert("Install failed");
    }
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Plugin Marketplace</h1>
      <Table className="min-w-full text-sm">
        <TableHeader>
          <TableRow>
            <TableHead>Plugin</TableHead>
            <TableHead>Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((name) => (
            <TableRow key={name}>
              <TableCell>{name}</TableCell>
              <TableCell>
                <Button onClick={() => install(name)}>Install</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
