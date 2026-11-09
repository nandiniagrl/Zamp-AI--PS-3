import { Suspense } from "react";
import type { Metadata } from "next";
import { RunWorkspaceB } from "@/components/b/RunWorkspace";

export const metadata: Metadata = { title: "Research run" };

export default async function RunPageB({ params }: PageProps<"/b/runs/[id]">) {
  const { id } = await params;
  return (
    <Suspense>
      <RunWorkspaceB runId={id} />
    </Suspense>
  );
}
