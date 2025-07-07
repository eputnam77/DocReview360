import React from "react";

export type LabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(({ children, ...props }, ref) => (
  <label ref={ref} {...props}>{children}</label>
));
Label.displayName = "Label";
