import { PropsWithChildren } from "react";

export function Card({ children }: PropsWithChildren) {
  return <div className="rounded-lg border bg-white p-4 shadow-sm">{children}</div>;
}

export function CardTitle({ children }: PropsWithChildren) {
  return <h3 className="text-base font-semibold text-slate-800 mb-2">{children}</h3>;
}
