#!/usr/bin/env bash
# Install the SA customer skills for Claude Code.
#
# Asks where the skills and your customer folders should live and which Jira project to use,
# fills those into the skills, installs them, and sets up the Drive helper's Python libraries. Safe to run again:
# it remembers your answers (in ~/.config/sa-skills/config.json) and offers them as defaults.
#
# It never asks for, reads or prints a token or secret. Signing in to Jira and Google is
# done separately; see ACCESS-AND-SETUP.md.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/claude-code"
CONFIG_DIR="$HOME/.config/sa-skills"
CONFIG="$CONFIG_DIR/config.json"
VENV="$HOME/.local/share/sa-skills/venv"
SKILLS=(customer-meeting-recap customer-session-prep customer-engagement-prep customer-recap-check)

# Show paths under your home folder as ~/..., the way the skills use them.
tilde() { case "$1" in "$HOME"*) printf '~%s' "${1#"$HOME"}" ;; *) printf '%s' "$1" ;; esac; }
expand() { case "$1" in "~") printf '%s' "$HOME" ;; "~/"*) printf '%s/%s' "$HOME" "${1#"~/"}" ;; *) printf '%s' "$1" ;; esac; }
saved() { [ -f "$CONFIG" ] && python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2],""))' "$CONFIG" "$1" || true; }

[ -d "$SRC" ] || { echo "Can't find $SRC. Run this script from inside the ai-sa-skills folder."; exit 1; }

echo "SA customer skills installer"
echo

# 1. Where the skills go.
prev_skills="$(saved skills_dir)"
echo "Where should the skills be installed?"
echo "  1) ~/.claude/skills: available in every Claude Code session (recommended)"
echo "  2) One project only: <project>/.claude/skills"
[ -n "$prev_skills" ] && echo "  (last time: $prev_skills)"
read -r -p "Choose 1 or 2 [1]: " choice
if [ "${choice:-1}" = "2" ]; then
  read -r -p "Project folder (e.g. ~/work/sa-project): " project
  [ -n "$project" ] || { echo "No folder given; stopping."; exit 1; }
  skills_dir="$(expand "$project")/.claude/skills"
else
  skills_dir="$HOME/.claude/skills"
fi

# 2. Where the customer folders go.
prev_customers="$(saved customers_dir)"
default_customers="${prev_customers:-~/work/customers}"
echo
echo "Where should your customer folders live? Each customer gets one folder with a CLAUDE.md"
echo "of links. Recaps and briefs themselves are saved to Google Drive, not here."
read -r -p "Customer folders [$default_customers]: " customers
customers_dir="$(expand "${customers:-$default_customers}")"

# 3. Your Jira site and project (where the recap skill files your tickets).
prev_site="$(saved jira_site)"
if [ -z "$prev_site" ] && command -v acli >/dev/null 2>&1; then
  # acli exits non-zero when it isn't signed in yet; that must not stop the installer.
  prev_site="$( (acli jira auth status 2>/dev/null || true) | sed -n 's/^ *Site: *//p' | head -1)"
fi
echo
echo "Your Jira site, e.g. yourcompany.atlassian.net"
read -r -p "Jira site [${prev_site:-none}]: " site
jira_site="${site:-$prev_site}"
jira_site="${jira_site#https://}"; jira_site="${jira_site%%/*}"
[ -n "$jira_site" ] || { echo "A Jira site is needed; stopping."; exit 1; }
prev_project="$(saved jira_project)"
echo "The key of your own Jira project for customer tasks (the letters in ticket keys like ABC-123)"
read -r -p "Jira project key [${prev_project:-none}]: " project_key
jira_project="$(printf '%s' "${project_key:-$prev_project}" | tr '[:lower:]' '[:upper:]')"
[ -n "$jira_project" ] || { echo "A Jira project key is needed; stopping."; exit 1; }

# 3b. Optional: the team's base Drive folder for customer projects (for engagement history).
prev_history="$(saved history_drive_folder)"
echo
echo "Optional: your team's base Google Drive folder for customer projects. The prep skill"
echo "searches it (through Glean) for earlier engagements with a customer. Press Enter to skip."
read -r -p "Base Drive folder URL [${prev_history:-none}]: " history
history_drive_folder="${history:-${prev_history:-none}}"
history_drive_folder="${history_drive_folder%%\?*}"

# 3c. Optional: your own Drive folder for automatic recaps (Active Customers list + logs).
prev_sa_folder="$(saved sa_drive_folder)"
echo
echo "Optional, for automatic recaps (customer-recap-check): your own Google Drive folder for"
echo "the Active Customers list. Paste the folder link, or press"
echo "Enter to skip (you can set it later by asking Claude to set up the recap check)."
read -r -p "Your Drive folder URL [${prev_sa_folder:-none}]: " sa_folder
sa_folder="${sa_folder%%\?*}"; sa_folder="${sa_folder##*/folders/}"; sa_folder="${sa_folder%%/*}"
sa_drive_folder="${sa_folder:-$prev_sa_folder}"

skills_t="$(tilde "$skills_dir")"
customers_t="$(tilde "$customers_dir")"
echo
echo "Skills:           $skills_t"
echo "Customer folders: $customers_t"
echo "Jira:             project $jira_project on $jira_site"
echo "History folder:   $history_drive_folder"
echo "Your Drive folder: ${sa_drive_folder:-none}"
read -r -p "Go ahead? [Y/n]: " ok
case "${ok:-Y}" in [Yy]*) ;; *) echo "Nothing changed."; exit 0 ;; esac

# 4. Remember the answers.
mkdir -p "$CONFIG_DIR" "$customers_dir" "$skills_dir"
# Merge into the existing settings, so values the skills saved themselves (such as the Slack
# self-DM and the recap check's mode) are kept.
python3 -I - "$CONFIG" "$skills_t" "$customers_t" "$jira_site" "$jira_project" "$history_drive_folder" "$sa_drive_folder" <<'PY'
import json, os, sys
path = sys.argv[1]
keys = ["skills_dir", "customers_dir", "jira_site", "jira_project", "history_drive_folder", "sa_drive_folder"]
try:
    with open(path) as f:
        cfg = json.load(f)
except (FileNotFoundError, ValueError):
    cfg = {}
for k, v in zip(keys, sys.argv[2:]):
    if v:
        cfg[k] = v
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(cfg, f, indent=2)
os.chmod(path, 0o600)
PY

# 5. Install the skills, filling in the folder paths and Jira settings.
for s in "${SKILLS[@]}"; do
  rm -rf "${skills_dir:?}/$s"
  cp -R "$SRC/$s" "$skills_dir/$s"
  find "$skills_dir/$s" -name __pycache__ -prune -exec rm -rf {} +
  python3 -I - "$skills_dir/$s" "$skills_t" "$customers_t" "$jira_site" "$jira_project" "$history_drive_folder" <<'PY'
import pathlib, sys
root, skills, customers, site, project, history = sys.argv[1:7]
values = {"{{SKILLS_DIR}}": skills, "{{CUSTOMERS_DIR}}": customers,
          "{{JIRA_SITE}}": site, "{{JIRA_PROJECT}}": project,
          "{{HISTORY_DRIVE_FOLDER}}": history}
for p in pathlib.Path(root).rglob("*"):
    if p.is_file() and p.suffix in (".md", ".py"):
        t = p.read_text()
        u = t
        for k, v in values.items():
            u = u.replace(k, v)
        if u != t:
            p.write_text(u)
PY
  echo "✓ Installed $s"
done

# 6. Python libraries for the Google Drive helper.
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --disable-pip-version-check google-api-python-client google-auth-oauthlib
echo "✓ Drive helper libraries ready"

# 7. What's still needed (sign-ins are yours to do).
echo
echo "Status:"
if command -v acli >/dev/null 2>&1; then
  if acli jira auth status >/dev/null 2>&1; then echo "  ✓ Jira: acli is signed in"
  else echo "  ✗ Jira: acli isn't signed in. See ACCESS-AND-SETUP.md, Part A (API token)"; fi
else
  echo "  ✗ Jira: acli isn't installed. See ACCESS-AND-SETUP.md, Part A"
fi
if [ -f "$CONFIG_DIR/google/token.json" ]; then echo "  ✓ Google Drive: signed in"
elif [ -f "$CONFIG_DIR/google/client_secret.json" ]; then echo "  ✗ Google Drive: client saved, not signed in yet. See ACCESS-AND-SETUP.md, step B6"
else echo "  ✗ Google Drive: not set up. See ACCESS-AND-SETUP.md, Part B"; fi
echo
echo "Next: open a Claude Code session in $customers_t/<customer>, then ask it to recap a call"
echo "or prep for a session. The skill creates the customer's folder if it doesn't exist yet."
echo "For automatic recaps, ask Claude to \"set up the recap check\" (see README.md)."
