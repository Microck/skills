"""Fetch normalized rows for the Artificial Analysis Search API leaderboard."""

from datetime import datetime, timezone
import json
import math
import re
from urllib.request import Request, urlopen


SOURCE_URL = "https://artificialanalysis.ai/agents/search-api"
USER_AGENT = "research-skill-rankings/1.0"
MAX_PAGE_BYTES = 5 * 1024 * 1024
_FLIGHT_PUSH = re.compile(r"<script>self\.__next_f\.push\((\[.*?\])\)</script>", re.S)
_DATA_MARKER = '{"searchProviders":'
_PROVIDER_COUNT = re.compile(r">(\d+) of (\d+) providers<")


def _number(row, field, upper=math.inf):
    value = row[field]
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= upper:
        raise ValueError(f"Invalid Artificial Analysis value for {field}")
    return value


def _parse_rows(page):
    if not page.rstrip().endswith("</html>"):
        raise ValueError("Incomplete Artificial Analysis leaderboard page")

    # Next.js embeds the full selectable table as JSON inside a JSON string.
    # The HTML table only renders the default selection and rounds its scores.
    chunks = (json.loads(match[1]) for match in _FLIGHT_PUSH.finditer(page))
    decoder = json.JSONDecoder()
    payloads = [
        decoder.raw_decode(chunk[1], match.start())[0]
        for chunk in chunks
        if len(chunk) == 2 and isinstance(chunk[1], str)
        for match in re.finditer(re.escape(_DATA_MARKER), chunk[1])
    ]
    if len(payloads) != 1:
        raise ValueError("Artificial Analysis leaderboard data was missing or ambiguous")

    payload = payloads[0]
    providers = payload["searchProviders"]
    selected = payload["defaultSelectedIds"]
    baseline = payload["modelBaseline"]
    model = baseline["answerModelSlug"]
    ids = {row["id"] for row in providers}
    displayed_counts = {(int(visible), int(total)) for visible, total in _PROVIDER_COUNT.findall(page)}
    if (
        not model
        or not providers
        or len(ids) != len(providers)
        or not selected
        or len(set(selected)) != len(selected)
        or not set(selected) <= ids
        or displayed_counts != {(len(selected), len(providers))}
    ):
        raise ValueError("Artificial Analysis leaderboard cohort was inconsistent")

    rows = {}
    for provider in providers:
        for field in ("isBaseline", "isNativeSearch"):
            if type(provider[field]) is not bool:
                raise ValueError(f"Invalid Artificial Analysis provider flag {field}")

        # The integrated first-party search tool uses a different harness.
        if provider["isBaseline"] or provider["isNativeSearch"] or provider["answerModelSlug"] != model:
            continue
        if provider["benchmarkCount"] != 3 or provider["missingBenchmarks"] != []:
            continue

        name = provider["providerName"]
        variant = provider["providerVariant"]
        if not isinstance(name, str) or not name or (variant is not None and not isinstance(variant, str)):
            raise ValueError("Invalid Artificial Analysis provider name or variant")
        label = f"{name} ({variant})" if variant else name
        latency = _number(provider, "searchTimePerTaskS")
        if label in rows or latency <= 0:
            raise ValueError(f"Duplicate mode or invalid search latency for {label}")
        rows[label] = {
            "quality": _number(provider, "aaSearchQualityIndex", 1) * 100,
            "latency": latency,
            "deepsearchqa": _number(provider, "deepsearchqaAvgF1", 1) * 100,
        }
    if not rows:
        raise ValueError("Artificial Analysis leaderboard had no comparable search modes")
    return rows


def fetch_rankings():
    """Return exact scores on a 0–100 scale and measured search seconds per task."""
    request = Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        if response.geturl() != SOURCE_URL or response.headers.get_content_type() != "text/html":
            raise ValueError("Unexpected Artificial Analysis leaderboard response")
        page = response.read(MAX_PAGE_BYTES + 1)
    if len(page) > MAX_PAGE_BYTES:
        raise ValueError("Artificial Analysis leaderboard page exceeded the size limit")
    return {
        "as_of": datetime.now(timezone.utc).date().isoformat(),
        "rows": _parse_rows(page.decode("utf-8")),
    }


if __name__ == "__main__":
    print(json.dumps(fetch_rankings(), indent=2))
