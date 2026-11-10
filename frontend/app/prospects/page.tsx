import { Suspense } from "react";
import type { Metadata } from "next";
import { History } from "@/components/workspace/History";

export const metadata: Metadata = { title: "Prospects" };

export default function ProspectsPage() {
  return (
    <Suspense>
      <History />
    </Suspense>
  );
}
