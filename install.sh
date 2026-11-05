#!/usr/bin/env bash
# Install the SA customer skills for Claude Code.
#
# Asks where the skills and your customer folders should live and which Jira site to use,
# fills those into the skills, installs them, and sets up the Drive helper's Python libraries. Safe to run again:
# it remembers your answers (in ~/.config/sa-skills/config.json) and offers them as defaults.
# Your Jira project key is set once by hand before the first install (see README.md, Install).
#
# It never asks for, reads or prints a token or secret. Signing in to Jira and Google is
# done separately; see README.md, "Sign in to Jira" and "Sign in to Google Drive".

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/claude-code"
CONFIG_DIR="$HOME/.config/sa-skills"
CONFIG="$CONFIG_DIR/config.json"
VENV="$HOME/.local/share/sa-skills/venv"
SKILLS=(customer-meeting-recap customer-session-prep customer-engagement-prep customer-recap-check customer-shared-notes)

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
echo "(Each customer gets one small folder there with a CLAUDE.md of links; recaps and briefs are saved to Google Drive, not here)"
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
prev_site="${prev_site:-launchdarkly.atlassian.net}"
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

# 3b. The team's shared base Drive folder for customer projects (required).
prev_history="$(saved history_drive_folder)"
case "$prev_history" in https://drive.google.com/*) ;; *) prev_history="" ;; esac
echo
echo "Your team's shared base Google Drive folder for customer projects. Everyone on the team"
echo "uses the same one; ask your manager for the link if you don't have it. The skills search"
echo "it for earlier engagements with a customer, so it's required."
if [ -n "$prev_history" ]; then
  echo "  Saved folder: $prev_history"
  prompt="Press Enter to keep the saved folder, or paste the team folder link: "
else
  prompt="Paste the team folder link: "
fi
while :; do
  read -r -p "$prompt" history
  case "$history" in
    ""|y|Y|yes|YES|Yes) [ -n "$prev_history" ] && { history="$prev_history"; break; } ;;
    https://drive.google.com/*/folders/*) history="${history%%\?*}"; break ;;
  esac
  echo "  Paste the Google Drive folder link (https://drive.google.com/drive/folders/...)."
done
history_drive_folder="$history"

# 3c. Your own Drive folder for the Active Customers Doc, which every customer skill reads.
prev_sa_folder="$(saved sa_drive_folder)"
printf '%s' "$prev_sa_folder" | grep -Eq '^[A-Za-z0-9_-]{10,}$' || prev_sa_folder=""  # ignore a bad saved answer
echo
echo "Your own Google Drive folder. I'll create your Active Customers Doc there: the list of"
echo "customers the skills work on, with their links."
if [ -n "$prev_sa_folder" ]; then
  echo "  Saved folder: https://drive.google.com/drive/folders/$prev_sa_folder"
  prompt="Press Enter to keep the saved folder, paste another folder link, or type pass to skip for now: "
else
  prompt="Paste your folder link, or type pass to skip for now (ask Claude to set up the recap check later): "
fi
while :; do
  read -r -p "$prompt" sa_folder
  case "$sa_folder" in
    ""|y|Y|yes|YES|Yes) [ -n "$prev_sa_folder" ] || { echo "  Paste a folder link, or type pass."; continue; }
      sa_folder="$prev_sa_folder"; break ;;
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
  else echo "  ✗ Jira: acli isn't signed in. See README.md, 'Sign in to Jira'"; fi
else
  echo "  ✗ Jira: acli isn't installed. See README.md, 'Sign in to Jira'"
fi
if [ -f "$CONFIG_DIR/google/token.json" ]; then echo "  ✓ Google Drive: signed in"
elif [ -f "$CONFIG_DIR/google/client_secret.json" ]; then echo "  ✗ Google Drive: client saved, not signed in yet. See README.md, 'Sign in to Google Drive', step 6"
else echo "  ✗ Google Drive: not set up. See README.md, 'Sign in to Google Drive'"; fi
echo
echo "Next steps:"
echo "  1. Go to your Active Customers Doc and update it with your customers. This lets you use"
echo "     the skills and the automatic recaps.${doc:+ $doc}"
echo "  2. Open a Claude Code session and call the skills 🙂"

# 8. The automated workflows. A shell script can't create a scheduled task: only a session in
# the Claude desktop app can, with its scheduled-tasks tool (and the setup needs the app's Slack
# and Glean sign-ins). So this only gets you there: it copies the setup prompt and opens the app.
# The task runs, for good, in the folder of the session that creates it (this clone), and in
# that session's permission mode. It must be Auto, so the hourly runs never stop to ask; two allow
# rules let Auto mode delete and create the task, which its automatic check blocks otherwise.
here_t="$(tilde "$HERE")"
local_settings="$HERE/.claude/settings.local.json"
task_rules=(mcp__scheduled-tasks__delete_scheduled_task mcp__scheduled-tasks__create_scheduled_task)
setup_prompt="Set up the recap check (the customer-recap-check skill) from this folder. If a scheduled task named customer-recap-check already exists, delete it and create it again from here, with the same schedule. Keep the settings I already have (mode, Drive folder, Slack self-DM). Don't run the check yourself."
echo
read -r -p "Turn on the automated workflows (the hourly recap check)? Type y for yes, Enter to skip: " auto
case "$(printf '%s' "${auto:-n}" | tr '[:upper:]' '[:lower:]')" in
  y|yes)
    case "$HERE" in
      */.claude/worktrees/*)
        echo "  ✗ This copy is a temporary worktree ($here_t). Run ./install.sh from your main"
        echo "    ai-sa-skills clone and answer y there: the task must not run from a folder that goes away." ;;
      *)
        echo "  The setup session runs in Auto mode, which blocks creating a scheduled task unless you allow it."
        echo "  These two Claude Code permission rules allow it, only in sessions in this clone:"
        for r in "${task_rules[@]}"; do echo "    $r"; done
        echo "  They go in $(tilde "$local_settings") (on this Mac only, never committed)."
        read -r -p "  Add them? Press Enter or type y to add, n to skip: " add_rules

        if keep "$add_rules"; then
          mkdir -p "$HERE/.claude"
          if python3 -I - "$local_settings" "${task_rules[@]}" <<'PY'
import json, os, sys
path, rules = sys.argv[1], sys.argv[2:]
d = {}
if os.path.exists(path):
    with open(path) as f:
        d = json.load(f)
allow = d.setdefault("permissions", {}).setdefault("allow", [])
allow.extend(r for r in rules if r not in allow)
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(d, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
PY
          then echo "  ✓ Added the two rules"
          else echo "  ✗ Couldn't update $(tilde "$local_settings") (is it valid JSON?). Add the two rules by hand"; fi
        else
          echo "  Skipped. Without them, Auto mode may block the setup session from creating the task."
        fi
        # Copy the prompt, and say so only if the clipboard really holds it (a terminal inside an
        # app or over SSH can accept pbcopy without reaching the Mac's clipboard).
        copied=""; opened=""
        if command -v pbcopy >/dev/null 2>&1 && command -v pbpaste >/dev/null 2>&1 \
          && printf '%s' "$setup_prompt" | pbcopy 2>/dev/null \
          && [ "$(pbpaste 2>/dev/null)" = "$setup_prompt" ]; then copied=1; fi
        if command -v open >/dev/null 2>&1 && open -a Claude >/dev/null 2>&1; then opened=1; fi
        echo
        echo "  Last step, in the Claude desktop app${opened:+ (now open)}:"
        echo "  1. Start a brand-new Code session, now that the installer is done: a session reads"
        echo "     the two rules only when it starts. Don't reuse a session that was already open."
        echo "  2. Its folder, with the worktree OFF: $here_t"
        echo "     The task runs from this folder for good; a worktree is a temporary copy that gets"
        echo "     cleaned up."
        echo "  3. Its permission mode: Auto (the mode picker by the message box). The rules only let"
        echo "     this session create the task. The task keeps this session's mode, and the hourly runs"
        echo "     use Slack, Glean, Drive, Jira and Bash: in Auto they never stop to ask you."
        if [ -n "$copied" ]; then echo "  4. Paste the setup prompt (it's on your clipboard) and send it. Here it is too:"
        else echo "  4. Copy this setup prompt and send it:"; fi
        echo
        echo "     $setup_prompt"
        echo
        echo "  5. Answer its questions (which hours to run). It tells you when the task is created."
        if [ "$(saved recap_check_mode)" = "live" ]; then echo "  Your recap check stays live."
        else echo "  It starts in dry-run mode. When its reports look right, say \"switch the recap check to live\"."; fi ;;
    esac ;;
  *)
    echo "  Skipped. To turn them on later, rerun ./install.sh and answer y." ;;
esac
