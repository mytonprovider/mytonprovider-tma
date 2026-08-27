import { Card } from "@/components/Card";
import { FieldRow } from "@/components/FieldRow";
import type { ReactNode } from "react";

export interface Field {
  label: ReactNode;
  value: ReactNode;
}

export function FieldCard({ rows }: { rows: Field[] }) {
  return (
    <Card>
      {rows.map((row, index) => (
        <FieldRow key={index} label={row.label} value={row.value} divider={index > 0} />
      ))}
    </Card>
  );
}
