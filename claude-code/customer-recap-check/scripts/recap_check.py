#!/usr/bin/env python3
"""Helper for the customer-recap-check skill: settings, processed calls, the Active Customers
Doc, the activity and audit logs, and Slack file uploads.

Run it with the Drive helper's Python (it reuses gdrive.py from the customer-meeting-recap
skill, installed next to this one):

  ~/.local/share/sa-skills/venv/bin/python -W ignore recap_check.py <command> ...

Commands (every one prints JSON):
  config get [KEY]                      read ~/.config/sa-skills/config.json (one key, or all)
  config set KEY VALUE                  set one key, keeping the others

  customers init --folder ID            create the Active Customers Doc in that folder, if missing
  customers read --folder ID [--all]    rows of the Active Customers Doc (Status Active only, unless --all)

  calls get --id CALL_ID                what happened to a Gong call before, or null
  calls mark --id CALL_ID --status S [--customer C] [--date D] [--title T] [--note N] [--slack-ts TS]
                                        record a call: done, held, skipped, error or dry-run
  calls held                            calls waiting for an answer

  log add --kind activity|audit --run RUN_ID --text TEXT [--dry-run]
                                        queue one log line (time is added for you)
  log flush --folder ID                 append queued lines to this month's log Docs in Drive

  slack-upload --url URL --file PATH    upload a file's bytes to a Slack upload URL

Nothing here reads or prints a token or secret.
"""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile
import urllib.request

HOME_CONFIG = os.path.expanduser("~/.config/sa-skills")
CONFIG = os.path.join(HOME_CONFIG, "config.json")
CALLS = os.path.join(HOME_CONFIG, "processed-calls.json")
LOG_DIR = os.path.join(HOME_CONFIG, "logs")
PENDING = os.path.join(LOG_DIR, "pending.jsonl")
STATUSES = ("done", "held", "skipped", "error", "dry-run")
CUSTOMERS_DOC = "Active Customers"
LOG_DOC = {"activity": "Recap Workflow – Activity Log – %s",
           "audit": "Recap Workflow – Audit Log – %s"}
# Settings that hold credentials never live in config.json, but refuse them anyway.
SECRET_WORDS = ("token", "secret", "password", "key")

CUSTOMERS_TEMPLATE = """# Active Customers

The meeting-recap check only looks at customers on this list marked **Active**, and only on
days you have a meeting with them. Add a row per customer you're working with; set Status to
Paused to leave one out. No links or email domains here: links live in each customer's
CLAUDE.md.

- **Customer:** the name you use, the same as the customer's folder name.
- **Folder:** the customer's folder inside your customer folders, e.g. acme/.
- **Gong account:** the account name Gong shows for the customer's calls.
- **Meeting title words:** words that appear in the titles of your meetings with them.
- **Status:** Active or Paused. The example row is ignored.

| Customer | Folder | Gong account | Meeting title words | Status |
| --- | --- | --- | --- | --- |
| Acme | acme/ | Acme Corporation | Acme | Example |
"""


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


def gdrive():
    """Import gdrive.py from the recap skill installed next to this one."""
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "..", "..", "customer-meeting-recap", "scripts"))
    import gdrive as g  # noqa: E402
    return g


def doc_markdown(g, svc, doc_id):
    data = svc.files().export(fileId=doc_id, mimeType="text/markdown").execute()
    return data.decode("utf-8") if isinstance(data, bytes) else data


def save_markdown(g, svc, folder, name, text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
        path = f.name
    try:
        return g.save(svc, folder, name, path)
    finally:
        os.unlink(path)


# --- config ---------------------------------------------------------------

def cmd_config(a):
    cfg = load(CONFIG, {})
    if a.action == "get":
        out(cfg.get(a.key) if a.key else cfg)
        return
    if not a.key or a.value is None:
        fail("config set needs KEY and VALUE")
    if any(w in a.key.lower() for w in SECRET_WORDS):
        fail("config.json never holds credentials; %r looks like one" % a.key)
    cfg[a.key] = a.value
    write_private(CONFIG, cfg)
    out({"saved": a.key})


# --- Active Customers Doc -------------------------------------------------

def unescape(cell):
    """Google's Markdown export escapes some characters; undo that."""
    return re.sub(r"\\(.)", r"\1", cell).strip()


def parse_table(md):
    rows, header = [], None
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if header is not None and rows:
                break
            continue
        cells = [unescape(c) for c in line.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
        elif not all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            rows.append(dict(zip(header, cells)))
    return rows


def cmd_customers(a):
    g = gdrive()
    svc = g.drive()
    found = g.find(svc, a.folder, name=CUSTOMERS_DOC)
    if a.action == "init":
        if found:
            out({"exists": found[0]})
        else:
            f = save_markdown(g, svc, a.folder, CUSTOMERS_DOC, CUSTOMERS_TEMPLATE)
            out({"created": f})
        return
    if not found:
        fail("no Active Customers Doc in that folder yet: run 'customers init --folder %s'" % a.folder)
    rows = parse_table(doc_markdown(g, svc, found[0]["id"]))
    if not a.all:
        rows = [r for r in rows if r.get("status", "").lower() == "active"]
    out({"doc": found[0].get("webViewLink"), "customers": rows})


# --- processed calls ------------------------------------------------------

def cmd_calls(a):
    calls = load(CALLS, {})
    if a.action == "get":
        out(calls.get(a.id))
        return
    if a.action == "held":
        out({k: v for k, v in calls.items() if v.get("status") == "held"})
        return
    if a.status not in STATUSES:
        fail("status must be one of %s" % ", ".join(STATUSES))
    entry = calls.get(a.id, {})
    entry.update({k: v for k, v in (("status", a.status), ("customer", a.customer), ("date", a.date),
                                    ("title", a.title), ("note", a.note), ("slack_ts", a.slack_ts)) if v})
    entry["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    calls[a.id] = entry
    write_private(CALLS, calls)
    out({"marked": a.id, "entry": entry})


# --- logs -----------------------------------------------------------------

def cmd_log(a):
    if a.action == "add":
        now = datetime.datetime.now()
        line = {"kind": a.kind, "month": now.strftime("%Y-%m"), "run": a.run,
                "text": "%s · %s%s" % (now.strftime("%Y-%m-%d %H:%M:%S"),
                                             "dry run · " if a.dry_run else "", a.text)}
        os.makedirs(LOG_DIR, exist_ok=True)
        fd = os.open(PENDING, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(json.dumps(line) + "\n")
        out({"queued": line["text"]})
        return

    try:
        with open(PENDING) as f:
            queued = [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        queued = []
    if not queued:
        out({"flushed": 0})
        return
    groups = {}
    for q in queued:
        groups.setdefault((q["kind"], q["month"]), []).append(q)
    g = gdrive()
    svc = g.drive()
    written = []
    try:
        for (kind, month), items in sorted(groups.items()):
            name = LOG_DOC[kind] % month
            found = g.find(svc, a.folder, name=name)
            text = doc_markdown(g, svc, found[0]["id"]).rstrip() if found else "# %s" % name
            run = None
            for q in items:
                if q["run"] != run:
                    run = q["run"]
                    text += "\n\n## Run %s\n" % run
                text += "\n- %s" % q["text"]
            f = save_markdown(g, svc, a.folder, name, text + "\n")
            written.append({"doc": name, "lines": len(items), "link": f.get("webViewLink")})
    except Exception as e:  # keep the queue so the next run can retry
        out({"error": "log flush failed, lines kept locally: %s" % e, "written": written})
        sys.exit(1)
    os.remove(PENDING)
    out({"flushed": len(queued), "docs": written})


# --- Slack ----------------------------------------------------------------

def cmd_slack_upload(a):
    with open(a.file, "rb") as f:
        body = f.read()
    req = urllib.request.Request(a.url, data=body, method="POST",
                                 headers={"Content-Type": "text/markdown",
                                          "Content-Length": str(len(body))})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out({"status": r.status, "bytes": len(body)})
    except urllib.error.HTTPError as e:
        fail("upload failed: HTTP %s (a 401 means the URL expired or was changed; get a new one)" % e.code)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("config")
    c.add_argument("action", choices=["get", "set"])
    c.add_argument("key", nargs="?")
    c.add_argument("value", nargs="?")

    cu = sub.add_parser("customers")
    cu.add_argument("action", choices=["init", "read"])
    cu.add_argument("--folder", required=True)
    cu.add_argument("--all", action="store_true")

    ca = sub.add_parser("calls")
    ca.add_argument("action", choices=["get", "mark", "held"])
    ca.add_argument("--id")
    for opt in ("--status", "--customer", "--date", "--title", "--note", "--slack-ts"):
        ca.add_argument(opt)

    lg = sub.add_parser("log")
    lg.add_argument("action", choices=["add", "flush"])
    lg.add_argument("--kind", choices=sorted(LOG_DOC))
    lg.add_argument("--run")
    lg.add_argument("--text")
    lg.add_argument("--folder")
    lg.add_argument("--dry-run", action="store_true")

    su = sub.add_parser("slack-upload")
    su.add_argument("--url", required=True)
    su.add_argument("--file", required=True)

    a = p.parse_args()
    if a.cmd == "calls" and a.action in ("get", "mark") and not a.id:
        fail("calls %s needs --id" % a.action)
    if a.cmd == "log" and a.action == "add" and not (a.kind and a.run and a.text):
        fail("log add needs --kind, --run and --text")
    if a.cmd == "log" and a.action == "flush" and not a.folder:
        fail("log flush needs --folder")
    {"config": cmd_config, "customers": cmd_customers, "calls": cmd_calls,
     "log": cmd_log, "slack-upload": cmd_slack_upload}[a.cmd](a)


if __name__ == "__main__":
    main()
