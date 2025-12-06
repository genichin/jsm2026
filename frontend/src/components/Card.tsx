import { PropsWithChildren } from "react";

export function Card({ children }: PropsWithChildren) {
  return <div className="rounded-md border border-gh-border-default bg-gh-canvas-default p-4">{children}</div>;
}

export function CardTitle({ children }: PropsWithChildren) {
  return <h3 className="text-base font-semibold text-gh-fg-default mb-2">{children}</h3>;
}
