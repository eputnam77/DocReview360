import React from "react";

export interface AvatarProps extends React.ImgHTMLAttributes<HTMLImageElement> {}

export function Avatar(props: AvatarProps) {
  return <img {...props} />;
}
