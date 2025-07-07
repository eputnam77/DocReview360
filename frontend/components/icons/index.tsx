import React from "react";

function createIcon(name: string) {
  return React.forwardRef<SVGSVGElement, React.SVGProps<SVGSVGElement>>((props, ref) => (
    <svg ref={ref} aria-label={name} viewBox="0 0 24 24" {...props} />
  ));
}

export const LayoutDashboard = createIcon("LayoutDashboard");
export const FolderOpen = createIcon("FolderOpen");
export const Workflow = createIcon("Workflow");
export const CirclePlay = createIcon("CirclePlay");
export const Plus = createIcon("Plus");
export const Pencil = createIcon("Pencil");
export const ArrowUpRight = createIcon("ArrowUpRight");
export const LogIn = createIcon("LogIn");
export const FileText = createIcon("FileText");
export const Users2 = createIcon("Users2");
export const BarChart2 = createIcon("BarChart2");
export const RefreshCw = createIcon("RefreshCw");
export const Bold = createIcon("Bold");
export const Italic = createIcon("Italic");
export const Strikethrough = createIcon("Strikethrough");
export const List = createIcon("List");
export const ListOrdered = createIcon("ListOrdered");
export const Undo2 = createIcon("Undo2");
export const Redo2 = createIcon("Redo2");
