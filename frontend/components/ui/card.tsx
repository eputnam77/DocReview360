import React from "react";

export type CardProps = React.HTMLAttributes<HTMLDivElement>;
export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;
export type CardTitleProps = React.HTMLAttributes<HTMLHeadingElement>;
export type CardDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;
export type CardContentProps = React.HTMLAttributes<HTMLDivElement>;
export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>;

export function Card(props: CardProps) {
  return <div {...props} />;
}

export function CardHeader(props: CardHeaderProps) {
  return <div {...props} />;
}

export function CardTitle(props: CardTitleProps) {
  return <h3 {...props} />;
}

export function CardDescription(props: CardDescriptionProps) {
  return <p {...props} />;
}

export function CardContent(props: CardContentProps) {
  return <div {...props} />;
}

export function CardFooter(props: CardFooterProps) {
  return <div {...props} />;
}
