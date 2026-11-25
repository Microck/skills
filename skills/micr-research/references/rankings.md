# Provider rankings

From the skill directory run `python3 scripts/rankings.py CATEGORY` (on Windows, `py -3 scripts/rankings.py CATEGORY`). Requires Python 3.9+ and a matching CLI on PATH or a configured API search credential. Each line names the actual executable, native arguments and the evidence behind its position. Substitute the user's input as an argument. The preflight may inspect CLI help to distinguish programs with the same executable name. It checks whether the required environment variables are set. Only the actual provider request verifies account access. Skip accounts without authorized access or budget.

- `search`, `news` and `papers` use NEEDLE's seven-day Overall, News and Scholar scores respectively. Higher share of the benchmark ceiling ranks first. Output shows the benchmark date for that metric. Only matching web search modes receive a score. When the request explicitly requires a publisher's news feed or a dedicated paper index, use the corresponding native vertical directly. [NEEDLE results](https://keenableai.github.io/needle/results/) · [Search adapters](https://github.com/keenableai/needle/tree/main/src/needle/shared/search)
- `deep-search` uses [Artificial Analysis DeepSearchQA](https://artificialanalysis.ai/agents/search-api) to rank multi-step searches. `deep-research` covers finished research jobs. Images, extraction and finished jobs use their own measurements and defaults.
- The first relevant lookup after seven days checks the public benchmark feed. Failed refreshes retain the last usable snapshot and retry after an hour. `--offline` uses the bundled or cached data. Cache files live under `$XDG_CACHE_HOME/research-skill` or `~/.cache/research-skill`.
- Bundled NEEDLE scores come from the [results feed](https://keenableai.github.io/needle/results.json) by Styskin, Petri and Gusev, distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The command selects the matching metric and displays its share as a percentage.

## Codex sessions using ranked web providers

For a session where web lookups must go through the skill’s providers, start Codex CLI with its built-in web search disabled:

```sh
codex -c 'web_search="disabled"'
```

The same override works with `codex exec`. It applies to that invocation. Provider CLIs still run in the shell when the session permits network access. MCP servers and other integrations have their own permissions. A skill can guide choices in an existing session; the runtime controls which tools the agent can call.

## Choose providers for a task

For “use Brave and Tavily for search, and Firecrawl for extraction,” run these from the skill directory:

```sh
python3 scripts/rankings.py search --only search=brave,tavily --only extract=firecrawl
python3 scripts/rankings.py extract --only search=brave,tavily --only extract=firecrawl
```

Each selection applies to its named category for this invocation. Give one comma-separated list per category. NEEDLE orders the eligible search modes within the list. Other categories keep their usual rankings unless you select providers for them too. The same flags limit which providers an explicit benchmark can call. Fallback stays inside the list, including local Scrapling only when selected for a restricted extraction task.

Use a supported executable name or the provider names Brave (`bx`), Tavily (`tvly`), Parallel (`parallel-cli`), and Context.dev (`context-dev`). Names are case-insensitive. An unsupported choice reports the supported names for that category. A supported but missing CLI is skipped with a diagnostic. If none of the selected CLIs is installed, the command stops.

### Official search CLI coverage

Search, news and paper discovery accept the verified search commands below in addition to Brave, Tavily, Linkup, Keenable, Parallel, Context.dev and Firecrawl. Users install and authenticate each provider's own CLI. NEEDLE's weekly feed supplies scores for the matching modes.

| Provider | Executable and search operation |
| --- | --- |
| Perplexity | [pplx search web](https://github.com/perplexityai/perplexity-cli), standard search with low context |
| Octen | [octen search](https://github.com/Octen-Team/octen-cli), standard English results with highlights |
| Jina | [jina search](https://github.com/jina-ai/cli), from the jina-cli package |
| TinyFish | [tinyfish search query](https://docs.tinyfish.ai/cli/commands), its web search operation |
| OpenAI | [openai responses create](https://github.com/openai/openai-cli), GPT-5.5 with web search |
| Anthropic | [ant messages create](https://github.com/anthropics/anthropic-cli), Claude Sonnet 5 with one web search |

For model-backed searches, confirm the user's budget covers model tokens and web search. Preserve each query as one argument and JSON-encode it when inserting it into a structured argument. If an older or unrelated program shares the executable name, check its subcommand help and skip it if the required operation is missing.

API modes in the November 23 snapshot include Exa (Auto and Lite), Perplexity Fast, WebIQ, You.com, DeepSeek, Seltz, Kagi, Google via Serper and Bing via SearchAPI. They use the bundled Python search command. Only configured modes enter the rankings. A key enables a route locally; account entitlements and quotas determine whether a live request succeeds. [NEEDLE adapters](https://github.com/keenableai/needle/tree/main/src/needle/shared/search)

| Selection | Credential environment variable |
| --- | --- |
| `exa` (highest ranked of Auto and Lite), `exa-auto`, `exa-lite` | `EXA_API_KEY` |
| `perplexity-fast` | `PERPLEXITY_API_KEY` |
| `webiq` | `WEBIQ_API_TOKEN` |
| `you` | `YOU_API_KEY` |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `seltz` | `SELTZ_API_KEY` |
| `kagi` | `KAGI_API_KEY` |
| `google` (Serper) | `SERPER_API_KEY` |
| `bing` (SearchAPI) | `SEARCHAPI_API_KEY` |

Use `--only search=perplexity` to rank both the native standard mode and the keyed Fast mode. Use `pplx` to select only the CLI. A provider appears once at its highest eligible score. The same selection rules apply to news and papers. Enter credentials through your shell or secret manager. The helper sends one request to the selected service and prints its JSON response for source inspection (up to 8 MiB).

## Extraction costs

`extract` lists installed hosted CLIs first. A hosted provider qualifies for price-first ranking after at least three completed benchmark cases and an 80% passage-retrieval rate. Among qualifying providers, the lowest estimated USD per 1,000 usable pages wins. Divide the rate per 1,000 one-page requests by the observed pass rate. This estimate assumes the listed rate for each attempt. Equal estimates favor preserving the highest-ranked installed search provider for search. Reliable hosts with unknown prices come next, followed by other hosted options. Scrapling is the final local fallback.

The bundled rates use ordinary single-page Markdown extraction, checked November 23, 2026. Monthly plan estimates assume full use of the included credits. Unused free allowances, overages and negotiated rates can change the order.

| Official CLI | USD / 1,000 requests | Price basis |
| --- | ---: | --- |
| firecrawl | 3.80 | Hobby monthly, $19 for 5,000 standard pages. [Pricing](https://www.firecrawl.dev/pricing) |
| keenable | 4.00 | Standard rate after the free shared allowance. [Billing](https://docs.keenable.ai/credits.md) |
| context-dev | 2.00 | Developer monthly, $20 for 10,000 one-page crawls. [Pricing](https://context.dev/pricing) |
| parallel-cli | 1.00 | Extract per 1,000 URLs. [Pricing](https://docs.parallel.ai/resources/pricing.md) |
| tvly | Unknown | Basic extraction is quoted per five successful URLs. Set the effective rate for your single-URL requests. [Billing](https://docs.tavily.com/documentation/api-credits.md) |

For account-specific rates, set `RESEARCH_EXTRACT_PRICES` to the path of a JSON file like `{"firecrawl": 0.99, "keenable": 0}`. Keys are hosted CLI names. Omitted keys keep published rates. Use zero only while your available allowance covers those calls. The preflight reads the file locally and accepts no credentials. A publisher can update the public estimates with the optional `extract_usd_per_1000` map in its rankings feed.

## Check installed tools

Run this manually when auditing or setting up a machine (not during ordinary lookups):

```sh
python3 scripts/rankings.py check
```

It prints a `[x]` / `[ ]` checklist of all supported ranked CLIs, API-only search environment variables (presence only, never values), and specialist tools (extraction, GitHub, media/transcription, and Kagi). It makes no network requests.

## Reproduce a comparison

```sh
python3 scripts/rankings.py benchmark extract
python3 scripts/rankings.py benchmark images
```

These optional commands make live requests using the installed official CLIs and their normal account configuration. Each eligible tool receives the same public cases. Extraction checks expected passages. Image search checks relevant words and image URLs in the top results, and reports source-page availability separately; it does not assess visual similarity or licensing. Only providers completing every case get a local ranking. Errors and incomplete runs are reported separately. Local results for a provider override published measurements. Run again after changing tools or accounts.

## Distribute updated measurements

A publisher can host [provider-scores.json](provider-scores.json) over HTTPS and set its public URL in the bundled file's optional `update_url` field, or users can set `RESEARCH_RANKINGS_URL`. The preflight checks that feed at most weekly after a successful refresh. Publish a dated, complete snapshot with numeric scores for the same tasks across providers. For example, an extraction score goes under `categories.extract`, keyed by executable name, with integer `passed` and `total` fields. Downloads supply data only. Commands stay in the installed script. NEEDLE and AA refresh independently of this optional feed.

The initial November 23 extraction snapshot scored Keenable, Firecrawl and Scrapling on three public pages. The image snapshot scored Firecrawl on two searches. The fresh test machine had no Tavily credentials and received no scorable Tavily responses. A small perfect score on these cases establishes coverage of these examples only.
