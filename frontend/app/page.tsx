import Link from "next/link";
import { CardFileMark, ProofMark } from "@/components/shared/ui";

/** Temporary chooser while both design directions are built side by side (removed once one is kept). */
export default function Home() {
  return (
    <main className="dir-a flex min-h-dvh items-center justify-center px-6">
      <div className="w-full max-w-[640px]">
        <h1 className="text-2xl font-semibold tracking-[-0.01em]">Outreach Copilot</h1>
        <p className="mt-1 text-muted">Two design directions share the same backend and data. Open either one; a run started in one appears in both.</p>
        <div className="mt-6 grid grid-cols-2 gap-4">
          <Link href="/a" className="panel flex items-start gap-3 p-5 transition-colors duration-150 hover:border-control">
            <CardFileMark size={28} />
            <span>
              <span className="block font-semibold">A — The card file</span>
              <span className="mt-1 block text-sm text-muted">Sidebar workspace; verified facts on a ruled prospect card.</span>
            </span>
          </Link>
          <Link href="/b" className="panel flex items-start gap-3 p-5 transition-colors duration-150 hover:border-control">
            <ProofMark size={28} />
            <span>
              <span className="block font-semibold">B — The checked proof</span>
              <span className="mt-1 block text-sm text-muted">Top bar and proof sheet; claims highlighted with sources in the margin.</span>
            </span>
          </Link>
        </div>
      </div>
    </main>
  );
}
