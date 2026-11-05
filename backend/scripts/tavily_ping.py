"""Phase 2 connectivity check (costs 1 free credit; a repeat within 24h costs 0 thanks to the cache).

  python -m scripts.tavily_ping "Stripe announcements" --topic news --max 5
"""
import argparse

from app.tools import tavily_client


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="Stripe announcements")
    ap.add_argument("--topic", default="news", choices=["general", "news"])
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--time-range", default="month", choices=["day", "week", "month", "year"])
    args = ap.parse_args()

    resp = tavily_client.search(args.query, branch="ping", topic=args.topic, max_results=args.max, time_range=args.time_range)
    if resp.error:
        print(f"ERROR: {resp.error}")
        return 1
    print(f'Query: "{resp.query}"  topic={args.topic}  results={len(resp.results)}  '
          f"credits used={resp.credits}  cached={resp.cached}\n")
    for i, r in enumerate(resp.results, 1):
        print(f"{i}. {r.title}")
        print(f"   {r.url}")
        print(f"   domain={r.domain}  date={r.published_date or 'n/a'}  score={r.score}")
        print(f"   {r.content[:200].strip()}…\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
