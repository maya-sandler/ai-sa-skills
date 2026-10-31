#!/usr/bin/env python3
"""Turn a Gong call read through Glean into a readable transcript file.

Glean `read_document` on a Gong call link returns the call in `richDocumentData.content`: a JSON
string whose `comments` array holds one entry per utterance (`author`, `text`, `createdAt`).
Save that read_document result to a file (or pass the file Claude Code saved it to when it was
too large to show), then:

  python3 gong_transcript.py --file <saved result> --out <scratchpad>/transcript.txt \
      [--speaker HASH=Name ...]

It writes one line per utterance, `[HH:MM:SS] speaker: text`, timed from the start of the call,
and prints JSON: utterance count, start, end, length in minutes, and each speaker with their
number of utterances. LaunchDarkly people show as their email; some external speakers show
only as a hex hash. Pass `--speaker '<hash>=<name>'` (the whole hash, or its first 6 or more
characters; quote it) to name them, e.g. `--speaker 'A1B2C3=Sam (unsure)'` for a name you're
unsure of.

Only the transcript is written. Gong's own call summary, also in the content, is left out.
"""
import argparse
import datetime
import json
import re
import sys

HASH = re.compile(r"[0-9A-F]{24,}")


def out(obj):
    print(json.dumps(obj, indent=2))


def fail(msg):
    out({"error": msg})
    sys.exit(1)


def find_content(obj):
    """richDocumentData.content anywhere in a parsed read_document result."""
    if isinstance(obj, dict):
        rich = obj.get("richDocumentData")
        if isinstance(rich, dict) and isinstance(rich.get("content"), str):
            return rich["content"]
        if "comments" in obj:
            return obj
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            found = find_content(v)
            if found is not None:
                return found
    return None


def tool_text(obj):
    """The text of a result Claude Code saved to a file: `[{"type": "text", "text": ...}]`."""
    if isinstance(obj, list) and obj and all(isinstance(b, dict) and b.get("type") == "text" for b in obj):
        return "\n".join(b.get("text", "") for b in obj)
    return None


def load_comments(raw):
    content = None
    try:
        parsed = json.loads(raw)
        text = tool_text(parsed)
        if text is not None:
            return load_comments(text)
        content = find_content(parsed)
    except ValueError:
        # Glean's text output: a line `content: "<JSON string>"`.
        m = re.search(r'^\s*content: (".*")\s*$', raw, re.M)
        if m:
            content = json.loads(m.group(1))
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except ValueError:
            content = None
    if not isinstance(content, dict) or not content.get("comments"):
        return None
    return content["comments"]


def when(c):
    return datetime.datetime.fromisoformat(c["createdAt"].replace("Z", "+00:00"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, help="the saved read_document result")
    p.add_argument("--out", required=True, help="where to write the transcript")
    p.add_argument("--speaker", action="append", default=[], help="HASH=Name for an external speaker")
    a = p.parse_args()

    with open(a.file, encoding="utf-8", errors="replace") as f:
        comments = load_comments(f.read())
    if not comments:
        fail("no transcript in that result: the call may not be in Glean yet")

    names = {}
    for s in a.speaker:
        key, _, name = s.partition("=")
        if not key or not name:
            fail("--speaker needs HASH=Name, got %r" % s)
        names[key.strip().upper()] = name.strip()

    def speaker(author):
        author = (author or "").strip() or "Unknown"
        if HASH.fullmatch(author):
            for key, name in names.items():
                if len(key) >= 6 and author.startswith(key):
                    return name
            return "Speaker " + author[:6]
        return author

    comments = sorted(comments, key=when)
    start = when(comments[0])
    counts = {}
    with open(a.out, "w") as f:
        for c in comments:
            secs = int((when(c) - start).total_seconds())
            who = speaker(c.get("author"))
            counts[who] = counts.get(who, 0) + 1
            text = re.sub(r"\s*\u0004\s*", " ", c.get("text", "")).strip()
            f.write("[%02d:%02d:%02d] %s: %s\n" % (secs // 3600, secs // 60 % 60, secs % 60, who, text))

    end = when(comments[-1])
    out({"file": a.out, "utterances": len(comments),
         "start": start.isoformat(timespec="seconds"), "end": end.isoformat(timespec="seconds"),
         "minutes": round((end - start).total_seconds() / 60),
         "speakers": dict(sorted(counts.items(), key=lambda kv: -kv[1]))})


if __name__ == "__main__":
    main()
