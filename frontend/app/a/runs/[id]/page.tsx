import { Suspense } from "react";
import type { Metadata } from "next";
import { RunWorkspaceA } from "@/components/a/RunWorkspace";

export const metadata: Metadata = { title: "Research run" };

export default async function RunPageA({ params }: PageProps<"/a/runs/[id]">) {
  const { id } = await params;
  return (
    <Suspense>
      <RunWorkspaceA runId={id} />
    </Suspense>
  );
}
