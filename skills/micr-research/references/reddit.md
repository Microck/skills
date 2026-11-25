# Reddit research

Use the `reddit` CLI ([Microck/reddit-cli](https://github.com/Microck/reddit-cli), install from GitHub Releases or `cargo install reddit-cli --locked`) for all Reddit post/comment inspection, subreddit browsing, searches and user activity. General web search can discover thread URLs, but it does not replace reading the threads through `reddit`. If `reddit` is not installed, do not scrape Reddit; report that Reddit threads were not checked and include the install link/command once at the end of the answer.

## Workflow

1. Define the topic, date range and relevant communities. For discovery, use an ordinary search engine with `site:reddit.com` or `reddit search` directly.
2. Inspect the strongest relevant threads with `reddit thread URL_OR_ID`. Use `--comment ID` to focus on a specific comment permalink, or `--full` (on `live`) to expand hidden replies within `--max-requests`.
3. Compare multiple discussions and dates. Distinguish the post's claim from commenters' experiences. Upvotes and karma measure reception, not expertise or factual truth.
4. Check `meta.notes` in JSON output for source caveats or partial multi-subreddit failures. Cite direct post/comment links and dates. State sampling and community bias; verify factual claims against primary sources outside Reddit.

## Commands

```bash
reddit search "TOPIC" --sub SUBREDDIT --type posts --limit 25
reddit search "TOPIC" --sub SUB1 --sub SUB2 --type comments --limit 25
reddit thread "REDDIT_POST_URL"
reddit thread "REDDIT_POST_URL" --comment COMMENT_ID
reddit sub SUBREDDIT --sort new --limit 25
reddit about SUBREDDIT
reddit user USERNAME --posts
reddit cache search "FTS_QUERY"
```

- Use subreddit names without `r/` and usernames without `u/`. Inspect `reddit COMMAND --help` before adding unfamiliar flags.
- Output defaults to JSON when piped (`--format json`, `jsonl`, or `md` for reading). Save large threads with `-o FILE`.
- Local SQLite store caches fetched items for 30 days by default; use `--offline` to query only cached items, `--refresh` to bypass cache reads, or `--no-cache` to skip caching.

## Data sources and auth

| Source | Behavior |
| --- | --- |
| `auto` (default) | Uses `live` when Reddit OAuth credentials resolve, and `archive` otherwise. |
| `live` | Reddit Data API via app-only OAuth (`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` or `reddit auth login`). Best for live rankings and full Reddit search. |
| `archive` | Arctic Shift archive, requiring **no credentials**. Best for comment search and date/author filters. Post/comment searches require `--sub` or `--author`; `reddit sub` uses `--sort new`; scores and comment counts are snapshots. |

Set the source with `--source`, `REDDIT_CLI_SOURCE`, or `config.toml`. Reuse existing auth (`reddit auth status`); never print credentials or start login without authorization. Report access, rate-limit or transport failures instead of switching to direct Reddit HTTP, Firecrawl, Scrapling or another scraper.

Evidence: inspected `Microck/reddit-cli` README and command surface on 2026-11-24.
