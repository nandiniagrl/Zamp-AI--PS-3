import { Suspense } from "react";
import type { Metadata } from "next";
import { HistoryB } from "@/components/b/History";

export const metadata: Metadata = { title: "Prospects" };

export default function ProspectsPageB() {
  return (
    <Suspense>
      <HistoryB />
    </Suspense>
  );
}
