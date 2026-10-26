# ai-sa-skills

Two Claude Code skills that take the busywork out of running customer engagements as a
Solutions Architect (SA): writing up each call, filing the follow-up tasks, and getting ready
for the next session.

- **`customer-meeting-recap`**: after a call, turns the recording or transcript into a recap
  Google Doc in the customer's Drive folder, and creates a Jira ticket for every follow-up the
  LaunchDarkly team committed to.
- **`customer-session-prep`**: before a call, writes a one-page prep brief (a Google Doc in the
  same folder) so you know in two minutes what to deliver, what's still open, and what to ask.

## The problem these solve

After every customer call, the same manual work: rewatch the recording, write up what was
discussed and decided, list who promised what, open a ticket for each of your tasks, and file
it all in the right customer folder. Before the next call, you dig through old notes, tickets,
support cases and docs to remember where things stand.

Doing this with Claude sounds easy, but the Claude desktop app's **Chat tab** can't do it on its
own. It runs in the cloud, so it can't use tools on your computer, and it has no way to *write*
to Jira or Google Drive. A search connector like Glean can read Jira, Drive, Gong and Salesforce
but can't create tickets or documents. API keys in a local `.env` don't help either, because the
Chat tab can't see your files.

These skills run in **Claude Code** instead (the desktop app's **Code tab**, or a terminal), on
your own computer, where they can use:

| For | They use | Why |
|---|---|---|
| Reading call transcripts, Salesforce, Drive, Jira and Slack | **Glean** (Claude connector) | Already searches everything you have access to |
| Creating Jira epics and tickets | **Atlassian CLI (`acli`)** with your Jira **API token** | Writes to Jira without an OAuth app, which company admins often block |
| Saving and reading Google Docs | A small **Drive helper** (`gdrive.py`) with your own Google **OAuth client** | Writes real Google Docs into the customer's folder, and can only touch the Docs it created |

## What each skill produces

### `customer-meeting-recap`

You say something like *"Recap this call: \<Gong link\>"*, or paste a transcript.

1. **Reads the call.** From your paste, or the Gong recording through Glean.
2. **Reads what came before.** The previous recap in the customer's Drive folder, so it can mark
   earlier action items as done or still open.
3. **Writes the recap** and saves it as `<Customer> – Meeting Recap – <date>` in the Drive folder:
   - Summary and what was discussed, including decisions
   - Artifacts shared, plus relevant LaunchDarkly docs (only links it has confirmed exist)
   - Scheduled meetings, with dates
   - **Action items – LaunchDarkly team**, with owner, due date and Jira ticket
   - **Action items – \<Customer\>**, with owner and due date
   - Open questions (theirs and ours), and the status of the previous recap's action items
   - **Customer links**: opportunity, Salesforce, Drive folder, Vitalstatistix, Jira epic, team
4. **Finds or creates the customer's Jira epic** (named after the customer, in Title Case) in your
   own Jira project.
5. **Creates one ticket per LaunchDarkly team action item**, skipping any that already exist:
   - **Title:** `<Owner>: <short task>`, e.g. `Alex: Confirm Big Segments Need Persistent Store`.
     No customer name, since the epic already says that.
   - **Assignee:** you, if it's your task. Other people's tasks are left unassigned, so the name in
     the title tells you it's one you only need to follow up on.
   - **Description:** the ask, background, why it matters, a one-sentence definition of done,
     and the customer links.

### `customer-session-prep`

You say something like *"Prep me for the next Acme session"*. It reads the latest recaps, the
session plan, your tickets under the customer's epic, the customer's recent support tickets and
what's known about their tech stack, then saves a one-page brief as
`<Customer> – Session Prep – <date>`:

- Goal for the session and the latest status (from the newest recap, or the latest Gong call if
  it's newer)
- **For an existing customer** picked up from an earlier engagement: where that engagement left
  off. It shows each planned session from the old kickoff deck, checked against the Gong calls
  as happened, partly happened or never happened, plus promises still open.
- **Deliver in \<session name\> (\<date or date TBD\>):** finished tickets to show or explain, and
  open ones that are due
- The customer's open questions, each with a draft answer or a docs link
- Action items to follow up on, split into the customer's items and LD's internal items
- Support tickets, tech stack, and where the engagement stands in the session plan
- All the links in one place, each labelled with the customer's name

The brief always uses the customer's name and "LD" instead of "they" or "we", so it reads clearly
when you forward it.

## How it keeps track of each customer

Each customer gets a small local folder, e.g. `~/work/customers/acme/`, holding a single
`CLAUDE.md`. Claude Code reads it automatically when you open a session there. It's an address
book, not notes: the customer's Jira epic, team, latest call and tech stack, and a list of
**opportunities**, each with its own links:

```text
## Opportunities
### RSA50 opportunity (1)    ← Salesforce opportunity, Drive folder, Vitalstatistix, session plan
### RSA100 opportunity
### RSA50 opportunity (2)
```

- **The skills create and update this file for you** as they learn links, people and facts.
- **They never guess links.** Salesforce, Drive and Vitalstatistix links come only from your
  prompt, the opportunity's own Drive folder, or your answer. If one is missing, the skill asks
  you for all the missing ones in one message.
- **New opportunity?** Give the skill the new Salesforce link (or say it's a new opportunity). It
  adds a new entry and asks, link by link, whether to reuse an existing opportunity's link or use
  a new one.

Everything the skills *produce* (recaps, briefs, transcripts) goes to Google Drive. Nothing but
this `CLAUDE.md` is kept on your computer.

## What you need

- **Claude Code**, with the **Glean** connector enabled.
- **macOS** with Homebrew and Python 3 (tested on macOS; Linux should work with small changes).
- **A Jira project of your own** for customer tasks, plus a **Jira API token**.
- **Edit access to each customer's Google Drive folder**, plus a **Google OAuth client** you
  create in your company's Google Cloud organization.

### About the credentials

You create **two credentials, once**. Neither is an API key you paste anywhere: both stay in
private files on your computer, and Claude never reads them.

| | Jira | Google Drive |
|---|---|---|
| What it is | An **API token** from your Atlassian account | An **OAuth client** (Client ID + secret) from your own Google Cloud project |
| How it's used | `acli` signs in with it once, using your email | You sign in once in the browser; that creates a token the helper reuses |
| Where it's kept | `~/.config/acli/token.txt` | `~/.config/sa-skills/google/` |
| What it can reach | What your Jira account can | **Only the Docs the helper created** (Google's `drive.file` permission) |
| Expires | On the date you choose (up to about a year) | Renews itself |

Why not simpler options? At many companies the Atlassian MCP connector and `acli`'s browser
sign-in are blocked by admin policy, and Claude has no Google Drive connector with write access.
The API token and your own OAuth client are what work. [ACCESS-AND-SETUP.md](ACCESS-AND-SETUP.md)
has the full details, including what we found blocked.

## Install

```bash
git clone <this repo's URL>
```

```bash
cd ai-sa-skills && ./install.sh
```

`install.sh` asks four questions and one optional one, then fills your answers into the skills and installs them:

| # | Question | Example answer | Why it's asked |
|---|---|---|---|
| 1 | Where should the skills be installed? | `1` for `~/.claude/skills` (every session), or `2` for one project's `.claude/skills` | Claude Code loads skills from these folders |
| 2 | Where should your customer folders live? | `~/work/customers` (default) | Where each customer's `CLAUDE.md` goes |
| 3 | Your Jira site | `yourcompany.atlassian.net` (offered automatically once `acli` is signed in) | For ticket links |
| 4 | Your Jira project key | `ABC` | Your tickets go to *your* project, not someone else's |
| 5 | Optional: your team's base Google Drive folder for customer projects | `https://drive.google.com/drive/folders/<id>`, or Enter to skip | The prep skill searches it for earlier engagements with an existing customer. If you skip it, the skill asks for folders when it needs them |

It also installs the Drive helper's Python libraries, then shows which sign-ins are still needed.
Your answers are saved in `~/.config/sa-skills/config.json` and offered as defaults next time.
It never asks for, reads or prints a token or secret.

**Then sign in, once (about 25 minutes):** follow Parts A and B of
[ACCESS-AND-SETUP.md](ACCESS-AND-SETUP.md):

- **Part A, Jira:** install `acli`, create an API token, save it to a private file, sign in.
- **Part B, Google Drive:** create a Google Cloud project and OAuth client, save it with the
  helper's `setup-client` command (the secret stays hidden as you paste), sign in in the browser.

Run `./install.sh` again afterwards: it fills in your Jira site for you and shows that both
sign-ins are done.

## How to use it best

### 1. Work in Claude Code, one project per customer

Use **Claude Code**: the Claude desktop app's **Code tab**, or `claude` in a terminal. Not the
Chat tab, where the skills can't reach Jira or Drive.

Give each customer **its own project**: a folder named after the customer inside your customers
folder, e.g. `~/work/customers/acme`. Always start that customer's sessions there:

- **Desktop app:** in the Code tab, start a new session and choose the customer's folder.
- **Terminal:** `cd ~/work/customers/acme && claude`.

Working from the customer's folder is what makes it effortless: Claude Code loads that folder's
`CLAUDE.md` automatically, so every session already knows the customer, its opportunities, Drive
folders, Jira epic and team, and you don't repeat links.

For a **new customer**, create the folder (`mkdir ~/work/customers/acme`) and open a session there,
or run the first skill from your customers folder and it creates the customer's folder for you.
Then switch to that folder for later sessions.

### 2. Call the skills by name

Type the skill as a slash command, followed by whatever you have for this call:

| Command | When |
|---|---|
| `/customer-meeting-recap` | After a call: recap Doc + Jira tickets |
| `/customer-session-prep` | Before a call: one-page prep brief |

You can also just ask ("recap this call", "prep me for Thursday's session") and Claude picks the
right skill. The slash command makes sure.

### 3. Add links as needed

The skill only knows what's in your prompt, the customer's `CLAUDE.md` and the opportunity's
Drive folder. Give it links the first time, and whenever something new comes up. It saves them
to `CLAUDE.md`, so later runs need only the call.

**First recap for a new customer:** give it everything you have.

```text
/customer-meeting-recap <Gong link>
Drive folder: <Drive folder link>
Salesforce opportunity: <Salesforce link>
Vitalstatistix: <Vitalstatistix link>
```

**Every recap after that:** just the call. Paste the transcript instead if there's no recording.

```text
/customer-meeting-recap <Gong link>
```

**A new opportunity for an existing customer:** add its Salesforce link. The skill adds a new
opportunity to `CLAUDE.md` and asks, link by link, whether to reuse the existing Drive folder and
Vitalstatistix links or use new ones.

```text
/customer-meeting-recap <Gong link>
New opportunity: <new Salesforce link>
```

**Before a call:** name the session or date if it isn't the next one, and the opportunity if the
customer has several.

```text
/customer-session-prep
/customer-session-prep for the 2026-11-04 session, RSA100 opportunity
```

**Picking up an existing customer:** point the skill at the earlier engagement's Drive folders.
It finds the customer's folder through Glean and checks the old session plan against the Gong
calls. If the new Drive folder doesn't exist yet, say so: the skill keeps the brief as a local
draft and saves it once you send the folder.

```text
/customer-session-prep use the latest Gong recording. Earlier work is in <Drive folder link>. Don't save yet, no Drive folder.
```

If anything is missing, the skill asks for all of it in **one** message, and never guesses a
link.

### 4. Review, then adjust

- **The recap and brief are linked in the chat** as Google Docs. Rerunning a skill for the same
  date updates that day's Doc instead of making a copy.
- **Tickets are created without asking first.** Check them, then ask for changes in the same
  session, e.g. "rename KEY-123 to …" or "that one is Alex's, unassign it".
- **The skill tells you what it added to `CLAUDE.md`** at the end of each run. You can also edit
  that file yourself, e.g. to fix a role or add a link.
- **On your phone:** use **Remote Control** of a session running on your computer. The skills don't
  work in a cloud session, which has none of your tools or sign-ins.

## What's in this repo

| Path | What it is |
|---|---|
| `install.sh` | Asks the questions, then installs the skills and the Drive helper's libraries |
| `ACCESS-AND-SETUP.md` | Full setup: credentials step by step, what works and what's blocked, troubleshooting |
| `claude-code/customer-meeting-recap/` | The recap skill: `SKILL.md`, `scripts/jira_ticket.py` (Markdown → Jira ticket), `scripts/gdrive.py` (Drive helper), `references/` |
| `claude-code/customer-session-prep/` | The prep skill: `SKILL.md` |
| `.github/workflows/` | The checks that run on every pull request (see below) |
| `.github/scripts/` | The privacy scan and docs check those workflows run |

## Checks on every pull request

Changes go to `main` through pull requests. Each one runs:

| Check | What it does | Fails when |
|---|---|---|
| **Privacy scan** | Scans every file and the PR's commit messages | A link isn't on the allowlist of public setup pages, or there's a real email address, a real-looking Jira key, an account or Salesforce ID, or a token |
| **Code and docs** | `shellcheck` on `install.sh`, compiles the Python scripts, checks Markdown formatting and that every relative link in the docs works, and that every `{{PLACEHOLDER}}` in the skills is one `install.sh` fills in | Any of these fails |
| **README updated with code changes** | Compares what the PR changed | The skills or `install.sh` changed but `README.md` and `ACCESS-AND-SETUP.md` didn't. Add the `no-docs-needed` label if nothing users see has changed |

None of these need a key or token: they run on GitHub's own runners.

To run the same checks on your computer before pushing:

```bash
python3 .github/scripts/privacy_scan.py && python3 .github/scripts/docs_check.py && shellcheck install.sh && npx markdownlint-cli2 "**/*.md"
```

### Review each pull request with Claude Code before merging

The privacy scan can't catch customer or colleague **names**, because a public list of names to
block would itself leak them. So before merging, have Claude review the pull request from your
own Claude Code session. It uses your normal Claude sign-in, and no key or token is stored in
GitHub. In Claude Code, run:

```text
/code-review --comment <pull request URL>
```

It posts its findings as comments on the pull request. Ask it to check in particular:

- **Privacy:** anything that names or identifies a real customer, company or colleague, any
  customer or internal link, and any account or record ID, including in commit messages.
- **Correctness:** skill instructions that contradict each other, steps that would fail, and
  `{{PLACEHOLDERS}}` that `install.sh` doesn't fill in.
- **Docs:** which parts of `README.md` or `ACCESS-AND-SETUP.md` the change makes out of date.

Without `--comment`, the findings stay in your Claude Code session instead.

## Rules for this repo

- **No customer data, no links.** No customer names, customer or internal links, account IDs or
  colleagues' names, anywhere: skills, examples, docs or commit messages. Use made-up examples
  (`Acme`, `Alex`, `KEY-123`).
- **No credentials or personal settings.** They live in each person's `~/.config/`. The
  `.gitignore` blocks common credential files and `CLAUDE.md` as a backstop.
- **Edit `claude-code/`, then rerun `./install.sh`.** The installed copies are replaced on every
  install. The master copy uses `{{SKILLS_DIR}}`, `{{CUSTOMERS_DIR}}`, `{{JIRA_SITE}}` and
  `{{JIRA_PROJECT}}` wherever a personal setting goes; keep those placeholders as they are.
