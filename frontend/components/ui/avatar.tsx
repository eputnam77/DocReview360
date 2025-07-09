// frontend/components/ui/avatar.tsx

import * as React from "react";

export interface AvatarProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  size?: number; // px
  fallback?: React.ReactNode;
}

export function Avatar({
  src,
  alt,
  size = 36,
  fallback,
  ...props
}: AvatarProps) {
  const [errored, setErrored] = React.useState(false);

  return (
    <span
      className="inline-flex items-center justify-center overflow-hidden rounded-full border border-gray-200 bg-gray-100 dark:bg-gray-800"
      style={{ width: size, height: size }}
      aria-label={alt}
    >
      {src && !errored ? (
        <img
          src={src}
          alt={alt}
          width={size}
          height={size}
          className="object-cover w-full h-full"
          onError={() => setErrored(true)}
          {...props}
        />
      ) : fallback ? (
        fallback
      ) : (
        // If no src or load error, show fallback (initials or icon)
        <span className="text-xs text-gray-400 dark:text-gray-500 font-semibold">
          {alt
            ? alt
                .split(" ")
                .map((w) => w[0])
                .join("")
                .toUpperCase()
                .slice(0, 2)
            : "?"}
        </span>
      )}
    </span>
  );
}
