#!/usr/bin/env python3
"""Fail if the repo contains links, IDs, emails or secrets that could identify a customer or a person.

This repo is public, so it can't list customer names to block (that list would itself leak them).
Instead it allows only known-safe patterns and flags everything else:

- URLs: only the public setup pages and endpoints the skills need, plus placeholders.
- Email addresses: only made-up ones (you@yourcompany.com) and placeholders.
- Jira keys: only the made-up KEY-123 / ABC-123 style.
- Long IDs: 24-character hex IDs (account IDs) and Salesforce record IDs.
- Secrets: token and key formats.

Usage: privacy_scan.py [--messages <git range>]   (also scans commit messages in that range)
"""
import re
import subprocess
import sys

ALLOWED_URL_PREFIXES = (
    "https://console.cloud.google.com/",
    "https://id.atlassian.com/manage-profile/security/api-tokens",
    "https://accounts.google.com/o/oauth2/auth",
    "https://oauth2.googleapis.com/token",
    "https://www.googleapis.com/auth/drive.file",
    "https://launchdarkly.com/docs/",
    "http://localhost",
)
# A URL is also fine when it's only a template: a placeholder, a format string, or a bare prefix.
TEMPLATE_URL = re.compile(r"(\{\{|<|%s|\.\.\.|\*)|^https?://drive\.google\.com/drive/folders/$|^https?://\}?$")
URL = re.compile(r"https?://[^\s)`\"'<>\]]*")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
ALLOWED_EMAILS = {"you@yourcompany.com", "noreply@anthropic.com"}
JIRA_KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-\d+\b")
ALLOWED_KEY_PREFIXES = {"KEY", "ABC", "UTF", "ISO", "SHA", "RFC", "TLS", "HTTP", "GPT", "RSA"}
HEX_ID = re.compile(r"\b[0-9a-f]{24}\b")
SALESFORCE_ID = re.compile(r"\b(00[0-9A-Za-z]{13}(?:[0-9A-Za-z]{3})?|a[0-9A-Z]{2}[0-9A-Za-z]{12,15})\b")
SECRETS = re.compile(r"ATATT[0-9A-Za-z_\-=]{20,}|GOCSPX-[0-9A-Za-z_\-]{10,}|gh[pousr]_[0-9A-Za-z]{20,}"
                     r"|xox[abpr]-[0-9A-Za-z-]{10,}|AKIA[0-9A-Z]{16}|sk-ant-[0-9A-Za-z_\-]{10,}")
SKIP_FILES = {".github/scripts/privacy_scan.py"}  # this file names the patterns it looks for


def problems_in(text):
    for n, line in enumerate(text.splitlines(), 1):
        for url in URL.findall(line):
            url = url.rstrip(".,;:")
            if not url.startswith(ALLOWED_URL_PREFIXES) and not TEMPLATE_URL.search(url):
                yield n, "link not on the allowlist: %s" % url
        for email in EMAIL.findall(line):
            if email.lower() not in ALLOWED_EMAILS:
                yield n, "email address: %s" % email
        for m in JIRA_KEY.finditer(line):
            if m.group(1) not in ALLOWED_KEY_PREFIXES:
                yield n, "real-looking Jira key: %s (use KEY-123)" % m.group(0)
        for pattern, label in ((HEX_ID, "24-character ID (looks like an account ID)"),
                               (SALESFORCE_ID, "Salesforce-style record ID"),
                               (SECRETS, "token or secret")):
            for m in pattern.finditer(line):
                yield n, "%s: %s" % (label, m.group(0)[:12] + "...")


def main():
    found = 0
    files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
    for path in files:
        if path in SKIP_FILES:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for n, msg in problems_in(text):
            print("::error file=%s,line=%d::%s" % (path, n, msg))
            found += 1

    if len(sys.argv) == 3 and sys.argv[1] == "--messages":
        log = subprocess.run(["git", "log", "--format=%H%n%B%n--end--", sys.argv[2]],
                             capture_output=True, text=True, check=True).stdout
        for block in log.split("--end--"):
            lines = block.strip().splitlines()
            if not lines:
                continue
            for _, msg in problems_in("\n".join(lines[1:])):
                print("::error::commit %s message: %s" % (lines[0][:7], msg))
                found += 1

    if found:
        print("\n%d problem(s). This repo is public: no customer names, customer or internal links, "
              "account IDs, real emails or secrets. Use made-up examples (Acme, Alex, KEY-123)." % found)
        sys.exit(1)
    print("Privacy scan passed.")


if __name__ == "__main__":
    main()
