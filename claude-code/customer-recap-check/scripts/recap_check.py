#!/usr/bin/env python3
"""Helper for the customer-recap-check skill: settings, processed calls, the Active Customers
Doc, the run log, Slack file uploads, and Gong "call is ready" emails.

Run it with the Drive helper's Python (it reuses gdrive.py from the customer-meeting-recap
skill, installed next to this one):

  ~/.local/share/sa-skills/venv/bin/python -W ignore recap_check.py <command> ...

Commands (every one prints JSON):
  config get [KEY]                      read ~/.config/sa-skills/config.json (one key, or all)
  config set KEY VALUE                  set one key, keeping the others

  customers init --folder ID            create the Active Customers Doc in that folder, if missing
  customers read --folder ID [--all]    rows of the Active Customers Doc (Status Active only, unless --all)

  calls get --id CALL_ID                what happened to a Gong call before, or null
  calls mark --id CALL_ID --status S [--customer C] [--date D] [--title T] [--url U]
             [--duration D] [--note N] [--slack-ts TS] [--missing LINKS|none] [--reminded YYYY-MM-DD]
                                        record a call: waiting, done, held, skipped, error or dry-run
  calls waiting                         calls whose Gong email came in, still to be recapped
                                        (status waiting, or dry-run)
  calls held                            calls waiting for an answer in Slack: held, or done with
                                        links still missing

  log add --kind activity|audit --run RUN_ID --text TEXT [--dry-run]
                                        append one line, stamped with the current time, to the
                                        run log ~/.config/sa-skills/recap-check-log.md

  slack-upload --url URL --file PATH    upload a file's bytes to a Slack upload URL

  gong-email --file PATH                read a Gong "call is ready" email (Glean read_document
                                        output, saved to a file) and print the call's ID, link,
                                        title, account, date and duration. Never the Key points

Nothing here reads or prints a token or secret.
"""
import argparse
import base64
import datetime
import html
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request

HOME_CONFIG = os.path.expanduser("~/.config/sa-skills")
CONFIG = os.path.join(HOME_CONFIG, "config.json")
CALLS = os.path.join(HOME_CONFIG, "processed-calls.json")
LOG_FILE = os.path.join(HOME_CONFIG, "recap-check-log.md")
# Lines queued by older versions, which flushed them to Drive Docs: moved into LOG_FILE.
PENDING = os.path.join(HOME_CONFIG, "logs", "pending.jsonl")
LOG_KINDS = ("activity", "audit")
STATUSES = ("waiting", "done", "held", "skipped", "error", "dry-run")
CUSTOMERS_DOC = "Active Customers"
# Settings that hold credentials never live in config.json, but refuse them anyway.
SECRET_WORDS = ("token", "secret", "password", "key")

CUSTOMERS_TEMPLATE = """# Active Customers

The meeting-recap check only recaps calls with customers on this list marked **Active**: it
starts when Gong emails you that a call is ready, and matches the call to a row here. Add a row per customer you're working with; set Status to
Paused to leave one out. No links or email domains here: links live in each customer's
CLAUDE.md.

- **Customer:** the name you use, the same as the customer's folder name.
- **Folder:** the customer's folder inside your customer folders, e.g. acme/.
- **Gong account:** the account name Gong shows for the customer's calls.
- **Meeting title words:** words that appear in the titles of your meetings with them (a
  backup, when Gong shows another account name).
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
    if a.action == "waiting":
        out({k: v for k, v in calls.items() if v.get("status") in ("waiting", "dry-run")})
        return
    if a.action == "held":
        out({k: v for k, v in calls.items() if v.get("status") == "held"
             or (v.get("status") == "done" and v.get("missing"))})
        return
    if a.status not in STATUSES:
        fail("status must be one of %s" % ", ".join(STATUSES))
    entry = calls.get(a.id, {})
    entry.update({k: v for k, v in (("status", a.status), ("customer", a.customer), ("date", a.date),
                                    ("title", a.title), ("url", a.url), ("duration", a.duration),
                                    ("note", a.note),
                                    ("slack_ts", a.slack_ts), ("reminded", a.reminded)) if v})
    if a.missing:
        entry["missing"] = [] if a.missing == "none" else [m.strip() for m in a.missing.split(",") if m.strip()]
    entry.setdefault("first_seen", datetime.datetime.now().isoformat(timespec="seconds"))
    entry["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    calls[a.id] = entry
    write_private(CALLS, calls)
    out({"marked": a.id, "entry": entry})


# --- logs -----------------------------------------------------------------

def cmd_log(a):
    lines = []
    try:
        with open(PENDING) as f:
            lines = [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        pass
    now = datetime.datetime.now()
    lines.append({"kind": a.kind, "run": a.run,
                  "text": "%s · %s%s" % (now.strftime("%Y-%m-%d %H:%M:%S"),
                                        "dry run · " if a.dry_run else "", a.text)})
    try:
        with open(LOG_FILE) as f:
            text = f.read()
        add = ""
    except FileNotFoundError:
        text = ""
        add = ("# Recap check log\n\nOne section per run, oldest first. **activity**: a step or "
               "tool call. **audit**: a change made in Drive, Jira or Slack.\n")
    i = text.rfind("\n## Run ")
    run = text[i + 8:text.index("\n", i + 1)].strip() if i >= 0 else None
    for q in lines:
        if q["run"] != run:
            run = q["run"]
            add += "\n## Run %s\n\n" % run
        when, _, rest = q["text"].partition(" · ")
        add += "- %s · %s · %s\n" % (when, q["kind"], rest)
    os.makedirs(HOME_CONFIG, exist_ok=True)
    fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write(add)
    if os.path.exists(PENDING):
        os.remove(PENDING)
        try:
            os.rmdir(os.path.dirname(PENDING))
        except OSError:
            pass
    out({"logged": add.rstrip().splitlines()[-1][2:], "file": LOG_FILE})


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


# --- Gong "call is ready" email --------------------------------------------

READY_SUFFIX = ": Call recording and analysis is ready"


def gmail_parts(raw):
    """Decoded bodies of every part of the raw Gmail API JSON in a read_document result.

    The JSON sits inside a quoted snippet, so its quotes may be escaped once or twice. The
    base64url alphabet has no quote or backslash, so a pattern that skips those finds every
    "data" field however deeply it's escaped."""
    parts = []
    for data in re.findall(r'"data\\*"\s*:\s*\\*"([A-Za-z0-9_\-]+=*)', raw):
        try:
            parts.append(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace"))
        except ValueError:
            continue
    return parts


def html_text(fragment):
    text = re.sub(r"<(style|script)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def cmd_gong_email(a):
    with open(a.file, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    body = next((p for p in gmail_parts(raw) if "gong.io/call?id=" in p), None)
    if body is None:
        fail("no Gong call link found in that email (is it a Gong 'call is ready' email?)")

    link = html.unescape(re.search(r'https://[A-Za-z0-9.-]+\.gong\.io/call\?[^"\'\s<>]+', body).group(0))
    u = urllib.parse.urlsplit(link)
    call_id = urllib.parse.parse_qs(u.query).get("id", [""])[0]
    if not call_id.isdigit():
        fail("the Gong link in that email has no call ID")

    m = re.search(r'class="entity-title"[^>]*>(.*?)</span>', body, re.S)
    title = html_text(m.group(1)) if m else ""
    if not title:
        m = re.search(r'^\s*title: "(.*)"\s*$', raw, re.M)
        title = (m.group(1) if m else "").replace(READY_SUFFIX, "").strip()

    # The account is the link to Gong's account page; date and duration follow it, set off by bullets.
    m = re.search(r'<a [^>]*href="[^"]*\.gong\.io/account\?[^"]*"[^>]*>(.*?)</a>', body, re.S)
    account = html_text(m.group(1)) if m else ""
    rest = html_text(body[m.end():] if m else body)
    m = re.match(r"\W*([A-Z][a-z]{2} \d{1,2}, \d{4})\W*•?\s*(.+?)\s*(?:LaunchDarkly:|Customer:|Go to call|$)", rest)
    date = duration = ""
    if m:
        try:
            date = datetime.datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat()
        except ValueError:
            date = m.group(1)
        duration = m.group(2).strip(" •")

    m = re.search(r'internalDate\\*"\s*:\s*\\*"(\d+)', raw)
    received = (datetime.datetime.fromtimestamp(int(m.group(1)) / 1000).isoformat(timespec="seconds")
                if m else None)
    out({"gong_call_id": call_id,
         "call_url": "%s://%s%s?id=%s" % (u.scheme, u.netloc, u.path, call_id),
         "title": title, "account": account, "date": date, "duration": duration,
         "email_received": received})


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
    ca.add_argument("action", choices=["get", "mark", "waiting", "held"])
    ca.add_argument("--id")
    for opt in ("--status", "--customer", "--date", "--title", "--url", "--duration", "--note", "--slack-ts",
                "--missing", "--reminded"):
        ca.add_argument(opt)

    lg = sub.add_parser("log")
    lg.add_argument("action", choices=["add"])
    lg.add_argument("--kind", choices=LOG_KINDS)
    lg.add_argument("--run")
    lg.add_argument("--text")
    lg.add_argument("--dry-run", action="store_true")

    su = sub.add_parser("slack-upload")
    su.add_argument("--url", required=True)
    su.add_argument("--file", required=True)

    ge = sub.add_parser("gong-email")
    ge.add_argument("--file", required=True)

    a = p.parse_args()
    if a.cmd == "calls" and a.action in ("get", "mark") and not a.id:
        fail("calls %s needs --id" % a.action)
    if a.cmd == "log" and a.action == "add" and not (a.kind and a.run and a.text):
        fail("log add needs --kind, --run and --text")
    {"config": cmd_config, "customers": cmd_customers, "calls": cmd_calls,
     "log": cmd_log, "slack-upload": cmd_slack_upload, "gong-email": cmd_gong_email}[a.cmd](a)


if __name__ == "__main__":
    main()
