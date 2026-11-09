import { Suspense } from "react";
import type { Metadata } from "next";
import { HistoryA } from "@/components/a/History";

export const metadata: Metadata = { title: "Prospects" };

export default function ProspectsPageA() {
  return (
    <Suspense>
      <HistoryA />
    </Suspense>
  );
}
