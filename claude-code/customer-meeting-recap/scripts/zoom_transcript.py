#!/usr/bin/env python3
"""Turn a Zoom meeting read with the Zoom connector into a readable transcript file.

The Zoom connector's `get_meeting_assets` returns the meeting as one JSON object. Its transcript
is in one of three places, depending on the meeting:

  recording.transcripts[].timeline[]     a cloud recording's transcript, with timestamps
  meeting_transcript.transcript_items[]  AI Companion, for meetings you host
  my_notes.transcript.transcript_items[] AI Companion, for meetings you only attend

It can also carry the AI Companion summary (`meeting_summary.summary_markdown`) and your own
"my notes" (`my_notes.content_markdown`). Save the get_meeting_assets result to a file (or pass
the file Claude Code saved it to when it was too large to show), then:

  python3 zoom_transcript.py --file <saved result> --out <scratchpad>/transcript.txt \
      [--summary-out <scratchpad>/zoom-summary.md]

It writes one line per utterance, `[HH:MM:SS] speaker: text` (`[--:--:--]` when Zoom gives no
time), and prints JSON: where the transcript came from, utterance count, length in minutes
(null when Zoom gives no times), each speaker with their number of utterances, and whether an
AI summary or "my notes" are there. With `--summary-out`, it also writes the AI summary and
"my notes" to that file.

Don't trust the `has_transcript` / `has_summary` flags in Zoom search results: they are often
false for meetings that have both. Read the assets and let this script judge.
"""
import argparse
import json
import re
import sys

# Zoom writes this instead of a summary when a meeting was too short.
PLACEHOLDER = re.compile(r"insufficient\s+(transcript|audio|content)|try again with a longer", re.I)
TASK_LINK = re.compile(r"\[\]\(https://tasks\.zoom\.us[^)]*\)")


def out(obj):
    print(json.dumps(obj, indent=2))


def fail(msg):
    out({"error": msg})
    sys.exit(1)


def unwrap(obj, depth=0):
    """The get_meeting_assets object inside a saved tool result: a JSON string, a
    `[{"type": "text", "text": ...}]` list, or a single-key wrapper."""
    if depth > 4:
        return obj
    if isinstance(obj, str):
        try:
            return unwrap(json.loads(obj), depth + 1)
        except ValueError:
            return obj
    if isinstance(obj, list) and obj and all(isinstance(b, dict) and b.get("type") == "text" for b in obj):
        return unwrap("\n".join(b.get("text", "") for b in obj), depth + 1)
    if isinstance(obj, dict) and len(obj) == 1:
        (key, value), = obj.items()
        if key in ("result", "content", "data", "output"):
            return unwrap(value, depth + 1)
    return obj


def seconds(ts):
    """'00:59:47.940' → 3587; None when it isn't a time."""
    m = re.fullmatch(r"(\d+):(\d{2}):(\d{2})(?:\.\d+)?", str(ts or "").strip())
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None


def utterances(data):
    """[(seconds or None, speaker, text)] and where they came from."""
    recording = data.get("recording") if isinstance(data.get("recording"), dict) else {}
    lines = []
    for t in recording.get("transcripts") or []:
        for item in (t or {}).get("timeline") or []:
            text = str((item or {}).get("text") or "").strip()
            if text:
                lines.append((seconds(item.get("ts")), str(item.get("display_name") or "Unknown").strip(), text))
    if lines:
        return lines, "recording"
    my_notes = data.get("my_notes") if isinstance(data.get("my_notes"), dict) else {}
    for where, container in (("meeting_transcript", data.get("meeting_transcript")),
                             ("my_notes", my_notes.get("transcript"))):
        items = (container or {}).get("transcript_items") if isinstance(container, dict) else None
        for item in items or []:
            text = str(item.get("text") if isinstance(item, dict) else item or "").strip()
            if not text:
                continue
            # Items read "Speaker Name: words"; display_name only when there's no prefix.
            if ": " in text:
                who, text = text.split(": ", 1)
            else:
                who = (item.get("display_name") if isinstance(item, dict) else "") or "Unknown"
            lines.append((seconds(item.get("ts")) if isinstance(item, dict) else None, who.strip(), text.strip()))
        if lines:
            return lines, where
    return [], None


def summary_and_notes(data):
    ms = data.get("meeting_summary") if isinstance(data.get("meeting_summary"), dict) else {}
    summary = ms.get("summary_markdown") if isinstance(ms.get("summary_markdown"), str) else ""
    if not summary.strip() or PLACEHOLDER.search(summary):
        summary = ""
    my_notes = data.get("my_notes") if isinstance(data.get("my_notes"), dict) else {}
    notes = my_notes.get("content_markdown") if isinstance(my_notes.get("content_markdown"), str) else ""
    return TASK_LINK.sub("", summary).strip(), TASK_LINK.sub("", notes).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, help="the saved get_meeting_assets result")
    p.add_argument("--out", required=True, help="where to write the transcript")
    p.add_argument("--summary-out", help="where to write the AI summary and 'my notes', if any")
    a = p.parse_args()

    with open(a.file, encoding="utf-8", errors="replace") as f:
        data = unwrap(f.read())
    if not isinstance(data, dict) or not any(k in data for k in ("meeting_uuid", "topic", "my_notes")):
        fail("that file isn't a get_meeting_assets result: save the whole response and try again")

    lines, source = utterances(data)
    summary, notes = summary_and_notes(data)
    result = {"meeting_uuid": data.get("meeting_uuid"), "topic": data.get("topic"),
              "start_time": data.get("start_time"), "source": source, "utterances": len(lines),
              "minutes": None, "speakers": {}, "has_summary": bool(summary), "has_my_notes": bool(notes)}

    if lines:
        counts = {}
        with open(a.out, "w") as f:
            for secs, who, text in lines:
                counts[who] = counts.get(who, 0) + 1
                stamp = "--:--:--" if secs is None else "%02d:%02d:%02d" % (secs // 3600, secs // 60 % 60, secs % 60)
                f.write("[%s] %s: %s\n" % (stamp, who, text))
        times = [s for s, _, _ in lines if s is not None]
        if times:
            result["minutes"] = round((max(times) - min(times)) / 60)
        result["file"] = a.out
        result["speakers"] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    if a.summary_out and (summary or notes):
        with open(a.summary_out, "w") as f:
            if summary:
                f.write("# Zoom AI Companion summary\n\n%s\n\n" % summary)
            if notes:
                f.write("# My notes (Zoom)\n\n%s\n" % notes)
        result["summary_file"] = a.summary_out

    if not lines and not (summary or notes):
        result["error"] = "no transcript, summary or notes in this meeting yet"
        out(result)
        sys.exit(1)
    out(result)


if __name__ == "__main__":
    main()
