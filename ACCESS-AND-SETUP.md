# SA customer skills: access and setup

Claude Code skills for LaunchDarkly Solutions Architects:

- **`customer-meeting-recap`** turns a customer call (Gong link or transcript) into a recap
  Google Doc in the customer's Drive folder, and creates your follow-up Jira tasks under the
  customer's epic in your Jira project.
- **`customer-session-prep`** writes a one-page prep brief for your next session as a Google Doc
  in the same folder, from that folder's recaps: status, what you owe the customer, open
  questions, support tickets and tech stack.
- **`customer-engagement-prep`** writes the same brief plus the engagement's history, for a new
  engagement or an account you're picking up.

Everything they produce goes to Google Drive. Nothing is saved on your Mac except a small
`CLAUDE.md` per customer with the links.

Tested on 2026-10-20 (macOS, Claude Code in the Claude desktop app's Code tab).

## How access works

You set up **two credentials, one for each system**. Both stay on your Mac, Claude never reads
either one, and both are used only through a command-line tool.

| | Jira | Google Drive |
|---|---|---|
| **What you create** | An **API token** (one long string) | An **OAuth client**: a Client ID + Client secret from your own Google Cloud project |
| **Where you create it** | id.atlassian.com → Security | console.cloud.google.com (a project in your company's organization) |
| **How it's used** | `acli` sends the token, with your email, on every request | The client lets you **sign in once in the browser**. That sign-in creates a token the helper uses after that |
| **Files on your Mac** | `~/.config/acli/token.txt`, plus `acli`'s own saved sign-in | `~/.config/sa-skills/google/client_secret.json` and `token.json` |
| **What it can reach** | Everything your Jira account can | **Only Docs the helper created itself** (Google's `drive.file` permission), in folders you can edit |
| **Expires** | On the date you pick (max about 1 year) | The sign-in token renews itself. Rerun `login` if Google revokes it |

## What works and what's blocked

| Access | Status | Notes |
|---|---|---|
| **Glean** connector | ✅ Works | Read-only. Reads Gong transcripts, Salesforce, Jira, Google Drive and Slack, limited to what you can see. **Can't create tickets or Docs.** |
| **Jira through `acli` + API token** | ✅ Works | Creates epics and tickets with epic link, due date, assignee and formatted description |
| **Google Drive through your own OAuth client** | ✅ Works | Creates and updates Google Docs in the customer folder and reads them back. |
| Jira through `acli` browser sign-in (`--web`) | ❌ Blocked | Approving in the browser still returns `access_denied` ("User did not authorize the request"), most likely an admin policy on OAuth apps |
| Atlassian Rovo MCP connector | ❌ Blocked | Couldn't be connected. Probably the same admin policy |
| Google Drive connector for Claude | ❌ Not enabled | Not available to Claude at the time of writing. Ask IT if that has changed |
| Gong / Salesforce connectors | ➖ Not available | Use Glean instead |
| **Gmail through Glean** | ✅ Works | Glean reaches your Gmail live. The recap check uses it only to find Gong's "call recording and analysis is ready" emails, about two hours before Glean's Gong search finds the call |
| **Slack** connector, posting by file share | ✅ Works | The recap check posts to your self-DM by sharing a small file with a message, and reads your replies. Only the file-upload tools can post |
| **Slack** connector, reading a customer's channels | ✅ Works | The recap reads only the channels and chats you listed for that customer, for context since the last call |
| Slack connector, plain send-message tool | ❌ Not offered | Not among the connector's tools at the time of writing; ask the admin who manages Claude connectors. The recap check would switch to it |
| Gong webhooks | ➖ Not needed | Need a Gong admin and a public endpoint. The recap check reads Gong's emails instead |
| API keys in `.env` for **Claude Desktop chat** | ❌ Won't work | Desktop chats run in a cloud sandbox and can't see your Mac's files or CLIs. That's why these skills run in Claude Code |

## Setup (about 25 minutes)

Run every command in **your own terminal** (the Terminal panel in the Code tab or the Terminal
app), not in the chat box.

### Part 0: Run the installer (about 2 minutes)

Clone this repo anywhere you like. Before the first install, set your **Jira project key**: the
project where your customer tasks go (the letters in ticket keys like `ABC-123`). Use your own
project, so your tickets don't land in someone else's. The installer never asks for it:

```bash
cd path/to/ai-sa-skills && python3 claude-code/customer-recap-check/scripts/recap_check.py config set jira_project ABC
```

Then run the installer from the same folder:

```bash
./install.sh
```

Each question suggests a value: press Enter (or type `y`) to keep it.

1. **Where to install the skills.** Enter for `~/.claude/skills` (recommended), so they work in
   every Claude Code session, or `2` for one project's `.claude/skills` folder.
2. **Your customer folders.** It suggests `~/work/customers`; type another path (starting with
   `~/` or `/`) to change it, e.g. `~/clients`. Each customer gets one folder there, holding just
   a `CLAUDE.md` of links.
3. **Your Jira site**, e.g. `yourcompany.atlassian.net`. If `acli` is already signed in, it asks
   you to confirm that site.
4. **Optional: your team's base Drive folder** for customer projects. Paste its link, or type
   `pass`.
5. **Your own Drive folder for the Active Customers Doc.** Paste its link, or type `pass`.

It then shows "Please confirm your selections"; Enter installs, `n` stops.

It then fills your answers into the skills, installs them, and installs the Drive helper's
Python libraries. Your answers are saved in `~/.config/sa-skills/config.json` and offered as
defaults next time. At the end it shows which sign-ins are still needed (Parts A and B). You can
run it before signing in to Jira; then run it again afterwards so the site is filled in for you.
Rerun it any time: to change an answer, or after `git pull` brings newer skills.

The commands below assume the recommended `~/.claude/skills`. If you chose a project folder,
use `<project>/.claude/skills` in their place.

### Part A: Jira (about 10 minutes)

**A1. Install the Atlassian CLI.** Trusting a Homebrew tap is a security setting, so do it yourself.

```bash
brew tap atlassian/homebrew-acli
```

```bash
brew trust atlassian/acli
```

```bash
brew install acli
```

`brew install` fails with "Refusing to load formula … from untrusted tap" until the trust
step has worked. `brew trust --json=v1` should list `atlassian/acli` under `"taps"`.

**A2. Create a Jira API token.** It's in your Atlassian account settings, not Jira's Personal settings.

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens (or in Jira, click your
   profile picture → **Manage account** → **Security** → **Create and manage API tokens**).
2. Click **Create API token**, the plain one, not "with scopes".
3. Name it (e.g. `acli-claude-code`), pick an expiry date, click **Create**, then click **Copy**.
   It's shown only once.

**A3. Save the token to a private file.** Run this right after clicking Copy, before you copy anything else:

```bash
mkdir -p ~/.config/acli && pbpaste > ~/.config/acli/token.txt && chmod 600 ~/.config/acli/token.txt
```

Check the size without printing it. It should be about 190 bytes; a small number like 23
means the clipboard held something else.

```bash
wc -c < ~/.config/acli/token.txt
```

**A4. Sign in** (use your own email):

```bash
acli jira auth login --site yourcompany.atlassian.net --email you@yourcompany.com --token < ~/.config/acli/token.txt
```

You should see `✓ Authentication successful`. To check later, run `acli jira auth status`.

### Part B: Google Drive (about 15 minutes)

**B1. Create a Google Cloud project:** go to https://console.cloud.google.com/projectcreate

- **Name:** e.g. `ai-sa-skills-<yourname>`.
- **Organization / Location:** must be **your company's Google Workspace organization**, not "No organization".
- After it's created, select it in the project picker at the top.

**B2. Enable the Drive API:** go to https://console.cloud.google.com/apis/library/drive.googleapis.com.
Check that the top bar shows your project, then click **Enable**.

**B3. Set up the consent screen:** go to https://console.cloud.google.com/auth/overview and click **Get started**.

- **App name:** `SA skills`; use your email for support and contact.
- **Audience:** **Internal**. That skips Google's app review and the "unverified app" warning.

**B4. Create the OAuth client:** go to https://console.cloud.google.com/auth/clients and click **Create client**.

- **Application type:** **Desktop app**. Name it anything, then click **Create**.
- The dialog shows the **Client ID** (ends in `.apps.googleusercontent.com`) and the
  **Client secret** (starts with `GOCSPX-`, about 35 characters). Keep it open for B5.
- If you lose the secret: open the client, click **Add secret** under "Client secrets", and copy
  the new one right away. Newer consoles show a secret only once.

**B5. Save your OAuth client.** (The installer already set up the helper's Python libraries.) This asks for the Client ID, then the secret. The secret stays
hidden while you paste. No download or Downloads folder is involved.

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore ~/.claude/skills/customer-meeting-recap/scripts/gdrive.py setup-client
```

It should print `{"saved": ".../client_secret.json"}`. (If you'd rather use Google's
**Download JSON** button, save that file as `~/.config/sa-skills/google/client_secret.json`
and `chmod 600` it.)

To check the secret without showing it, run this. A good one prints `GOCSPX- 35`:


```bash
python3 -c 'import json,os; s=json.load(open(os.path.expanduser("~/.config/sa-skills/google/client_secret.json")))["installed"]["client_secret"]; print(s[:7], len(s))'
```

**B6. Sign in to Google:**

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore ~/.claude/skills/customer-meeting-recap/scripts/gdrive.py login
```

A browser opens. Choose your work Google account and click **Allow** for "See, edit, create
and delete only the specific Google Drive files you use with this app". The terminal should
print `{"signed_in_as": "you@yourcompany.com"}`.

### Part C: Customers

The installer already put the skills in place; Claude Code picks them up automatically.

**C1. Add a customer.** Easiest: just run a skill with the customer's links in your prompt
(Salesforce opportunity and/or Drive folder). If there's no `<customer folders>/<customer>/`
folder yet (the location you chose in Part 0), the skill creates it with a `CLAUDE.md`. Before
saving the recap, it asks once, in one message, for every link that isn't in your prompt or the
Drive folder, and saves your answers there. That includes the customer's **Slack channels and
chats** (shared channel, internal account channel, group DMs): send each one's link (right-click
→ Copy link), or say "none". The skills never search for channels themselves, read only the
ones you list, and never name them in a Doc or ticket.

`CLAUDE.md` keeps one entry per **opportunity**, named like `RSA50 opportunity (1)`,
`RSA100 opportunity`, `RSA50 opportunity (2)`, each with its own Salesforce, Drive folder,
Vitalstatistix and session plan links. The template is in
`claude-code/customer-meeting-recap/references/customer-folder-template.md`.

**New opportunity for an existing customer:** give the skill the new Salesforce opportunity
link, or say it's a new opportunity. It adds a new entry and asks you, link by link, whether to
reuse an existing opportunity's link (for example, the same Drive folder) or use a new one. It
never copies links between opportunities on its own, and it doesn't take links from a Glean
search without your OK, because a search can return another opportunity's link.

The Jira epic is one per customer (named after the customer, in Title Case); the recap skill
finds or creates it.

You need **edit access to the customer's Drive folder**. If saving fails with "can't add files
to it", ask the folder's owner to make you an editor.

**C2. Use them.** In the Code tab, start a session in the customer's folder, then:

- **After a call:** "Recap this call: <Gong link>" (or paste the transcript).
- **Before a call:** "Prep me for the next <customer> session."

### Part D: Automatic recaps (optional, about 10 minutes)

`customer-recap-check` recaps your customer calls on a schedule, with no prompt. It needs no new
credential: it uses the Jira and Drive sign-ins from Parts A and B, plus two Claude connectors.

It starts from Gong's **"call recording and analysis is ready"** email, which Gong sends to each
participant about two hours before Glean's Gong search finds the call. Keep those emails on in
Gong (they are by default), and don't filter them out of your inbox. The check reads only those
emails, and only the call link, account, date and duration from each. The recap is always
written from the call's full transcript, so a call waits until Glean has it.

**D1. Check the connectors.** In claude.ai, **Settings → Connectors**, make sure these are
connected and enabled for Claude Code:

| Connector | Tools the check uses |
|---|---|
| **Glean** | Search and read document: Gong's emails in your Gmail, the call's transcript, the customer's Drive folder |
| **Slack** | Read channel and read thread (your self-DM, and the customer channels you listed), and the two file-upload tools (get file upload URL, complete file upload), which is how it posts to your self-DM |

**D2. Have a Drive folder of your own** for the Active Customers Doc, which every customer skill
reads. You need edit access to it. Give it to `install.sh` (its last question): once you're signed in to
Google Drive, the installer creates the Doc there and prints its link. Otherwise setting up the
check creates it.

**D3. Set it up.** In any Claude Code session, say **"set up the recap check"**. It:

1. Saves your Drive folder and creates the **Active Customers** Doc there, if the installer
   hasn't already. Add one row per
   customer, with its Documentation name, Drive folder link, Slack channels, Gong account and
   Status Active. Every customer skill works only on Active rows (see the README).
2. Finds your Slack self-DM from your Slack user ID and saves it. Nothing to look up yourself.
3. Asks which hours to run, then creates an hourly scheduled task in the desktop app.
4. Starts in **dry-run mode**: for a while it only reports what it would do.

**D4. Approve its tools once.** On the first runs, approve the tools it uses when asked
(Glean, Slack, and Bash for the helper scripts and `acli`), so later runs don't stop
for permission. Turn on Claude notifications on your Mac and phone, so you're pinged when a
recap is ready or a question waits for you.

**D5. Go live** when the dry runs look right: say **"switch the recap check to live"**.

**When links are missing,** it asks you once in your self-DM for all of them; reply in the
thread. Only a missing Drive folder holds the recap: with nowhere to save it, the call waits,
with a reminder at most once a day. Other missing links don't: the recap and tickets are made
with `Not found` for them, and when you reply, the links are saved for next time and filled in
on the recap Doc. If the opportunity was missing, the meeting is then added to the Master
Engagement Doc too.

The desktop app must be open and your Mac awake at check time; a missed check runs at the next
one. Everything the check produces goes to Google Drive, Jira and your Slack self-DM; on your
Mac it keeps only `~/.config/sa-skills/processed-calls.json` (Gong call IDs and outcomes) and its
run log, `~/.config/sa-skills/recap-check-log.md`.

## Rules for tokens and secrets

- Never paste a token or client secret into a Claude chat, and never ask Claude to read
  `~/.config/acli/token.txt` or anything in `~/.config/sa-skills/google/`. The skills pass
  them only to `acli` and the Drive helper; they never open them.
- Keep all of these files at `chmod 600`, outside any git repo, and don't share them. Each
  person creates their own; a token is what identifies *you*.
- **Jira token expired** (`acli` says `unauthorized`): repeat A2–A4 and delete the old token.
- **Drive says "not signed in"**: rerun B6. If it says the client secret is invalid, add a new
  secret (B4), then redo B5 and B6.
- **Blocked at A2 or B1** (no "Create API token" button, or no permission to create projects):
  ask your IT team.

## Things we learned the hard way

- **The client secret is easy to paste wrong.** "`invalid_client: The provided client secret is
  invalid`" after approving in the browser means the saved secret doesn't match. Use the check
  in B5.
- **"Download JSON" may not download anything.** In our test no file was saved, which led to
  several rounds of `mv: No such file or directory`. `setup-client` avoids the download entirely.
- **`~/.config` is hidden in Finder.** Press ⌘ + Shift + . to show hidden folders, or just check
  from the terminal.
- **`acli jira auth login --web` needs keyboard focus** in the terminal at the site picker. At
  LaunchDarkly it's blocked anyway; use the API token.
- **`acli`'s `--site` only works with `--email` and `--token`,** not with `--web`.
- **Jira search can't return `duedate`.** Use `acli jira workitem view <KEY> --fields duedate`.
- **`acli` can't change a ticket's parent epic after creation.** Fix it in the Jira UI, or
  create the ticket again.
- **Epic link and due date on creation:** use `acli jira workitem create --from-json` with
  `"parentIssueId"` and `"additionalAttributes": {"duedate": "YYYY-MM-DD"}`. The description must
  be Atlassian Document Format; `scripts/jira_ticket.py` converts Markdown for you.
- **The Drive helper only sees its own Docs.** That's the `drive.file` permission working as
  intended. Use Glean to read other files in the folder.
- **Python warnings** about Python 3.9 being end-of-life are harmless; `-W ignore` hides them.
- **In zsh, don't store a command in a variable** (`G="python script.py"; $G list`). zsh doesn't
  split it into words, and you get "no such file or directory".

## What's in this repo

```
ai-sa-skills/
├── README.md                    ← short overview
├── ACCESS-AND-SETUP.md          ← this guide
├── install.sh                   ← asks where things go, then installs (Part 0)
└── claude-code/                 ← the skills' master copy, with placeholders
    ├── customer-meeting-recap/  (SKILL.md, scripts/jira_ticket.py, scripts/gdrive.py, scripts/gong_transcript.py, references/)
    ├── customer-session-prep/   (SKILL.md)
    ├── customer-engagement-prep/ (SKILL.md)
    └── customer-recap-check/    (SKILL.md, scripts/recap_check.py), see Part D
```

**To change the skills,** edit the master copy in `claude-code/`, not the installed copy, then
rerun `./install.sh` to install your changes. The master copy uses `{{SKILLS_DIR}}`,
`{{CUSTOMERS_DIR}}`, `{{JIRA_SITE}}` and `{{JIRA_PROJECT}}` wherever a personal setting goes;
keep those as they are.

**Never commit personal or customer data.** This repo must contain no customer names, no
customer or internal links, no account IDs, and no tokens or secrets. Use made-up examples
(`Acme`, `Alex`, `KEY-123`) in skills and docs. Personal settings and credentials live in each
person's `~/.config/`, and customer details in their own customer folders, outside the repo.

These skills run in Claude Code: the desktop app's **Code tab** or a terminal. They don't work in
the desktop app's **Chat tab** (Projects), which runs in the cloud and can't use `acli` or the
Drive helper.
