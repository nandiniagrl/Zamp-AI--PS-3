import { Suspense } from "react";
import type { Metadata } from "next";
import { RunWorkspace } from "@/components/workspace/RunWorkspace";

export const metadata: Metadata = { title: "Research run" };

export default async function RunPage({ params }: PageProps<"/runs/[id]">) {
  const { id } = await params;
  return (
    <Suspense>
      <RunWorkspace runId={id} />
    </Suspense>
  );
}
