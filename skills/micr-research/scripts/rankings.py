#!/usr/bin/env python3
"""Print native CLI routes; run providers only for an explicit benchmark."""
import argparse
import hashlib
import math
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import subprocess
import tempfile
from urllib.parse import urlsplit
from http.client import HTTPException
import urllib.request

from search_api import MODES as API_MODES, credential_for
from aa_rankings import fetch_rankings
from provider_benchmarks import benchmark

REFERENCES = Path(__file__).resolve().parents[1] / "references"
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "research-skill"
WEEK = timedelta(days=7)
# Templates are local code. Rankings downloads contain measurements only.
AA_SEARCH = [
    ("parallel-cli", 'search --mode advanced --max-results 10 --query "QUERY" "OBJECTIVE"', "Parallel Search (advanced, objective)"),
    ("parallel-cli", 'search --mode fast --max-results 10 --query "QUERY" "OBJECTIVE"', "Parallel Search (fast, objective)"),
    ("keenable", 'search --mode pro --max-results 10 "QUERY"', "Keenable Search (pro)"),
    ("keenable", 'search --mode realtime --max-results 10 "QUERY"', "Keenable Search (realtime)"),
    ("firecrawl", 'search "QUERY" --sources web --no-domain-tools --limit 10 --json', "Firecrawl Search"),
    ("tvly", 'search "QUERY" --depth basic --max-results 10 --json', "Tavily Search (basic)"),
    ("linkup", '--json search "QUERY" --depth fast --output search-results --max-results 10', "Linkup Search (fast)"),
    ("linkup", '--json search "QUERY" --depth standard --output search-results --max-results 10', "Linkup Search (standard)"),
    ("bx", 'context "QUERY" --count 10', "Brave Search (LLM context)"),
    ("bx", 'web "QUERY" --result-filter web --count 10', "Brave Search (web)"),
    ("linkup", '--json search "QUERY" --depth flash --output search-results --max-results 10', "Linkup Search (flash, alpha)"),
    ("parallel-cli", 'search --mode basic --max-results 10 --query "QUERY"', "Parallel Search (basic)"),
    ("parallel-cli", 'search --mode turbo --max-results 10 --query "QUERY"', "Parallel Search (turbo)"),
    ("context-dev", 'web search --query "QUERY"', None),
]
NEEDLE_URL = "https://keenableai.github.io/needle/results.json"
NEEDLE_METRICS = {"search": "overall", "news": "news", "papers": "scholar"}
# Engine IDs refer to NEEDLE's public search adapters. Parallel uses a query
# alone in this benchmark; AA also evaluates modes that take an objective.
# Retrieval instructions and tool budgets from NEEDLE's llmsearch adapters.
SEARCH_PROMPT = (
    "Call the web search tool exactly once, passing the user's message verbatim as the "
    "query: do not rewrite, shorten, or drop any part of it, including operators such as "
    "site: or after:. Then reply with only a JSON array, no prose and no code fence: one "
    "object per search result you received, in the order received, with keys url, title, "
    "snippet. Copy the snippet text verbatim from the search result; do not paraphrase or "
    "summarize."
)

NEEDLE_SEARCH = [
    *((mode, f'scripts/search_api.py {mode} -- "QUERY"', mode) for mode in API_MODES),
    ("pplx", 'search web "QUERY" -n 10 --search-context-size low', "perplexity"),
    ("jina", 'search "QUERY" -n 10 --json', "jina"),
    ("octen", 'search "QUERY" -n 10 --highlight --highlight-max-tokens 512 --language en --safesearch off --json', "octen"),
    ("tinyfish", 'search query "QUERY"', "tinyfish"),
    ("openai", 'responses create --model gpt-5.5 --reasoning.effort low --max-output-tokens 32000 '
     """--tool '{"type":"web_search","search_context_size":"low"}' --tool-choice '{"type":"web_search"}' """
     """--include '["web_search_call.action.sources"]' """
     f'--instructions "{SEARCH_PROMPT}" --input "QUERY"', "chatgpt-search"),
    ("ant", 'messages create --model claude-sonnet-5 --max-tokens 32000 '
     """--tool '{"type":"web_search_20250305","name":"web_search","max_uses":1}' """
     f'--system {shlex.quote(json.dumps(SEARCH_PROMPT))} '
     """--message '{"role":"user","content":"QUERY"}'""", "claude-search"),
    ("keenable", 'search --mode realtime --max-results 10 "QUERY"', "keenable-realtime"),
    ("keenable", 'search --mode pro --max-results 10 "QUERY"', "keenable"),
    ("context-dev", 'web search --query "QUERY" --country us --num-results 10', "context"),
    ("parallel-cli", 'search --mode advanced --max-results 10 --query "QUERY"', "parallel"),
    ("parallel-cli", 'search --mode fast --max-results 10 --query "QUERY"', "parallel-fast"),
    ("parallel-cli", 'search --mode turbo --max-results 10 --query "QUERY"', "parallel-turbo"),
    ("firecrawl", 'search "QUERY" --sources web --no-domain-tools --limit 10 --json', "firecrawl"),
    ("tvly", 'search "QUERY" --depth basic --max-results 10 --json', "tavily"),
    ("bx", 'context "QUERY" --count 10', "brave-llmcontext"),
    ("bx", 'web "QUERY" --result-filter web --count 10', "brave"),
    ("linkup", '--json search "QUERY" --depth standard --output search-results --max-results 10', "linkup"),
]
ROUTES = {
    "search": NEEDLE_SEARCH,
    "deep-search": AA_SEARCH,
    "extract": [
        ("keenable", 'fetch "URL" --live'), ("context-dev", 'web web-crawl-md --url "URL" --max-depth 0 --max-pages 1 --use-main-content-only --wait-for-ms 0'),
        ("firecrawl", 'scrape "URL" --only-main-content'), ("parallel-cli", 'extract "URL" --full-content'),
        ("tvly", 'extract "URL" --format markdown --json'),
        ("scrapling", 'extract get "URL" page.txt --no-stealthy-headers'),
    ],
    "news": [("firecrawl", 'search "QUERY" --sources news', None), ("tvly", 'search "QUERY" --topic news --json', None), *NEEDLE_SEARCH],
    "images": [("firecrawl", 'search "QUERY" --sources images --limit 5 --json'),
               ("tvly", 'search "QUERY" --depth basic --max-results 5 --include-images --include-image-descriptions --json'),
               ("linkup", '--json search "QUERY" --depth fast --output search-results --include-images --max-results 5'),
               ("bx", 'images "QUERY" --count 5')],
    "papers": [("firecrawl", 'research search-papers "QUERY" --limit 5 --json', None), *NEEDLE_SEARCH],
    "deep-research": [("parallel-cli", 'research run "QUESTION" --processor lite-fast --text'),
                      ("context-dev", 'web answers --task "QUESTION" --mode ultra')],
}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def store(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        temporary = Path(handle.name)
        try:
            json.dump(payload, handle, allow_nan=False)
            handle.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def observation_date(record):
    return date.fromisoformat(record["as_of"])


def valid_aa(data):
    try:
        observation_date(data)
        return bool(data["rows"]) and all(
            isinstance(row, dict) and all(
                type(row.get(k)) in (int, float) and math.isfinite(row[k]) and row[k] >= 0
                for k in ("quality", "deepsearchqa", "latency"))
            for row in data["rows"].values())
    except (TypeError, ValueError, KeyError, AttributeError):
        return False


def recently_written(path, interval):
    try:
        stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except FileNotFoundError:
        return False
    return datetime.now(timezone.utc) - stamp < interval


def permit_refresh(cache):
    # Avoid repeatedly delaying preflight on a network outage. The timestamp
    # records an attempt, independently of the last usable measurement.
    attempt = cache.with_suffix(".attempt")
    if recently_written(attempt, timedelta(hours=1)):
        return False
    try:
        attempt.parent.mkdir(parents=True, exist_ok=True)
        attempt.touch()
    except OSError:
        pass
    return True


def needle_table(feed):
    vertical_metrics = (NEEDLE_METRICS["news"], NEEDLE_METRICS["papers"])
    dates = {"overall": date.fromisoformat(feed["updated"][:10])}
    for vertical in feed["verticals"]:
        if vertical["id"] in vertical_metrics and vertical["runs"] > 0:
            dates[vertical["id"]] = date.fromisoformat(vertical["last_run"][:10])
    if dates.keys() != set(NEEDLE_METRICS.values()):
        raise ValueError("Missing NEEDLE run dates")
    rows = {}
    for engine in feed["engines"]:
        engine_id = engine["engine_id"]
        if not isinstance(engine_id, str) or not engine_id or engine_id in rows:
            raise ValueError("Invalid NEEDLE engine ID")
        scores = {"overall": engine["overall"]}
        for metric in vertical_metrics:
            scores[metric] = (engine["verticals"].get(metric) or {}).get("share")
        for score in scores.values():
            if score is not None and (type(score) not in (int, float) or not 0 <= score <= 1):
                raise ValueError("Invalid NEEDLE share")
        rows[engine_id] = scores
    for metric in dates:
        if not any(rows.get(engine_id, {}).get(metric) is not None for _, _, engine_id in NEEDLE_SEARCH):
            raise ValueError(f"Missing supported NEEDLE scores for {metric}")
    return {"as_of": dates["overall"].isoformat(), "dates": dates, "rows": rows}


def fetch_needle():
    with urllib.request.urlopen(NEEDLE_URL, timeout=8) as response:
        raw = response.read(512001)
    if len(raw) > 512000:
        raise ValueError("Oversized NEEDLE feed")
    return json.loads(raw)


def aa_table(raw):
    if not valid_aa(raw):
        raise ValueError("Invalid AA snapshot")
    return raw


def benchmark_snapshot(offline, needle):
    if needle:
        source, filename, parse, fetch = "NEEDLE", "needle-results.json", needle_table, fetch_needle
    else:
        source, filename, parse, fetch = "AA", "search-rankings.json", aa_table, fetch_rankings
    cache = CACHE / (source.lower() + ".json")

    candidates = []
    for path in (REFERENCES / filename, cache):
        try:
            table = parse(read_json(path))
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
        candidates.append((observation_date(table), path == cache, table))
    if not candidates:
        raise ValueError(f"No readable {source} rankings. Reinstall the bundled snapshot.")
    as_of, cached, table = max(candidates, key=lambda item: item[:2])
    if (offline or datetime.now(timezone.utc).date() - as_of < WEEK
            or (cached and recently_written(cache, WEEK)) or not permit_refresh(cache)):
        return table
    try:
        raw = fetch()
        fresh = parse(raw) if needle else raw
        if observation_date(fresh) >= as_of:
            store(cache, raw)
            return fresh
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, HTTPException) as error:
        print(f"{source} refresh unavailable ({type(error).__name__}); using {as_of}.", file=sys.stderr)
    return table


def published_scores(offline):
    """A publisher can distribute updated measurements without shipping new code."""
    bundled = read_json(REFERENCES / "provider-scores.json") or {}
    url = os.environ.get("RESEARCH_RANKINGS_URL") or bundled.get("update_url")
    if not url:
        return bundled
    if urlsplit(url).scheme != "https":
        raise ValueError("RESEARCH_RANKINGS_URL must be an HTTPS URL.")
    cache = CACHE / ("published-" + hashlib.sha256(url.encode()).hexdigest()[:16] + ".json")
    saved = read_json(cache) or {}
    try:
        validate_scores(saved)
        if observation_date(saved) < observation_date(bundled):
            saved = {}
    except (TypeError, ValueError, KeyError):
        saved = {}
    if not offline and not (saved and recently_written(cache, WEEK)) and permit_refresh(cache):
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                if urlsplit(response.geturl()).scheme != "https":
                    raise ValueError("Expected HTTPS")
                raw = response.read(131073)
            if len(raw) > 131072:
                raise ValueError("Oversized rankings")
            fresh = json.loads(raw)
            validate_scores(fresh)
            if observation_date(fresh) >= observation_date(saved or bundled):
                store(cache, fresh)
                saved = fresh
        except (OSError, ValueError, TypeError, KeyError, HTTPException) as error:
            print(f"Published rankings unavailable ({type(error).__name__}); using saved data.", file=sys.stderr)
    return {**bundled, **saved}


def validate_extract_prices(prices):
    hosted = {provider for provider, _ in ROUTES["extract"]} - {"scrapling"}
    if not isinstance(prices, dict) or prices.keys() - hosted:
        raise ValueError("Extraction prices must map supported hosted CLI names to USD per 1,000 requests.")
    for provider, price in prices.items():
        if type(price) not in (int, float) or not 0 <= price < math.inf:
            raise ValueError(f"Expected a finite, nonnegative extraction price for {provider}.")


def extract_prices(public):
    prices = public.get("extract_usd_per_1000", {})
    configured = os.environ.get("RESEARCH_EXTRACT_PRICES")
    if not configured:
        return prices, {}
    overrides = read_json(Path(configured).expanduser())
    if overrides is None:
        raise ValueError("RESEARCH_EXTRACT_PRICES must point to a readable JSON price map.")
    validate_extract_prices(overrides)
    return prices, overrides


def validate_scores(data):
    observation_date(data)
    if data["schema"] != 1 or not isinstance(data["categories"], dict):
        raise ValueError("Unknown ranking format")
    validate_extract_prices(data.get("extract_usd_per_1000", {}))
    for category, scores in data["categories"].items():
        if category not in ROUTES or not isinstance(scores, dict):
            raise ValueError("Invalid category")
        for row in scores.values():
            if not isinstance(row, dict) or any(type(row.get(k)) is not int for k in ("passed", "total")):
                raise ValueError("Invalid benchmark score")
            if not 0 <= row["passed"] <= row["total"] or not row["total"]:
                raise ValueError("Invalid benchmark counts")


def local_scores(category):
    data = read_json(CACHE / f"{category}.json")
    if not data:
        return {}
    try:
        validate_scores(data)
        scores = data["categories"][category]
        for row in scores.values():
            observation_date(row)
        return scores
    except (ValueError, TypeError, KeyError):
        return {}


def provider_names(category):
    return dict.fromkeys(row[0] for row in ROUTES[category])


SEARCH_FAMILIES = {"exa": ("exa", "exa-lite"), "perplexity": ("pplx", "perplexity-fast")}
MODE_FAMILY = {mode: modes[0] for modes in SEARCH_FAMILIES.values() for mode in modes}


def provider_selections(options):
    aliases = {"perplexity": "pplx", "chatgpt": "openai", "anthropic": "ant", "claude": "ant", "brave": "bx", "tavily": "tvly", "parallel": "parallel-cli", "context.dev": "context-dev"}
    selections = {}
    for option in options:
        category, sep, names = option.partition("=")
        if not sep or category not in ROUTES:
            raise ValueError(f"Use --only CATEGORY=PROVIDER,... with a category from {', '.join(ROUTES)}.")
        if category in selections:
            raise ValueError(f"Give one --only list for {category}.")
        supported = provider_names(category)
        selected = set()
        for name in names.split(","):
            name = name.strip().lower()
            if category in NEEDLE_METRICS and name in SEARCH_FAMILIES:
                selected.update(SEARCH_FAMILIES[name])
                continue
            name = {"exa-auto": "exa", "you.com": "you", "serper": "google", "searchapi": "bing"}.get(name, name)
            provider = aliases.get(name, name)
            if provider not in supported:
                raise ValueError(f"Unsupported {category} provider {name!r}. Choose from {', '.join(sorted(supported))}.")
            selected.add(provider)
        selections[category] = selected
    return selections


# Apache Ant, the older Python OpenAI CLI and Jina's neural-search server
# can occupy these names. Verify the matching command before offering a route.
CLI_HELP = {
    "ant": (("messages", "create", "--help"), "--max-tokens"),
    "openai": (("responses", "create", "--help"), "--input"),
    "jina": (("search", "--help"), "--ssrn"),
}


def matches_search_cli(name, path):
    if name not in CLI_HELP:
        return True
    args, marker = CLI_HELP[name]
    try:
        help_text = subprocess.run([path, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return marker.encode() in help_text


def installed_routes(category, selections):
    names = selections.get(category) or provider_names(category)
    available = {}
    for name in names:
        if name in API_MODES:
            if credential_for(name):
                available[name] = sys.executable
        elif (path := shutil.which(name)) and matches_search_cli(name, path):
            available[name] = os.path.abspath(path)
    return available


def preferred_search_provider(selections):
    # Only consult saved rankings. Extraction can still run without search data.
    installed = installed_routes("search", selections)
    if not installed:
        return None
    try:
        first = next(ranked_routes("search", installed, True, selections), None)
    except ValueError:
        return None
    return first[1] if first and first[0][0] == 0 else None


def extract_priority(provider, row, price, price_basis):
    if provider == "scrapling":
        return (3,), "local fallback"
    passed, total = (row["passed"], row["total"]) if row else (0, 0)
    rate = passed / total if total else 0
    price_note = "price unknown" if price is None else f"{price_basis} ${price:g}/1k requests"
    if total >= 3 and rate >= 0.8:
        if price is None:
            return (1, -rate), price_note
        cost = price / rate
        return (0, cost), f"{price_note}, est. ${cost:g}/1k usable pages"
    return (2, -rate), f"{price_note}, limited reliability evidence"


def ranked_routes(category, installed, offline, selections):
    routes = [route for route in ROUTES[category] if route[0] in installed]
    ranked = []
    if category in NEEDLE_METRICS:
        data = benchmark_snapshot(offline, needle=True)
        metric = NEEDLE_METRICS[category]
        for provider, command, engine_id in routes:
            score = data["rows"].get(engine_id, {}).get(metric)
            if score is None:
                key, evidence = (1, 0), "unscored; default order"
            else:
                key = (0, -score)
                evidence = f"NEEDLE {metric} {score:.2%}, {data['dates'][metric]}"
            ranked.append((key, provider, command, evidence))
    elif category == "deep-search":
        data = benchmark_snapshot(offline, needle=False)
        metric = "deepsearchqa"
        for provider, command, label in routes:
            row = data["rows"].get(label, {})
            if row.get(metric) is None:
                key, evidence = (1, 0, 0), "unscored"
            else:
                key = (0, -row[metric], row["latency"])
                evidence = f"AA {metric} {row[metric]:.2f}/100, {data['as_of']}"
            ranked.append((key, provider, command, evidence))
    else:
        public = published_scores(offline)
        local = local_scores(category)
        published = public["categories"].get(category, {})
        if category == "extract":
            prices, overrides = extract_prices(public)
        for provider, command in routes:
            if provider in local:
                row = local[provider]
                origin, stamp = "local", row["as_of"]
            else:
                row = published.get(provider)
                origin, stamp = "published", public["as_of"]
            evidence = f"{origin} benchmark {row['passed']}/{row['total']}, {stamp}" if row else "unscored"
            if category == "extract":
                price = overrides.get(provider, prices.get(provider))
                basis = "account" if provider in overrides else "published"
                key, note = extract_priority(provider, row, price, basis)
                evidence = f"{evidence}, {note}"
            elif row:
                key = (0, -row["passed"] / row["total"])
            else:
                key, evidence = (1, 0), "unscored; default order"
            ranked.append((key, provider, command, evidence))
        if category == "extract":
            costs = [key[1] for key, *_ in ranked if key[0] == 0]
            if len(costs) != len(set(costs)):
                reserved = preferred_search_provider(selections)
                # The stable price sort below retains this order on an exact tie.
                ranked.sort(key=lambda item: item[0][0] == 0 and item[1] == reserved)
    seen = set()
    for key, provider, command, evidence in sorted(ranked, key=lambda item: item[0]):
        family = MODE_FAMILY.get(provider, provider)
        if family not in seen:
            seen.add(family)
            yield key, provider, command, evidence


SPECIALIST_TOOLS = (
    ("Extraction & parsing", (
        ("scrapling", "local web extraction fallback"),
        ("defuddle", "local HTML article parser"),
        ("markit", "PDF/document to Markdown conversion"),
        ("curl", "raw HTML/metadata inspection"),
    )),
    ("GitHub", (
        ("gh", "GitHub code/repo search and file API"),
        ("gitquarry", "GitHub repo discovery, tree and code search"),
    )),
    ("Media, video & transcription", (
        ("yt-dlp", "YouTube captions and audio extraction"),
        ("youtube_transcript_api", "alternative YouTube caption client"),
        ("gemini-api", "visual YouTube/video analysis, transcription, deep research"),
        ("transcribe-cli", "local transcribe.cpp runtime (Parakeet Ultra needs a separate GGUF model)"),
        ("parakeet-mlx", "local Parakeet TDT 0.6B v3 transcription (Apple Silicon)"),
        ("chough", "local Parakeet TDT 0.6B v3 transcription (CPU ONNX)"),
        ("whisper-cli", "local whisper.cpp transcription (99 languages)"),
        ("whisper", "local OpenAI Whisper transcription (99 languages)"),
    )),
    ("Other specialist CLIs", (
        ("kagi", "Kagi subscriber search, summarize, ask-page, translate"),
        ("reddit", "Reddit read-only CLI (reddit-cli; live OAuth or Arctic Shift archive)"),
    )),
)


def print_checklist():
    """Print a manual local checklist of supported tools and API env vars (no network calls)."""
    cli_categories = {}
    for category, rows in ROUTES.items():
        for row in rows:
            name = row[0]
            if name not in API_MODES and name != "scrapling":
                cats = cli_categories.setdefault(name, [])
                if category not in cats:
                    cats.append(category)

    def cli_line(name, detail):
        path = shutil.which(name)
        if not path:
            return f"- [ ] `{name}` - {detail}"
        if not matches_search_cli(name, path):
            return f"- [ ] `{name}` - {detail} (incompatible executable on PATH)"
        return f"- [x] `{name}` - {detail}"

    print("## Ranked provider CLIs")
    for name, categories in cli_categories.items():
        print(cli_line(name, ", ".join(categories)))

    print("\n## API-only search modes (env var present)")
    for mode, (env_var, *_) in API_MODES.items():
        mark = "x" if credential_for(mode) else " "
        print(f"- [{mark}] `{mode}` (`{env_var}`)")

    for heading, tools in SPECIALIST_TOOLS:
        print(f"\n## {heading}")
        for name, detail in tools:
            print(cli_line(name, detail))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use saved rankings without checking public feeds.")
    parser.add_argument("--only", metavar="CATEGORY=NAME,...", action="append", default=[],
                        help="Limit a category to these providers for this task. Repeat for other categories.")
    parser.add_argument("action", choices=[*ROUTES, "benchmark", "check"])
    parser.add_argument("category", nargs="?", choices=["extract", "images"])
    args = parser.parse_args()
    if args.action == "check":
        if args.category or args.only:
            parser.error("`check` takes no category or --only filters.")
        print_checklist()
        return 0
    if (args.action == "benchmark") != bool(args.category):
        parser.error("Use a category alone, or benchmark extract / benchmark images.")
    category = args.category or args.action
    selections = provider_selections(args.only)
    installed = installed_routes(category, selections)
    selected = selections.get(category)
    if selected:
        missing = selected - installed.keys()
        if missing:
            for name in sorted(missing):
                reason = f"set {API_MODES[name][0]}" if name in API_MODES else "CLI missing or incompatible on PATH"
                print(f"{name} unavailable for {category}: {reason}.", file=sys.stderr)
    if not installed:
        qualifier = "selected" if selected else "supported"
        print(f"No {qualifier} provider available for {category}.", file=sys.stderr)
        return 1
    if args.action == "benchmark":
        if args.offline:
            parser.error("Benchmarks need network access.")
        scores = benchmark(category, installed, selected)
        complete = {p:r for p,r in scores.items() if r.get("cases") and r["cases"] == r["total"]}
        if not complete:
            print("No complete measurement; previous rankings retained.", file=sys.stderr)
            return 1
        today = datetime.now(timezone.utc).date().isoformat()
        saved = local_scores(category)
        saved.update({name: dict(row, as_of=today) for name, row in complete.items()})
        store(CACHE / f"{category}.json", {"schema": 1, "as_of": today, "categories": {category: saved}})
    for rank, (_, provider, command, evidence) in enumerate(ranked_routes(category, installed, args.offline, selections), start=1):
        executable = shlex.quote(installed[provider]) if provider in API_MODES else provider
        print(f"{rank}. {executable} {command}  [{evidence}]")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
