export type Column<T> = {
  key: keyof T;
  header: string;
  align?: "left" | "right";
  format?: (value: T[keyof T], row: T) => React.ReactNode;
};

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  rowKey,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, i: number) => string;
}) {
  return (
    <div
      className="overflow-x-auto rounded-lg border"
      style={{ borderColor: "rgba(255,255,255,0.1)" }}
    >
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
            {columns.map((c) => (
              <th
                key={String(c.key)}
                className="whitespace-nowrap px-3 py-2 font-medium"
                style={{
                  textAlign: c.align ?? "left",
                  color: "#898781",
                }}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={rowKey(row, i)}
              style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
            >
              {columns.map((c) => (
                <td
                  key={String(c.key)}
                  className="tabular whitespace-nowrap px-3 py-2"
                  style={{ textAlign: c.align ?? "left" }}
                >
                  {c.format ? c.format(row[c.key], row) : String(row[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <div className="px-3 py-6 text-center text-sm" style={{ color: "#898781" }}>
          No rows to show.
        </div>
      )}
    </div>
  );
}
