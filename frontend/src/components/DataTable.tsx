"use client";
import * as React from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";

type Props<T> = {
  columns: ColumnDef<T, any>[];
  data: T[];
};

export function DataTable<T extends object>({ columns, data }: Props<T>) {
  const table = useReactTable({ columns, data, getCoreRowModel: getCoreRowModel() });
  return (
    <div className="overflow-x-auto border border-gh-border-default rounded-md">
      <table className="min-w-full">
        <thead className="bg-gh-canvas-subtle">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-gh-border-default">
              {hg.headers.map((header) => (
                <th key={header.id} className="px-3 py-2 text-left text-xs font-semibold text-gh-fg-muted">
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-b border-gh-border-default hover:bg-gh-canvas-subtle transition-colors">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-3 text-sm text-gh-fg-default">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
