import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * DataTable — the net-new primitive hi2vi_web lacks (P4.S1). The dashboard's
 * projects / credentials / feedback lists all render tabular data, so this is a
 * headless, token-styled table:
 *
 *  - typed `columns` (a header + a per-row `cell` renderer),
 *  - `rows` + a stable `rowKey`,
 *  - sensible defaults: hairline borders, `text-caption` headers, hover row,
 *    and an `overflow-x-auto` wrapper so a wide table scrolls instead of
 *    breaking the page layout,
 *  - an empty-state slot (`empty`) spanning all columns,
 *  - an optional right-aligned actions column (`actions: true`, or `align`).
 *
 * Purely presentational: all data arrives as props — it never fetches. Later
 * slices (S3/S4/S5) pass server-fetched rows straight in.
 */
export interface DataTableColumn<T> {
  /** Stable column key (also the React key for header/cell nodes). */
  key: string;
  /** Header cell content. */
  header: ReactNode;
  /** Renders the cell for one row. */
  cell: (row: T, index: number) => ReactNode;
  /**
   * Horizontal alignment. Defaults to `left` — or `right` when `actions` is set
   * (actions/numeric columns sit at the trailing edge).
   */
  align?: "left" | "right" | "center";
  /** Marks this as the trailing actions column (right-aligned, tighter). */
  actions?: boolean;
  /** Extra classes applied to this column's header + cells. */
  className?: string;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  /** Stable key for each row. */
  rowKey: (row: T, index: number) => string;
  /** Shown (spanning every column) when `rows` is empty. Defaults to a note. */
  empty?: ReactNode;
  /** Extra classes on the scroll wrapper. */
  className?: string;
}

const alignClass: Record<
  NonNullable<DataTableColumn<unknown>["align"]>,
  string
> = {
  left: "text-left",
  right: "text-right",
  center: "text-center",
};

function resolveAlign<T>(col: DataTableColumn<T>): string {
  return alignClass[col.align ?? (col.actions ? "right" : "left")];
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty = "No items to display.",
  className,
}: DataTableProps<T>) {
  return (
    <div
      className={cn(
        "overflow-x-auto rounded-lg border border-hairline",
        className,
      )}
    >
      <table className="w-full border-collapse text-body-sm">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  "border-b border-hairline bg-surface px-4 py-2 text-micro font-bold tracking-[0.6px] text-steel uppercase",
                  resolveAlign(col),
                  col.className,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-10 text-center text-body-sm text-steel"
              >
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr
                key={rowKey(row, i)}
                className="border-b border-hairline-soft transition-colors last:border-b-0 hover:bg-surface"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      "px-4 py-2 align-middle text-ink",
                      resolveAlign(col),
                      col.className,
                    )}
                  >
                    {col.cell(row, i)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
