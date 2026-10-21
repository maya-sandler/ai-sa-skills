#!/usr/bin/env python3
"""Create a Jira work item with acli from a Markdown description.

Converts the Markdown to Atlassian Document Format (ADF), builds the JSON that
`acli jira workitem create --from-json` takes, creates the item, then reads it
back to confirm the parent epic, due date and assignee came out as asked.

Assigned to the signed-in user by default; pass --unassigned for someone else's task.

Usage:
  jira_ticket.py --project KEY --summary "Alex: Build Relay Proxy Demo" --description-file desc.md \
      [--type Task] [--parent KEY-42] [--due 2026-10-30] [--unassigned] [--dry-run]

Prints one JSON line: {"key": ..., "url": ..., "parent": ..., "duedate": ..., "warnings": [...]}
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

INLINE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)|\*\*([^*]+)\*\*|(https?://[^\s)]+)")


def inline_nodes(text):
    """Turn one line of Markdown into ADF text nodes (links, bold, bare URLs)."""
    nodes, pos = [], 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            nodes.append({"type": "text", "text": text[pos:m.start()]})
        label, url, bold, bare = m.groups()
        if url:
            nodes.append({"type": "text", "text": label, "marks": [{"type": "link", "attrs": {"href": url}}]})
        elif bold:
            nodes.append({"type": "text", "text": bold, "marks": [{"type": "strong"}]})
        else:
            nodes.append({"type": "text", "text": bare, "marks": [{"type": "link", "attrs": {"href": bare}}]})
        pos = m.end()
    if pos < len(text):
        nodes.append({"type": "text", "text": text[pos:]})
    return nodes or [{"type": "text", "text": " "}]


def markdown_to_adf(md):
    """Support the subset the ticket template uses: #-headings, - bullets, paragraphs."""
    content, bullets, para = [], [], []

    def flush():
        if para:
            content.append({"type": "paragraph", "content": inline_nodes(" ".join(para))})
            para.clear()
        if bullets:
            content.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": inline_nodes(b)}]}
                for b in bullets]})
            bullets.clear()

    for raw in md.splitlines():
        line = raw.rstrip()
        heading = re.match(r"^(#{1,6})\s+(.*)", line)
        bullet = re.match(r"^\s*[-*]\s+(.*)", line)
        if not line.strip():
            flush()
        elif heading:
            flush()
            content.append({"type": "heading", "attrs": {"level": len(heading.group(1))},
                            "content": inline_nodes(heading.group(2))})
        elif bullet:
            if para:
                flush()
            bullets.append(bullet.group(1))
        else:
            if bullets:
                flush()
            para.append(line.strip())
    flush()
    return {"type": "doc", "version": 1, "content": content}


def created_key(output, project, parent):
    """Find the new item's key. The output also mentions the parent's key, so skip it."""
    try:
        data = json.loads(output)
        if isinstance(data, dict) and data.get("key"):
            return data["key"]
    except ValueError:
        pass
    keys = [k for k in re.findall(r"\b%s-\d+\b" % re.escape(project), output) if k != parent]
    return keys[0] if keys else None


def current_site():
    out = subprocess.run(["acli", "jira", "auth", "status"], capture_output=True, text=True).stdout
    m = re.search(r"Site:\s*(\S+)", out)
    return m.group(1) if m else "<your-site>.atlassian.net"


def current_email():
    out = subprocess.run(["acli", "jira", "auth", "status"], capture_output=True, text=True).stdout
    m = re.search(r"Email:\s*(\S+)", out)
    return m.group(1) if m else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summary", required=True)
    p.add_argument("--description-file", required=True)
    p.add_argument("--project", required=True, help="Jira project key")
    p.add_argument("--type", default="Task")
    p.add_argument("--parent")
    p.add_argument("--due", help="YYYY-MM-DD")
    p.add_argument("--unassigned", action="store_true", help="leave it unassigned (someone else's task)")
    p.add_argument("--dry-run", action="store_true", help="print the JSON instead of creating")
    a = p.parse_args()

    with open(a.description_file) as f:
        description = markdown_to_adf(f.read())

    item = {"projectKey": a.project, "type": a.type, "summary": a.summary, "description": description}
    email = current_email()
    if email and not a.unassigned:
        item["assignee"] = email
    if a.parent:
        item["parentIssueId"] = a.parent
    if a.due:
        item["additionalAttributes"] = {"duedate": a.due}

    if a.dry_run:
        print(json.dumps(item, indent=2))
        return

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(item, f)
        path = f.name
    try:
        res = subprocess.run(["acli", "jira", "workitem", "create", "--from-json", path, "--json"],
                             capture_output=True, text=True)
    finally:
        os.unlink(path)
    key = created_key(res.stdout, a.project, a.parent)
    if res.returncode != 0 or not key:
        sys.exit("create failed:\n" + res.stdout + res.stderr)

    # Read back to confirm the fields acli may silently drop.
    view = subprocess.run(["acli", "jira", "workitem", "view", key, "--fields", "parent,duedate,assignee", "--json"],
                          capture_output=True, text=True)
    fields = {}
    try:
        fields = json.loads(view.stdout).get("fields", {})
    except ValueError:
        pass
    parent = (fields.get("parent") or {}).get("key")
    warnings = []
    if a.parent and parent != a.parent:
        warnings.append("parent not set: link %s to epic %s in Jira" % (key, a.parent))
    if a.due and fields.get("duedate") != a.due:
        warnings.append("due date not set: set %s on %s in Jira" % (a.due, key))
    assignee = (fields.get("assignee") or {}).get("emailAddress")
    if a.unassigned and fields.get("assignee"):
        # The project may have a default assignee; clear it.
        subprocess.run(["acli", "jira", "workitem", "edit", "--key", key, "--remove-assignee", "--yes"],
                       capture_output=True, text=True)
        assignee = None
    print(json.dumps({"key": key, "url": "https://%s/browse/%s" % (current_site(), key), "parent": parent,
                      "duedate": fields.get("duedate"), "assignee": assignee, "warnings": warnings}))


if __name__ == "__main__":
    main()
