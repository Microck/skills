"""Search one of the NEEDLE modes without an equivalent native CLI."""
import argparse
import json
import os
import sys
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Fixed destinations keep benchmark feeds and query text out of auth routing.
EXA = ("EXA_API_KEY", "https://api.exa.ai/search", "x-api-key", "")
MODES = {
    "exa": EXA,
    "exa-lite": EXA,
    "perplexity-fast": ("PERPLEXITY_API_KEY", "https://api.perplexity.ai/search", "Authorization", "Bearer "),
    "webiq": ("WEBIQ_API_TOKEN", "https://api.microsoft.ai/v3/search/web", "x-apikey", ""),
    "you": ("YOU_API_KEY", "https://ydc-index.io/v1/search", "X-API-Key", ""),
    "deepseek": ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/tools/search", "Authorization", "Bearer "),
    "seltz": ("SELTZ_API_KEY", "https://api.seltz.ai/v1/search", "x-api-key", ""),
    "kagi": ("KAGI_API_KEY", "https://kagi.com/api/v1/search", "Authorization", "Bot "),
    "google": ("SERPER_API_KEY", "https://google.serper.dev/search", "X-API-KEY", ""),
    "bing": ("SEARCHAPI_API_KEY", "https://www.searchapi.io/api/v1/search", "Authorization", "Bearer "),
}


def credential_for(mode):
    return os.environ.get(MODES[mode][0], "").strip()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def search_request(mode, query, credential):
    _, url, header, prefix = MODES[mode]
    headers = {header: prefix + credential, "Accept": "application/json"}
    if mode == "bing":
        params = urlencode({"q": query, "num": 10, "engine": "bing"})
        return Request(f"{url}?{params}", headers=headers)
    if mode in ("exa", "exa-lite"):
        body = {"query": query, "type": "lite" if mode == "exa-lite" else "auto", "numResults": 10,
                "contents": {"highlights": {"maxCharacters": 2000}}}
    elif mode == "perplexity-fast":
        body = {"query": query, "max_results": 10, "search_type": "fast", "search_context_size": "low"}
    elif mode == "webiq":
        body = {"query": query, "maxResults": 10, "language": "en", "region": "US",
                "contentFormat": "passage", "maxLength": 2000, "safeSearch": "off"}
    elif mode == "seltz":
        body = {"query": query, "max_results": 10, "fields": {"content": {"max_characters_per_result": 2000}}}
    elif mode == "google":
        body = {"q": query, "num": 10, "gl": "us", "hl": "en"}
    elif mode == "kagi":
        body = {"query": query, "limit": 10}
    else:
        body = {"query": query, "count": 10}
        if mode == "deepseek":
            body["need_content"] = False
    headers["Content-Type"] = "application/json"
    return Request(url, data=json.dumps(body).encode(), headers=headers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("query")
    args = parser.parse_args()
    env = MODES[args.mode][0]
    key = credential_for(args.mode)
    if not key:
        parser.exit(1, f"{args.mode} needs {env}.\n")
    try:
        request = search_request(args.mode, args.query, key)
        with build_opener(NoRedirect()).open(request, timeout=45) as response:
            limit = 8 * 1024 * 1024
            raw = response.read(limit + 1)
            if len(raw) > limit:
                parser.exit(1, f"{args.mode} response exceeded 8 MiB.\n")
            payload = json.loads(raw)
    except HTTPError as error:
        parser.exit(1, f"{args.mode} returned HTTP {error.code}.\n")
    except (ValueError, OSError, HTTPException) as error:
        parser.exit(1, f"{args.mode} request failed ({type(error).__name__}).\n")
    if not isinstance(payload, dict) or payload.get("error"):
        parser.exit(1, f"{args.mode} returned an invalid or error response.\n")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
