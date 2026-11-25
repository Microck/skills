"""Small live smoke benchmarks for extraction and image-search CLIs."""

import html
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit


EXTRACTION_CASES = (
    ("iana-domains", "https://www.iana.org/domains/reserved", ("without prior coordination with us", "test idn top level domains")),
    ("zen-of-python", "https://peps.python.org/pep-0020/", ("flat is better than nested", "namespaces are one honking great idea")),
    ("reserved-domains", "https://www.rfc-editor.org/rfc/rfc2606.html", ("without fear of conflicts", "sure to be invalid")),
)

IMAGE_CASES = (
    ("apollo-11", "Apollo 11 Buzz Aldrin on the Moon NASA photograph AS11-40-5903", ("aldrin", "moon")),
    ("great-wave", "The Great Wave off Kanagawa Hokusai Metropolitan Museum of Art", ("great wave", "kanagawa")),
)

EXTRACTION_COMMANDS = {
    "keenable": ("fetch", "{target}", "--live"),
    "firecrawl": ("scrape", "{target}", "--format", "markdown", "--only-main-content", "--json"),
    "context-dev": (
        "--format", "json", "web", "web-crawl-md", "--url", "{target}", "--max-depth", "0",
        "--max-pages", "1", "--use-main-content-only", "--wait-for-ms", "0",
    ),
    "parallel-cli": ("extract", "{target}", "--full-content", "--no-excerpts", "--json"),
    "scrapling": ("extract", "get", "{target}", "{output}", "--no-stealthy-headers"),
    "tvly": ("extract", "{target}", "--format", "markdown", "--json"),
}

IMAGE_COMMANDS = {
    "bx": ("images", "{target}", "--count", "5"),
    "firecrawl": ("search", "{target}", "--sources", "images", "--limit", "5", "--json"),
    "linkup": (
        "--json", "search", "{target}", "--depth", "fast", "--output", "search-results",
        "--include-images", "--max-results", "5",
    ),
    "tvly": ("search", "{target}", "--include-images", "--include-image-descriptions", "--max-results", "5", "--json"),
}

EXTRACTION_FIELDS = {
    "context-dev": ("markdown", None),
    "parallel-cli": ("full_content", "errors"),
    "tvly": ("raw_content", "failed_results"),
}


class BenchmarkError(Exception):
    """A sanitized operational failure, excluded from the score."""


def failure_reason(message):
    if re.search(r"usage.exceeded|insufficient (?:credits|balance)|payment required|\b402\b", message, re.I):
        return "credits unavailable"
    if re.search(
        r"unauthenticated|unauthorized|invalid api key|no api key|"
        r"api[_ -]key (?:missing|required|not found)|not (?:authenticated|logged in)|"
        r"login required|\b401\b",
        message,
        re.I,
    ):
        return "credentials unavailable"
    if re.search(r"unknown (?:command|option|flag|argument)|unexpected argument|no such (?:command|option)", message, re.I):
        return "unsupported CLI version"
    if re.search(r"\b429\b|rate.limit|too many requests", message, re.I):
        return "rate limited"
    return "provider request failed"


def run_cli(executable, args, target, workspace):
    with_output_file = "{output}" in args
    output_path = workspace / "page.txt"
    command = [executable, *(arg.format(target=target, output=output_path) for arg in args)]
    try:
        if with_output_file:
            output_path.unlink(missing_ok=True)
        completed = subprocess.run(
            command, cwd=workspace, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=60, check=False,
        )
        if completed.returncode:
            raise BenchmarkError(failure_reason(completed.stderr + "\n" + completed.stdout))
        if with_output_file:
            # Scrapling may exit successfully after writing an HTTP error page.
            if re.search(r"Fetched \([45]\d\d\)", completed.stderr):
                raise BenchmarkError("target page fetch failed")
            return output_path.read_text(encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        raise BenchmarkError("provider timed out") from None
    except FileNotFoundError:
        raise BenchmarkError("executable or output file unavailable") from None
    except OSError:
        raise BenchmarkError("provider could not run") from None
    return completed.stdout


def json_response(output):
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        raise BenchmarkError("unrecognized response") from None
    if not isinstance(payload, dict):
        raise BenchmarkError("unrecognized response")
    if payload.get("success") is False or payload.get("error") or payload.get("detail"):
        raise BenchmarkError(failure_reason(str(payload)))
    return payload


def response_rows(value):
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise BenchmarkError("unrecognized response")
    return value


def response_text(row, key):
    value = row.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BenchmarkError("unrecognized response")
    return value


def response_object(value):
    if not isinstance(value, dict):
        raise BenchmarkError("unrecognized response")
    return value


def keenable_body(output):
    # Read the top-level YAML scalar and its indented continuation lines.
    lines = iter(output.splitlines())
    for line in lines:
        if line.startswith("content:"):
            body = [line.removeprefix("content:").strip()]
            for line in lines:
                if line and not line[0].isspace():
                    break
                body.append(line)
            return "\n".join(body)
    raise BenchmarkError("unrecognized response")


def extraction_text(provider, output):
    if provider == "keenable":
        return keenable_body(output)
    if provider == "scrapling":
        return output
    payload = json_response(output)
    if provider in EXTRACTION_FIELDS:
        content_key, errors_key = EXTRACTION_FIELDS[provider]
        rows = response_rows(payload.get("results"))
        if not rows and errors_key and payload.get(errors_key):
            raise BenchmarkError(failure_reason(str(payload[errors_key])))
        if provider == "context-dev":
            statuses = [response_object(row.get("metadata", {})).get("success") for row in rows]
            if statuses and all(status is False for status in statuses):
                raise BenchmarkError("target page fetch failed")
        return "\n".join(response_text(row, content_key) for row in rows)
    metadata = response_object(payload.get("metadata", {}))
    if metadata.get("error") or (isinstance(status := metadata.get("statusCode"), int) and status >= 400):
        raise BenchmarkError(failure_reason(str(metadata)))
    return response_text(payload, "markdown")


def normalized(value):
    return " ".join(re.findall(r"\w+", html.unescape(value).casefold()))


def usable_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)
    except ValueError:
        return False


def image_hits(provider, output):
    if provider == "firecrawl" and output.strip() == "No results found.":
        return
    payload = json_response(output)
    if provider == "tvly":
        # Top-level image search hits carry descriptions but no source page.
        # Count a source only when a web result explicitly contains the same image URL.
        images = response_rows(payload.get("images"))
        sources = set()
        for row in response_rows(payload.get("results")):
            if usable_url(response_text(row, "url")):
                for image in response_rows(row.get("images", [])):
                    url = response_text(image, "url")
                    if usable_url(url):
                        sources.add(url)
        for image in images[:5]:
            url = response_text(image, "url")
            yield url, response_text(image, "description"), url in sources
    elif provider == "linkup":
        for row in response_rows(payload.get("results"))[:5]:
            if row.get("type") == "image":
                yield response_text(row, "url"), response_text(row, "name"), False
    elif provider == "bx":
        for row in response_rows(payload.get("results"))[:5]:
            properties = response_object(row["properties"]) if row.get("properties") is not None else {}
            thumbnail = response_object(row["thumbnail"]) if row.get("thumbnail") is not None else {}
            image_url = response_text(properties, "url") or response_text(thumbnail, "src")
            yield image_url, response_text(row, "title"), usable_url(response_text(row, "url"))
    else:
        data = response_object(payload.get("data"))
        for row in response_rows(data.get("images", []))[:5]:
            yield response_text(row, "imageUrl"), response_text(row, "title"), usable_url(response_text(row, "url"))


def score_images(provider, output, terms):
    matched = sourced = False
    for image_url, description, has_source in image_hits(provider, output):
        if usable_url(image_url) and all(term in normalized(description) for term in terms):
            matched = True
            sourced |= has_source
    return matched, sourced


def benchmark(category, executables, selected=None):
    """Return one score per provider with at least one valid case."""
    cases, commands = {
        "extract": (EXTRACTION_CASES, EXTRACTION_COMMANDS),
        "images": (IMAGE_CASES, IMAGE_COMMANDS),
    }[category]
    scores = {}
    with TemporaryDirectory(prefix="research-benchmark-") as disposable:
        workspace = Path(disposable)
        for provider, command in commands.items():
            if selected is not None and provider not in selected:
                continue
            if not (executable := executables.get(provider)):
                print(f"{provider}: CLI unavailable", file=sys.stderr)
                continue
            passed = scored = errors = source_pages = 0
            for case, target, terms in cases:
                try:
                    output = run_cli(executable, command, target, workspace)
                    if category == "extract":
                        content = normalized(extraction_text(provider, output))
                        matched = all(term in content for term in terms)
                    else:
                        matched, sourced = score_images(provider, output, terms)
                        source_pages += sourced
                except BenchmarkError as error:
                    errors += 1
                    print(f"{provider}/{case}: {error}", file=sys.stderr)
                    if str(error) in {
                        "credits unavailable", "credentials unavailable", "unsupported CLI version",
                        "rate limited", "executable or output file unavailable", "provider could not run",
                    }:
                        break
                    continue
                scored += 1
                passed += matched
                print(f"{provider}/{case}: {'pass' if matched else 'miss'}", file=sys.stderr)
            if scored:
                scores[provider] = {"passed": passed, "total": scored, "errors": errors, "cases": len(cases)}
                if category == "images":
                    scores[provider]["source_pages"] = source_pages
    return scores
