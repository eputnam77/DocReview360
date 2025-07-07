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
