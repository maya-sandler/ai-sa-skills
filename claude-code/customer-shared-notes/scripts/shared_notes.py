#!/usr/bin/env python3
"""Helper for the customer-shared-notes skill: the ledger of recaps already in each shared Doc.

The ledger is ~/.config/sa-skills/shared-notes.json. It maps each Master Engagement Doc's ID to
the recap Doc IDs added to it, with each recap's Gong call ID when it has one. It holds only IDs,
never Doc names or content.

  python3 shared_notes.py <command> ...

Commands (every one prints JSON):
  ledger get --doc DOC_ID                      the recaps already added to that shared Doc, or null
  ledger check --doc DOC_ID --recap RECAP_ID [--call CALL_ID]
                                               is this recap (or this Gong call) already in that Doc?
  ledger add --doc DOC_ID --recap RECAP_ID [--call CALL_ID]
                                               record that the recap was added (keeps everything else)
"""
import argparse
import datetime
import json
import os
import sys

LEDGER = os.path.join(os.path.expanduser("~/.config/sa-skills"), "shared-notes.json")


def out(obj):
    print(json.dumps(obj, indent=2))


def fail(msg):
    out({"error": msg})
    sys.exit(1)


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return default


def write_private(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def cmd_ledger(a):
    ledger = load(LEDGER, {})
    recaps = ledger.get(a.doc, {}).get("recaps", {})
    if a.action == "get":
        out(ledger.get(a.doc))
        return
    if a.action == "check":
        if a.recap in recaps:
            out({"already_there": True, "matched_by": "recap", "recap": a.recap})
            return
        for rid, r in recaps.items():
            if a.call and r.get("call") == a.call:
                out({"already_there": True, "matched_by": "call", "recap": rid})
                return
        out({"already_there": False})
        return
    # add: reload right before writing, so another run's entries are kept.
    ledger = load(LEDGER, {})
    entry = ledger.setdefault(a.doc, {}).setdefault("recaps", {}).get(a.recap, {})
    if a.call:
        entry["call"] = a.call
    entry.setdefault("added", datetime.datetime.now().isoformat(timespec="seconds"))
    ledger[a.doc]["recaps"][a.recap] = entry
    write_private(LEDGER, ledger)
    out({"recorded": a.recap, "doc": a.doc, "entry": entry})


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("ledger")
    lg.add_argument("action", choices=["get", "check", "add"])
    lg.add_argument("--doc", required=True)
    lg.add_argument("--recap")
    lg.add_argument("--call")
    a = p.parse_args()
    if a.action in ("check", "add") and not a.recap:
        fail("ledger %s needs --recap" % a.action)
    cmd_ledger(a)


if __name__ == "__main__":
    main()
