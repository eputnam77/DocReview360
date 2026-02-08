import dynamic from "next/dynamic";
import React, { useEffect, useRef, useState } from "react";
const MenuIcon = dynamic(() => import("lucide-react").then(m => m.Menu));
const TableIcon = dynamic(() => import("lucide-react").then(m => m.Table));
const ImageIcon = dynamic(() => import("lucide-react").then(m => m.Image));
export default function InsertMenu({ insertTable, insertImage, disabled = false }) {
    const [open, setOpen] = useState(false);
    const menuRef = useRef(null);
    useEffect(() => {
        if (disabled && open) {
            setOpen(false);
        }
    }, [disabled, open]);
    useEffect(() => {
        if (!open)
            return;
        function handleMouseDown(e) {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                setOpen(false);
            }
        }
        function handleKeyDown(e) {
            if (e.key === "Escape") {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", handleMouseDown);
        document.addEventListener("keydown", handleKeyDown);
        return () => {
            document.removeEventListener("mousedown", handleMouseDown);
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [open]);
    return (<div className="relative" ref={menuRef}>
      <button onClick={() => {
            if (disabled)
                return;
            setOpen(prev => !prev);
        }} className={`ml-2 p-2 rounded bg-gray-200 ${disabled ? "opacity-50 cursor-not-allowed" : ""}`} title="Insert" disabled={disabled}>
        <MenuIcon className="w-4 h-4"/>
      </button>
      {open && (<div className="absolute right-0 mt-1 bg-white border rounded shadow-md z-10">
          <button onClick={() => {
                insertTable();
                setOpen(false);
            }} className="flex items-center gap-2 px-2 py-1 hover:bg-gray-100 w-full text-left" title="Insert Table">
            <TableIcon className="w-4 h-4"/> Table
          </button>
          <button onClick={() => {
                insertImage();
                setOpen(false);
            }} className="flex items-center gap-2 px-2 py-1 hover:bg-gray-100 w-full text-left" title="Insert Image">
            <ImageIcon className="w-4 h-4"/> Image
          </button>
        </div>)}
    </div>);
}
