# Choose a provider

For ranked operations use the [available CLI and API routes](rankings.md). If every listed search provider fails, discovery is exhausted, including search via MCP connectors. Move straight to the known primary URL or report the gap. For a known primary URL, remove the failed provider names from the extraction choices before fetching. A Firecrawl search rate limit also crosses off Firecrawl scrape, even when a new ranking prints it first. If Scrapling is the sole surviving route, use `rankings.py extract --only extract=scrapling` and execute its command. A user-selected subset still limits the surviving routes. Otherwise report the search gap. A built-in web search would silently widen the provider list.

| Need | Provider or reference | Capabilities and constraints |
| --- | --- | --- |
| Ordinary web lookup, site/date filters, point-in-time search | [Keenable](keenable.md) | Web search and page Markdown. Respect the configured allowance. |
| News/image verticals or a web coverage gap | [Kagi](kagi.md) | Subscriber search and explicit filters; Quick Answer is synthesis, not primary evidence. |
| Objective plus several related keyword queries | [Parallel](parallel.md) | One objective, repeatable queries, bounded excerpts, domain and freshness controls. Requires working credits. |
| Search with relevant passages or inline Markdown | [Context.dev](extraction.md#contextdev) | Search result content can be requested; `query-fanout` currently has no effect. |
| Search plus scrape, news/images, developer or paper indexes | [Firecrawl](extraction.md#firecrawl) | Combines discovery with extraction. The paper index is distinct from research-category web filtering. |
| Another web index, controlled query expansion, image/video discovery | [Octen](octen.md) | Focused search and explicit broad search; media needs beta entitlement. Installed MCP capabilities lag the HTTP contract. |
| Multi-query search, JS extraction, bounded crawl/map, deep research | Tavily (`tvly`) | `tvly search` accepts up to 5 queries at once; `tvly extract` supports up to 20 URLs and `--extract-depth advanced` for JS pages; `crawl`, `map`, and `research` require auth (`search`/`extract` allow keyless fair-use caps). Passing `-o` without a path writes into `.tavily/`. |
| Pre-extracted grounding, discussions/videos/places, Goggles, AI answers | Brave (`bx`) | Bare `bx "query"` defaults to `context` (LLM grounding), not `web`. Use `bx web --result-filter discussions` for forums, `bx videos` for video metadata, `bx places` for POIs, and `--goggles` for custom re-ranking. `bx answers` (and `--enable-research`) streams synthesis, not raw source passages. |
| Raw search results vs sourced answers, HTML/PDF fetch | Linkup (`linkup`) | `linkup search` defaults to synthesized `sourcedAnswer`; pass `--output search-results` (check `--help` for exact flag casing) for primary search results. Use `linkup fetch URL` for known HTML/PDF pages instead of search. |
| Visual video/YouTube analysis and multimodal document inspection | Gemini API (`gemini-api`) | Standard `gemini-api analyze -i <URL-or-file>` inspects visual frames and audio in YouTube URLs or local media; see [Media](media.md#visual-video-and-youtube-analysis). |
| Repository discovery / README inspection | [Gitquarry](github.md) | Repository filters and optional reranking. Exact API usage across repositories belongs to `gh search code`. |
| Reddit opinions, posts, comments or communities | [Reddit CLI](reddit.md) | Search engines can discover URLs; inspect Reddit content only through `reddit` (`reddit-cli`, live OAuth or Arctic Shift archive). |
| Known URLs / local files | [Extraction](extraction.md) | Ranked hosted extraction, local parsers, raw readers and document conversion have different purposes. |
| Image/video search or transcripts | [Media](media.md) | Search results, captions and transcribed audio are distinct evidence. |
| Bounded entity discovery | [Entity discovery](entities.md) | FindAll returns entities, not pages; separate from narrative deep research. |
| Existing research run status or results | [Existing runs](deep-research.md#existing-runs) | Retrieve the supplied run; do not create a replacement job. |
| Requested or task-warranted deep research | [Starting deep research](deep-research.md#starting-deep-research) | Choose sustained investigation when the evidence work warrants it; honor scope, speed and spending limits. |

## Capability and access checks

Before the first unfamiliar call, inspect installed `--help` or the mounted MCP schema. Local source checkouts may lag the executable. Authentication presence is not proof of working access. An authenticated search does not prove image/video entitlement, deep-research access or remaining credit.

For high-impact claims, verify independent original sources. Multiple engines can return the same page.
