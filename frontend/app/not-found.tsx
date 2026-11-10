import Link from "next/link";

export default function NotFound() {
  return (
    <div className="rounded-[10px] border border-line bg-surface px-10 py-9">
      <h1 className="text-2xl font-semibold tracking-[-0.015em]">Page not found</h1>
      <p className="mt-1 max-w-[60ch] text-muted">This address doesn&rsquo;t match any screen. Older links to /a or /b now live at the main addresses.</p>
      <div className="mt-5 flex gap-2">
        <Link href="/" className="btn btn-primary">
          Research a prospect
        </Link>
        <Link href="/prospects" className="btn btn-secondary">
          See prospects
        </Link>
      </div>
    </div>
  );
}
