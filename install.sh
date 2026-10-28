#!/usr/bin/env bash
# Install the SA customer skills for Claude Code.
#
# Asks where the skills and your customer folders should live and which Jira site to use,
# fills those into the skills, installs them, and sets up the Drive helper's Python libraries. Safe to run again:
# it remembers your answers (in ~/.config/sa-skills/config.json) and offers them as defaults.
# Your Jira project key is set once by hand before the first install (see README.md, Install).
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
# Enter, "y" or "yes" keeps the suggested value.
keep() { case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in ""|y|yes) return 0 ;; *) return 1 ;; esac; }
saved() { [ -f "$CONFIG" ] && python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2],""))' "$CONFIG" "$1" || true; }

[ -d "$SRC" ] || { echo "Can't find $SRC. Run this script from inside the ai-sa-skills folder."; exit 1; }

# Your Jira project key is set by hand before the first install, never asked here.
jira_project="$(saved jira_project)"
if ! printf '%s' "$jira_project" | grep -Eq '^[A-Z][A-Z0-9_]{1,9}$'; then
  echo "Before running this installer, please set your Jira project key first by running this"
  echo "command in bash (replace ABC with your project's key):"
  echo "  python3 claude-code/customer-recap-check/scripts/recap_check.py config set jira_project ABC"
  echo "The project key is not a secret or an API key. It's the project's short name, the letters"
  echo "before the dash in your ticket keys (ABC in ABC-123). Your API token in"
  echo "~/.config/acli/token.txt is separate, and this installer doesn't read it."
  echo "See README.md, Install, step 2. Nothing changed."
  exit 1
fi

echo "SA customer skills installer"
echo

# 1. Where the skills go.
prev_skills="$(saved skills_dir)"
echo "Where should the skills be installed?"
echo "  1) ~/.claude/skills: available in every Claude Code session (recommended)"
echo "  2) One project only: <project>/.claude/skills"
[ -n "$prev_skills" ] && echo "  (last time: $prev_skills)"
read -r -p "Type 1 or 2, or press Enter for 1: " choice
if [ "${choice:-1}" = "2" ]; then
  read -r -p "Project folder (e.g. ~/work/sa-project): " project
  [ -n "$project" ] || { echo "No folder given; stopping."; exit 1; }
  skills_dir="$(expand "$project")/.claude/skills"
else
  skills_dir="$HOME/.claude/skills"
fi

# 2. Where the customer folders go.
prev_customers="$(saved customers_dir)"
case "$prev_customers" in "~"*|/*) ;; *) prev_customers="" ;; esac  # ignore a bad saved answer
default_customers="${prev_customers:-~/work/customers}"
echo
echo "What is the local path you want your customer CLAUDE.md files saved in?"
echo "Each customer gets one small folder there with a CLAUDE.md of links; recaps and briefs"
echo "are saved to Google Drive, not here."
while :; do
  read -r -p "Press Enter to keep $default_customers, or type another folder (e.g. ~/customers): " customers
  if keep "$customers"; then customers="$default_customers"; break; fi
  case "$customers" in "~"*|/*) break ;; esac
  echo "  That isn't a folder path: start it with ~/ or /."
done
customers_dir="$(expand "$customers")"

# 3. Your Jira site and project (where the recap skill files your tickets).
prev_site="$(saved jira_site)"
if [ -z "$prev_site" ] && command -v acli >/dev/null 2>&1; then
  # acli exits non-zero when it isn't signed in yet; that must not stop the installer.
  prev_site="$( (acli jira auth status 2>/dev/null || true) | sed -n 's/^ *Site: *//p' | head -1)"
fi
case "$prev_site" in *.*) ;; *) prev_site="" ;; esac
echo
while :; do
  if [ -n "$prev_site" ]; then
    echo "Confirm your Jira site is $prev_site."
    read -r -p "Press Enter to confirm, or type another site (e.g. yourcompany.atlassian.net): " site
    if keep "$site"; then site="$prev_site"; fi
  else
    read -r -p "Type your Jira site (e.g. yourcompany.atlassian.net): " site
  fi
  site="${site#https://}"; site="${site%%/*}"
  case "$site" in *.*) break ;; esac
  echo "  That isn't a Jira site: it looks like yourcompany.atlassian.net."
  prev_site=""
done
jira_site="$site"

# 3b. Optional: the team's base Drive folder for customer projects (for engagement history).
prev_history="$(saved history_drive_folder)"
case "$prev_history" in https://*|none) ;; *) prev_history="" ;; esac
echo
echo "Optional: your team's base Google Drive folder for customer projects. The prep skill"
echo "searches it (through Glean) for earlier engagements with a customer."
[ -n "$prev_history" ] && [ "$prev_history" != none ] && echo "  (now: $prev_history)"
while :; do
  read -r -p "Paste the folder link, press Enter to keep what's there, or type pass to skip: " history
  case "$history" in
    ""|y|Y|yes|YES|Yes) history="${prev_history:-none}"; break ;;
    pass|PASS|Pass) history=none; break ;;
    https://drive.google.com/*) history="${history%%\?*}"; break ;;
  esac
  echo "  Paste a Google Drive folder link (https://drive.google.com/drive/folders/...), or type pass."
done
history_drive_folder="$history"

# 3c. Your own Drive folder for the Active Customers Doc, which every customer skill reads.
prev_sa_folder="$(saved sa_drive_folder)"
echo
echo "I'll create your Active Customers Doc (the customers the skills work on, with their links)"
echo "in your own Google Drive folder. You can also do this later by asking Claude to set up the"
echo "recap check."
[ -n "$prev_sa_folder" ] && echo "  (now: folder $prev_sa_folder)"
while :; do
  read -r -p "Paste the folder link, press Enter to keep what's there, or type pass to skip: " sa_folder
  case "$sa_folder" in
    ""|y|Y|yes|YES|Yes) sa_folder="$prev_sa_folder"; break ;;
    pass|PASS|Pass) sa_folder=""; break ;;
    https://drive.google.com/*/folders/*)
      sa_folder="${sa_folder%%\?*}"; sa_folder="${sa_folder##*/folders/}"; sa_folder="${sa_folder%%/*}"; break ;;
  esac
  echo "  Paste a Google Drive folder link (https://drive.google.com/drive/folders/...), or type pass."
done
sa_drive_folder="$sa_folder"

skills_t="$(tilde "$skills_dir")"
customers_t="$(tilde "$customers_dir")"
echo
echo "Please confirm your selections:"
echo "Skills:           $skills_t"
echo "Customer folders: $customers_t"
echo "Jira:             project $jira_project on $jira_site"
echo "History folder:   $history_drive_folder"
echo "Your Drive folder: ${sa_drive_folder:-none (skipped)}"
echo "This replaces the installed copies of: ${SKILLS[*]}."
echo "Your customer folders, other skills, logs and Active Customers Doc are left as they are."
read -r -p "Install with these? Press Enter or type y to go ahead, n to stop: " ok
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
if [ -z "$sa_drive_folder" ]; then
  echo "  ✗ Active Customers Doc: no Drive folder given. Rerun ./install.sh with one"
elif [ -f "$CONFIG_DIR/google/token.json" ]; then
  doc="$("$VENV/bin/python" -W ignore "$skills_dir/customer-recap-check/scripts/recap_check.py" customers init --folder "$sa_drive_folder" 2>/dev/null \
    | "$VENV/bin/python" -I -c 'import json,sys; d=json.load(sys.stdin); f=d.get("created") or d.get("exists") or {}; print(("created " if d.get("created") else "") + f.get("webViewLink",""))' 2>/dev/null || true)"
  if [ -n "$doc" ]; then echo "  ✓ Active Customers Doc: $doc"
  else echo "  ✗ Active Customers Doc: couldn't create it. Check you can edit the Drive folder, then rerun ./install.sh"; fi
else
  echo "  ✗ Active Customers Doc: created when you rerun ./install.sh after signing in to Google Drive"
fi
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
