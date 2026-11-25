# Images, video and transcripts

## Discover media

- For text-to-image discovery use the `images` order from [rankings](rankings.md).
- Reference-image search: Octen accepts exactly one reference image instead of text; the installed MCP adapter has a documented incompatibility, so use the verified HTTP contract in that reference.
- Video/segment search: Octen video search accepts a text query and can return matched timestamps. Brave (`bx videos "QUERY"`) also returns video metadata (duration, views, creator). Preserve the source page and segment boundaries.
- UI inspiration with style tokens/snippets belongs to the separate `octen-design` skill.

A thumbnail or search hit does not establish licensing, provenance, the video's spoken content, or what appears across the video. Inspect the source and retrieve captions before quoting speech, or inspect the video itself for visual claims.

## Visual video and YouTube analysis

Captions and transcripts do not show slides, charts, UI demos, or on-screen actions. When the question requires inspecting **visual content** in a YouTube video or local clip, use Google's `gemini-api` CLI if installed and configured (or the `gemini-api-cli` skill):

```bash
gemini-api analyze -m gemini-3.5-flash-lite -i "$VIDEO_OR_YOUTUBE_URL" \
  "Describe the relevant on-screen moments with timestamps."
```

- For local files larger than ~14 MB, upload once first with `gemini-api files upload <path> --wait` and pass the returned `files/<id>` URI to `-i`.
- Use `gemini-3.5-flash-lite` for high-throughput visual inspection or `gemini-4-hydrogen` / `gemini-4-neon` when denser reasoning over slides or UI details is needed; check account quota and billing before running.
- Keep captions or publisher transcripts first for **verbatim spoken quotes**. Multimodal video analysis can paraphrase speech rather than reproduce exact wording.
- Do not upload private local recordings to a hosted API without user authorization.

## YouTube captions first

For a supplied publisher transcript URL, run the extract preflight and fetch that URL with the first listed extractor. Keep the retrieved transcript and inspect the requested portion. For an opening remark, read the first cues or sentences. Search with neutral words from the question and inspect adjacent lines; a failed search for a guessed answer says nothing about whether speech was retrieved. If the passage answers the question, cite the transcript and stop. If it yields only a summary, leave that extractor immediately and try captions with yt-dlp. Prefer creator-provided captions. If a client cannot supply captions and access remains open, use the alternative below. On access denial, bot detection or HTTP 429, stop requests to that video host. When captions fail and the publisher hosts a separate transcript page, read its embedded transcript next. The [publisher transcript reader](../scripts/publisher-transcript.py) takes HTML on stdin and prints the spoken text from the page's VideoObject metadata. Use the available publisher-transcript tool, or run the following from the skill directory on a public publisher page:

```bash
curl --fail --silent --show-error --location --max-redirs 3 --proto-redir '=https' --max-time 20 -- "$PUBLISHER_URL" | python3 scripts/publisher-transcript.py
```

Cite that publisher page as soon as its text answers the question. Its untimed text supports a quotation. Link only the publisher transcript when it supplies untimed words. Add a time, timestamped URL or start-of-video link only after retrieving a timed cue for those words in the same recording. If the user offers a transcript or a timestamp as alternatives, the transcript link completes the request. If the HTML has no embedded transcript, use the next available page extractor on the publisher page. Respect access denials from that publisher. If no source yields speech, say which words you could not verify.

```bash
yt-dlp --list-subs --skip-download "$URL"
WORK=$(mktemp -d)
yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs en --sub-format json3 -o "$WORK/captions.%(ext)s" "$URL"
```

Choose the requested/source language and inspect the actual downloaded filename. Save into the relevant project, or `~/Downloads` when no project applies. Use `Channel_Title.txt` with unsafe characters replaced by `_`; use the video ID if metadata is unavailable. Do not overwrite an existing transcript without checking it.

Flatten the chosen JSON3 file only when plain text is requested. Keep the original timing data when citations need timestamps:

```bash
python3 - "$CAPTION_FILE" "$OUTPUT_FILE" <<'PY'
import html
import json
from pathlib import Path
import re
import sys
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
parts = [
    ''.join(segment.get('utf8', '') for segment in event.get('segs') or [])
    for event in payload.get('events', [])
]
transcript = re.sub(r'\s+', ' ', html.unescape(' '.join(
    part.strip() for part in parts if part.strip()
))).strip()
if not transcript:
    raise SystemExit('Caption track contains no transcript text')
Path(sys.argv[2]).write_text(transcript + '\n', encoding='utf-8')
print(sys.argv[2])
PY
```

The installed alternative caption client accepts a video ID, not a URL:

```bash
youtube_transcript_api VIDEO_ID --list-transcripts
youtube_transcript_api VIDEO_ID --languages en --exclude-generated --format text
youtube_transcript_api VIDEO_ID --languages en --format json
```

JSON preserves segment data; text removes timestamps. Cookie authentication is disabled in the inspected client. Use this as an available client, not to retry around an access block.

## No usable captions

When captions are genuinely absent (or for local audio/video recordings), transcribe locally first so private media stays on-device and no paid API is invoked automatically.

### Local transcription (preferred)

1. **Local Parakeet transcription for the 25 supported European languages.** Choose a runtime with a matching local model.
   - **Parakeet Ultra GGUF** with [transcribe.cpp](https://github.com/handy-computer/transcribe.cpp/blob/main/docs/models/parakeet-ultra.md): set `MODEL` to the installed Ultra GGUF path. Convert the input to 16 kHz mono WAV and request token timestamps when timing matters.
     ```bash
     ffmpeg -i "$WORK/audio.mp3" -ar 16000 -ac 1 -c:a pcm_s16le "$WORK/audio.wav"
     transcribe-cli -m "$MODEL" --timestamps token "$WORK/audio.wav"
     ```
   - **Apple Silicon (`parakeet-mlx`):**
     ```bash
     parakeet-mlx "$WORK/audio.mp3" --output-format srt   # txt, srt, vtt, json, or all; add --highlight-words for word timestamps
     ```
   - **Linux / Windows / Intel Mac CPU (ONNX via `chough` or `onnx-asr`):**
     ```bash
     chough -f vtt -o "$WORK/transcript.vtt" "$WORK/audio.mp3"   # supports text, json, vtt; accepts video files directly
     ```
2. **Broader language coverage (99 languages), heavy accents, or when Parakeet is not installed:** Fall back to Whisper (`whisper-cli` from `whisper.cpp`, `faster-whisper` on CUDA, or OpenAI `whisper`):
   ```bash
   yt-dlp -f ba -x --audio-format mp3 -o "$WORK/audio.%(ext)s" "$URL"
   whisper "$WORK/audio.mp3" --model turbo --output_format txt --output_dir "$WORK"
   ```
   Pass a known language with `--language`; use `json` or `srt` output to preserve segment timestamps. On GPU servers running large open-weight ASR checkpoints, **SOV-Transcribe-1** (Apache 2.0, 7 languages), **Voxtral Small**, and **Nemotron 3.5 Transcribe** currently lead open-weight accuracy benchmarks.

### Hosted transcription (opt-in only)

Keep hosted or paid transcription strictly opt-in; never escalate to it automatically after a YouTube block or with private recordings. When the user authorizes a hosted API:
- **Highest independent recorded-audio accuracy (Nov 2026 AA-WER):** ElevenLabs **Scribe v2** (90+ languages, speaker diarization up to 32 speakers), Mistral **Voxtral Small / Mini Transcribe 3**, and **AssemblyAI Universal-3.5 Pro** (or **Universal-2** for lowest base rate). **Deepgram Nova-3** leads on hosted speed with built-in diarization.
- **If `gemini-api` is already configured and authorized:** `gemini-api transcribe -i "$LOCAL_FILE_OR_FILE_URI" --format srt --out "$WORK/transcript.srt"` outputs timestamped, speaker-labeled transcripts (local files or `files/<id>` only; `transcribe` does not accept YouTube URLs directly).

Local transcription can be slow on first run and may download model weights. If a tool's extractor is obsolete, report the version/error and use its actual installation method for an authorized update, not an automatic package upgrade.

Read the transcript's beginning and a relevant passage before claiming success. Distinguish captions from machine transcription, cite timestamps where available, and remove only temporary files created by this workflow after preserving the requested output.

Evidence: prior caption workflow and inspected installed transcript-client argument definitions. YouTube and Whisper were not live-tested during consolidation; access restrictions remain possible.
