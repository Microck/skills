"""Read one publisher-supplied VideoObject transcript from HTML on stdin."""
from html.parser import HTMLParser
import json
import sys


def transcripts(value):
    if isinstance(value, list):
        for item in value:
            yield from transcripts(item)
    elif isinstance(value, dict):
        kinds = value.get("@type", [])
        if isinstance(kinds, str):
            kinds = [kinds]
        speech = value.get("transcript")
        if isinstance(kinds, list) and any(str(kind).rsplit("/", 1)[-1] == "VideoObject" for kind in kinds):
            if isinstance(speech, str) and speech.strip():
                yield speech.strip()
        for child in value.values():
            if isinstance(child, (list, dict)):
                yield from transcripts(child)


class PublisherPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.block = None
        self.speech = set()

    def handle_starttag(self, tag, attrs):
        if tag == "script" and str(dict(attrs).get("type", "")).lower() == "application/ld+json":
            self.block = []

    def handle_data(self, text):
        if self.block is not None:
            self.block.append(text)

    def handle_endtag(self, tag):
        if tag == "script" and self.block is not None:
            try:
                self.speech.update(transcripts(json.loads("".join(self.block))))
            except json.JSONDecodeError:
                pass
            self.block = None


if __name__ == "__main__":
    page = PublisherPage()
    for chunk in iter(lambda: sys.stdin.read(65536), ""):
        page.feed(chunk)
    page.close()
    if len(page.speech) != 1:
        sys.exit("No unambiguous VideoObject transcript in this page.")
    print("Publisher transcript text only. This reader verifies no playback times, including the start. Cite the publisher page for the quotation.", file=sys.stderr)
    print(page.speech.pop())
