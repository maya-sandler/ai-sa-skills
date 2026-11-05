# ai-sa-skills

Claude Code skills that take the busywork out of running customer engagements: prepare for a meeting, automatically recap meetings (no prompt needed) and create a customer-facing document of all meetings, create Jira tickets as needed, and create a historical deep research for old-logo customers.

This repo includes:

- **An installer** (`install.sh`), with the setup steps in [Install](#install) below.
  The installer asks a few questions, installs the skills with your settings, and creates your
  **Active Customers Doc**, the Google Doc listing the customers the skills use and easy to maintain. 
  [Install](#install) also walks you through the Jira and Google Drive sign-ins.
- **Two automated workflows**, run by one hourly scheduled task in the Claude desktop app
  (`customer-recap-check`):
  1. **Automatic recaps:** finds Gong's "call is ready" emails for your Active customers, writes
     the recap and Jira tickets, updates the customer-facing Doc, and reports in your Slack
     self-DM. See "`customer-recap-check` workflow" below for the flowchart.
  2. **Active Customers sync:** copies your Active Customers Doc into each customer's
     `CLAUDE.md`, and creates the folder for a new Active customer. Skipped silently when
     there's no Active Customers Doc. See "Your Active Customers Doc" below.
- **Five Claude Code skills** (in `claude-code/`):

| Skill | What it does | How it runs |
|---|---|---|
| **`customer-meeting-recap`** | After a call, turns the recording or transcript into a recap Google Doc in the customer's Drive folder, and creates a Jira ticket for every follow-up the LaunchDarkly team committed to | **Manual:** you prompt it (`/customer-meeting-recap`). The recap check also runs it automatically |
| **`customer-session-prep`** | Before a call, writes a one-page prep brief (a Google Doc in the same folder) from that folder's recaps, so you know in two minutes what to deliver, what's still open, and what to ask | **Manual:** you prompt it (`/customer-session-prep`) |
| **`customer-engagement-prep`** | The same brief plus the engagement's history (earlier engagements, older folders, every Gong call), for a new engagement or an account you're picking up | **Manual:** you prompt it (`/customer-engagement-prep`) |
| **`customer-shared-notes`** | Adds each recap to the customer-facing `<Customer>-LaunchDarkly Master Engagement Doc`, newest meeting on top, without Jira tickets or internal links | **Manual** (`/customer-shared-notes`), and **automatic:** the recap check runs it after every recap |
| **`customer-recap-check`** | Every hour, syncs your Active Customers Doc into each customer's `CLAUDE.md`, then looks for Gong's "call is ready" emails for your Active customers, recaps the new ones, updates the Master Engagement Doc, and tells you in your Slack self-DM, asking there when links are missing | **Automatic workflow:** a scheduled task in the Claude desktop app, set up once ("set up the recap check") |

**Where you call them from:** Claude Code. You can't call them from Slack or the Chat tab. Slack is only
where the recap check reports to you and asks for missing links; you answer by replying in the
post's thread, and the next hourly run reads your reply.

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
| Knowing a call is ready to recap (recap check) | Gong's **"call is ready" email**, read from your Gmail through **Glean** | Arrives about two hours before Glean's Gong search finds the call, and only goes to people who were on it |
| Creating Jira epics and tickets | **Atlassian CLI (`acli`)** with your Jira **API token** | Writes to Jira without an OAuth app, which company admins often block |
| Saving and reading Google Docs | A small **Drive helper** (`gdrive.py`) with your own Google **OAuth client** | Writes real Google Docs into the customer's folder, and can only touch the Docs it created |
| Telling you a recap is ready, and asking you for missing links (recap check and recap) | **Slack** (Claude connector): posts to your self-DM by sharing a small file, reads your replies | The connector's file-sharing tools are the ones that can post; it never posts anywhere but your self-DM |
| Running on a schedule (recap check) | A Claude Code **scheduled task** in the desktop app | Runs on your Mac with your sign-ins; nothing runs in the cloud |

## What each skill produces

### `customer-meeting-recap`

You say something like *"Recap this call: \<Gong link\>"*, or paste a transcript.

1. **Reads the whole call.** From your paste, or the full Gong transcript through Glean, never
   Gong's summary. It works out who each speaker is.
2. **Asks once for any missing link** (Drive folder, Salesforce, Vitalstatistix, session plan,
   the customer's Slack channels) in one message, in chat and in your Slack self-DM, and waits
   for your answer before it saves anything. Answer in either place. If you don't answer, the
   hourly recap check picks the call up from the Slack thread, as for its own calls. Links you
   skip become `Not found`, and it lists them at the end.
3. **Reads what came before.** The previous recap in the customer's Drive folder, so it can mark
   earlier action items as done or still open, and the customer's Slack channels since the last
   call, for follow-ups and promises. Channels are never named in the recap or tickets.
4. **Writes the recap** and saves it as `<Customer> – Meeting Recap – <date>` in the Drive folder:
   - Summary and what was discussed, including decisions
   - Artifacts shared, plus relevant LaunchDarkly docs (only links it has confirmed exist)
   - Scheduled meetings, with dates
   - **Action items – LaunchDarkly team**, with owner, due date and Jira ticket
   - **Action items – \<Customer\>**, with owner and due date
   - **Next steps**: open questions (theirs and ours) and decisions still to make, never
     repeating an action item
   - The status of the previous recap's action items
   - **Customer links**: opportunity, Salesforce, Drive folder, Vitalstatistix, Jira epic, team
5. **Finds or creates the customer's Jira epic** (named after the customer, in Title Case) in your
   own Jira project.
6. **Creates one ticket per LaunchDarkly team action item**, skipping any that already exist:
   - **Title:** `<Owner>: <short task>`, e.g. `Alex: Confirm Big Segments Need Persistent Store`.
     No customer name, since the epic already says that.
   - **Assignee:** you, if it's your task. Other people's tasks are left unassigned, so the name in
     the title tells you it's one you only need to follow up on.
   - **Description:** the ask, background, why it matters, a one-sentence definition of done,
     and the customer links.

### `customer-session-prep`

The quick prep. You say something like *"Prep me for the next Acme session"*. It looks only at the
customer's current Drive folder (the one you give, or the Folder link in your Active Customers
Doc): the recaps in it, the follow-up items from them that are still open (checking their Jira
tickets), the customer's support tickets, tech stack, session plan and links, and the Slack
channels in your Active Customers Doc. It saves a one-page brief as
`<Customer> – Session Prep – <session name> (<date or date TBD>)`:

- Goal for the session and the latest status
- **Deliver in \<session name\> (\<date or date TBD\>):** finished tickets to show or explain, and
  open ones that are due
- The customer's next steps and questions, each with a draft answer or a docs link
- Action items to follow up on, split into the customer's items and LD's internal items
- Support tickets, tech stack, and where the engagement stands in the session plan
- All the links in one place, each labelled with the customer's name

It doesn't look at earlier engagements, older folders or the customer's other Gong calls. That's
`customer-engagement-prep`.

### `customer-engagement-prep`

The full prep, with the engagement's history: use it for a new engagement, or an existing customer
(an existing logo) you're picking up. On top of what `customer-session-prep` reads, it searches the
team's older Drive folders and every Gong call for the account, and saves
`<Customer> – Engagement Prep and Next Session (<session name>, <date or date TBD>)`, for example
`Acme Corp – Engagement Prep and Next Session (kickoff, date TBD)`:

It has two parts. **Where things stand:**

- Latest status, with anything inferred (a plan name, a trial) marked "Confirm" instead of stated
  as fact
- **The customer's business model and context design:** how the customer sells and deploys its
  product, how it gates features today, a first context kind and segments to propose, concerns
  the customer raised, and whether the deal's numbers (MAU, service connections) matter here
- **Where the earlier engagement left off:** the pre-sales calls for a new engagement, or each
  planned session from the old kickoff deck checked against the Gong calls (happened, partly,
  never), plus promises still open
- Action items for the customer and for LD, support tickets, the session plan, links, and the
  tech stack with a question under each item that's still open

Then, under **NEXT:**

- **Questions for the customer** at the session, numbered, most important first
- **Questions for the LD account team** (AE, SE, CSM) before the session: plan, SOW scope, what a
  POC validated
- **The customer's open questions to LD**, each with the answer on its own line and docs links
- **The plan for the session:** prep to do first, then the suggested engagement plan with what
  to show live and which customer pain each answers

Both briefs use the customer's name and "LD" instead of "they" or "we", so they read clearly
when you forward them.

### `customer-shared-notes`

The Doc you share with the customer. You say something like *"Update the Master Engagement Doc
for Acme"*, or the recap check runs it after each automatic recap. It keeps one Google Doc per
opportunity, `<Customer>-LaunchDarkly Master Engagement Doc`, in the opportunity's Drive folder:

- **One block per meeting, newest on top,** each with the same sections as the recap: summary,
  what was discussed, artifacts, scheduled meetings, both sides' action items, and next steps.
- **Everything internal is left out:** Jira tickets and keys, Salesforce, Vitalstatistix, Slack
  and internal Drive links, the internal Gong link, internal-only tasks and deal notes. Public
  docs links stay.
- **A Gong share link,** if you made one and replied with it in Slack, goes on the meeting's
  **Recording** line.
- **It only copies from the recaps** in the Drive folder, never rewording or adding anything. To
  fix a meeting, fix its recap and ask to refresh that meeting.
- **It never adds a meeting twice** (a small ledger on your Mac records which recaps are in), and
  it keeps any edits you or the customer made to the Doc.

The Doc stays private to you: review it, then click **Share** in the Doc and add the customer's
people yourself.

### `customer-recap-check`

You set it up once: answer **y** to the installer's last question, or say "set up the recap
check" in a Code session in your `ai-sa-skills` clone (worktree off, Auto mode). After that, a scheduled task runs it every hour,
by default from 9:05 to 21:05 on weekdays, and you don't prompt anything. The schedule is the only
trigger: a call whose Gong email arrives by about 21:00 is recapped the same day, and a later one
at the first check of the next weekday.

1. **Reads your Active Customers Doc** (see "Your Active Customers Doc" below) and works only on
   the rows marked Active. It also copies every row into its customer's `CLAUDE.md` (the
   Active Customers sync).
2. **Finds Gong's "call is ready" emails for your active customers only,** since the last run
   (Gmail, through Glean). It searches once per Active row, by its Gong account, and works only on
   emails whose Gong account exactly matches an Active row. Anything else is skipped silently, so
   other calls make no work. Gong sends one to each
   participant when a call's recording is ready, so it knows you were on the call. It reads only
   the call link, account, date and duration from each email.
   **For each new call, it posts once in your Slack self-DM** that it saw the meeting, with the
   internal Gong link, and asks you to create a share link for the customer in Gong (click
   **Share** on the call) and reply in that thread with it, or reply "no link". Everything later
   about that call goes in the same thread.
3. **Skips calls already recapped,** using a processed-calls log on your Mac and the Gong call ID
   each recap records, so a call is never recapped twice.
4. **Waits for the full transcript** in Glean, and writes the recap only from it.
5. **Runs `customer-meeting-recap` unattended:** it never stops to wait. Only a missing Drive
   folder holds the call, since there's nowhere to save the recap: it asks you in Slack, and
   reminds you at most once a day. Anything else missing (which opportunity it is, Salesforce,
   Vitalstatistix, session plan, Slack channels) doesn't hold it: the recap and tickets are made
   with `Not found` for it, and the "recap ready" post asks you for it. When you reply, the link
   is saved to the customer's `CLAUDE.md` and filled in on the recap Doc. If the opportunity was
   missing, the meeting is then added to the Master Engagement Doc (which never shows internal
   links).
6. **Updates the Master Engagement Doc:** after each finished recap, runs `customer-shared-notes`
   to add the meeting to the opportunity's customer-facing `<Customer>-LaunchDarkly Master
   Engagement Doc`. It runs only once the recap is saved, never in dry-run mode, and never adds a
   meeting twice.
7. **Posts in the call's Slack thread:** "recap ready" with the links, including the Master
   Engagement Doc, or a question you answer by replying in the thread. A Gong share link you
   reply with is added to that meeting in the Master Engagement Doc (straight away if the meeting
   is already there, otherwise with the recap), and the check confirms in the thread. The next run reads your reply and
   finishes the call. A Claude notification on your Mac and phone pings you too, since Slack
   doesn't notify you about posts made as you.
8. **Logs everything** to one Markdown file on your Mac, `~/.config/sa-skills/recap-check-log.md`:
   a section per run, with an **activity** line for every step and tool call and an **audit**
   line for every change made in Drive, Jira or Slack. Nothing is logged to Drive.

It starts in **dry-run mode** (see below): it only reports what it would do, until you switch it
to live.

#### `customer-recap-check` workflow

What each hourly run does, in live mode:

```mermaid
flowchart TD
    T(["Scheduled hourly task (9:05 to 21:05)"]) --> AC[Find active customers in “Active Customers” doc]
    AC --> E[Search for “Gong's call-is-ready” email]
    E --> C{Find Gong account match with an active customer?}
    C -- No --> X([Skip it])
    C -- Yes --> S["Post “Saw the meeting” with the internal Gong link, asking for a customer share link"] --> D{Already recapped?}
    D -- Yes --> X2([Skip it])
    D -- No --> TR{Full transcript in Glean?}
    TR -- Not yet --> W([Wait for the next run])
    TR -- Yes --> DF{Drive folder known?}
    DF -- Yes --> R
    DF -- No --> Q2[Ask in your Slack self-DM for all missing links] --> H[(Held call, waiting for your reply)]
    H -. next run .-> RP{Did you reply to the self-DM in thread?}
    RP -- Yes, with the folder --> R
    RP -- No --> RM[Remind in the self-DM, once a day] --> H
    R["Write recap doc with “Not found” for missing links & create Jira tickets"] --> SN[Add last recap to the “Master Engagement Doc”]
    SN --> P[Post “Recap ready” in self-DM, asking for any missing links]
    P -. you reply .-> U[Save the links to CLAUDE.md, fill them in on the recap doc]
    S -. you reply with a share link .-> SL[Add it to that meeting in the Master Engagement Doc, and confirm in the thread]
```

**Log:** every step is logged as it happens, with its own time, to
`~/.config/sa-skills/recap-check-log.md` on your Mac (one section per run). The run ends with a
one-line summary. Nothing is logged to Drive.

**Replying:** reply in the thread of the post that asked, in your Slack self-DM, with the links.
Replying "skip" for a link writes `Not found` for it, and it isn't asked for again. A Gong share
link goes in the call's thread too; it's added only to the Master Engagement Doc, never to
`CLAUDE.md`, the internal recap or the log.

**Not in the diagram:** you can still run `/customer-meeting-recap` yourself at any time, for
example for a call the check skipped. It asks you for missing links in chat and in your self-DM,
and if you don't answer, the next hourly run finishes the call from the Slack thread.

#### Dry-run mode

Dry-run mode is a trial mode, so you can see what the check would do before it writes anything.
**The check starts in dry-run mode when you set it up,** and stays in it until you say "switch
the recap check to live".

- **What it does:** every hourly run reads your Active Customers Doc, finds and matches the Gong
  emails, and skips calls already done, exactly as in live mode. Then, instead of the recap, it
  posts one message per call in your self-DM: "Dry run: would recap *\<title\>* with
  \<Customer\> and add it to the Master Engagement Doc; links missing: \<links\>".
- **What it doesn't do:** it writes no recap, creates no Jira tickets, doesn't touch the Master
  Engagement Doc, and asks no questions. Its log lines are marked "dry run".
- **What it's for:** checking that your Active Customers rows (Gong account, Folder link) find the
  right calls, and that the links each recap needs are in place, before anything is created.
- **Going live:** say "switch the recap check to live" (or "switch the recap check to dry run" to
  go back). Calls a dry run reported in the last 2 days are then recapped for real. Older ones
  are skipped.

## Your Active Customers Doc

One Google Doc in your own Drive folder, `Active Customers`, that you keep yourself and can edit
from any device. **Every customer skill reads it first and works only on customers marked
Active** (any case), so old customers are left alone. Put in it whatever you want the skills to
know:

| Customer | Documentation name | Folder link | Salesforce opportunity | Slack channels | Gong account | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Acme | Acme Corp | `<Drive folder link>` | `<Salesforce opportunity link>` | `<Slack channel links>` | Acme Corporation | Active |

- **Customer:** your name for it. Its local folder is that name in lowercase, with hyphens.
- **Documentation name:** the name used in every Doc, e.g. `Acme Corp – Meeting Recap –
  2026-10-26`. Blank: the Customer value is used.
- **Folder link:** the Drive folder where the customer's recaps and prep briefs live.
- **Salesforce opportunity:** the link to the opportunity you're working on now. It tells the
  skills which opportunity in `CLAUDE.md` a call or brief belongs to.
- **Slack channels:** the customer's channels and chats (shared channel, internal account channel,
  group DMs). The skills read them for context and never name them in a Doc or ticket.
- **Gong account:** the account name Gong shows, so the recap check finds the customer's calls.
- **Status:** Active or Not active.

**Changes flow into `CLAUDE.md` automatically.** Every hourly recap check copies each row into
its customer's `CLAUDE.md`, in a section called "From the Active Customers Doc", and creates the
folder and `CLAUDE.md` for a new Active customer. So edit the Doc, not that section: an edit
reaches `CLAUDE.md` within the hour (during the check's hours). The rest of `CLAUDE.md`
(opportunities, team, calls) is never touched by this. With no Active Customers Doc in your
folder, the sync is skipped silently and no `CLAUDE.md` changes. If the two disagree, the Doc wins. A customer that isn't in the Doc, or isn't Active, gets a message
asking you to mark it Active, and nothing else. `install.sh` creates the Doc (its last question), and
"set up the recap check" creates it if it's still missing. Without it, the skills work from
`CLAUDE.md` alone.

## How it keeps track of each customer

Each customer gets a small local folder, e.g. `~/work/customers/acme/`, holding a single
`CLAUDE.md`. Claude Code reads it automatically when you open a session there. It's an address
book, not notes: the customer's Jira epic, team, latest call and tech stack, and a list of
**opportunities**, each with its own links:

```
## Opportunities
### RSA50 opportunity (1)    ← Salesforce opportunity, Drive folder, Vitalstatistix, session plan
### RSA100 opportunity
### RSA50 opportunity (2)
```

- **The skills create and update this file for you** as they learn links, people and facts.
- **They never guess links.** Salesforce, Drive and Vitalstatistix links come only from your
  prompt, the opportunity's own Drive folder, or your answer. If one is missing, the skill asks
  you for all the missing ones in one message.
- **Slack channels come only from you.** The recap asks for the customer's channels and chats
  (shared channel, internal account channel, group DMs) and saves them in a **Slack** section.
  It never searches for them, and never names them in a Doc or ticket.
- **New opportunity?** Give the skill the new Salesforce link (or say it's a new opportunity). It
  adds a new entry and asks, link by link, whether to reuse an existing opportunity's link or use
  a new one.

Everything the skills *produce* (recaps, briefs, transcripts) goes to Google Drive. Nothing but
this `CLAUDE.md` is kept on your computer.

## Install

### Prerequisites

- **Claude Code**, with the **Glean** and **Slack** connectors switched on. In claude.ai,
  **Settings → Connectors**, check both are connected and enabled for Claude Code:

  | Connector | What the skills use it for |
  |---|---|
  | **Glean** | Search and read: Gong's emails in your Gmail, call transcripts, the customer's Drive folder, Jira and Salesforce |
  | **Slack** | Read channel and read thread (your self-DM, and the customer channels you listed), and the two file-upload tools (get file upload URL, complete file upload), which is how it posts to your self-DM |
- **Your Gmail comes through Glean,** so no extra API, token or Gmail connector is needed. Your
  company connects Gmail to Glean, and Glean only returns what you can see yourself; the recap
  check uses it to find Gong's "call is ready" emails, and opens no other mail. Check that a
  Glean search shows your Gmail, keep those Gong emails on (they are by default), and don't
  filter them out of your inbox. (The Google token you create below covers only the Drive files
  the skills make, and the Jira token only Jira: neither can read your Gmail.)
- **macOS** with Homebrew and Python 3 (tested on macOS; Linux should work with small changes).
- **A Jira project of your own** for customer tasks, plus a **Jira API token**.
- **Edit access to each customer's Google Drive folder**, plus a **Google OAuth client** you
  create in your company's Google Cloud organization.

#### About the credentials

You create **two credentials, once**, one for Jira and one for Google Drive. You never paste
either into Claude, a chat or this repo: each goes into a private file on your Mac, by a command
that writes the file for you, and Claude never reads it. The steps are in
[Sign in to Jira](#sign-in-to-jira) and [Sign in to Google Drive](#sign-in-to-google-drive)
below.

| | Jira | Google Drive |
|---|---|---|
| What you create | An **API token** in your Atlassian account's Security settings | An **OAuth client** (a Client ID and a Client secret) in your own Google Cloud project. There's no Google API key or token to create |
| Where you put it | Copy the token, then run one command that saves your clipboard to **`~/.config/acli/token.txt`** (readable only by you). You don't create or open the file yourself | Run the Drive helper's **`setup-client`** command and paste the Client ID, then the Client secret, when it asks (the secret stays hidden). It writes **`~/.config/sa-skills/google/client_secret.json`** for you |
| Then | Run `acli jira auth login ... --token < ~/.config/acli/token.txt`, which reads the token from the file, so you never type it | Run the helper's **`login`** command and click **Allow** in the browser. That saves **`~/.config/sa-skills/google/token.json`**, which the helper reuses |
| What it can reach | What your Jira account can | **Only the Docs the helper created** (Google's `drive.file` permission) |
| Expires | On the date you choose (up to about a year): then create a new token and repeat both steps | Renews itself |

**Keep them safe:**
- Never paste the token or the client secret into a Claude chat, and never ask Claude to read
  `~/.config/acli/token.txt` or anything in `~/.config/sa-skills/google/`. The skills pass them
  only to `acli` and the Drive helper; they never open them.
- Keep these files private (`chmod 600`, which the commands below do), outside any git repo, and
  don't share them. Each person creates their own: a token is what identifies *you*.

Why not simpler options? At many companies the Atlassian MCP connector and `acli`'s browser
sign-in are blocked by admin policy, and Claude has no Google Drive connector with write access.
The API token and your own OAuth client are what work. See
[What works and what's blocked](#what-works-and-whats-blocked).

### Run the installer

**1. Get the repo.**

```bash
git clone <this repo's URL>
```

**2. Set your Jira project key, once, before the first install.** It's the project your customer
tasks go to: the letters before the dash in ticket keys (`ABC` in `ABC-123`). It's the project's
short name, not a secret or an API key, and it's separate from your API token. Use your own project, so your tickets
don't land in someone else's. The installer doesn't ask for it; it stops and reminds you if it
isn't set.

To find your key, open any ticket in the project where your customer tasks should go. The
ticket number starts with the key: for a ticket `SA-482`, the key is `SA`. Replace `ABC` with
your key:

```bash
cd ai-sa-skills && python3 claude-code/customer-recap-check/scripts/recap_check.py config set jira_project ABC
```

To change it later, run the same command with the new key, then the installer again.

**3. Run the installer** from the same folder, in the Mac's **Terminal** app (it asks
questions, and copies the last step's prompt to your clipboard):

```bash
./install.sh
```

Run every command in this guide in **your own terminal**, not in the Claude chat box.

It asks these questions. Each one suggests a value: press **Enter** (or type `y`) to keep it.

| # | It asks | What to answer | Why it's asked |
|---|---|---|---|
| 1 | Where should the skills be installed? | **Enter** for `~/.claude/skills` (recommended: available in every Claude Code session), or `2` for one project's `.claude/skills` | Claude Code loads skills from these folders |
| 2 | What is the local path you want your customer CLAUDE.md files saved in? | **Enter** to keep it, or type another folder path starting with `~/` or `/`, e.g. `~/clients` | Where each customer's `CLAUDE.md` of links goes. Recaps and briefs are saved to Google Drive, not here |
| 3 | Confirm your Jira site is `launchdarkly.atlassian.net` | **Enter** to confirm, or type another site | For ticket links |
| 4 | Your team's shared base Google Drive folder for customer projects (required) | Paste the team folder link, or **Enter** to keep a saved one. Everyone uses the same folder; ask your manager if you don't have it | The skills search it for earlier engagements with a customer |
| 5 | Your own Google Drive folder, where I'll create your Active Customers Doc | Paste the folder link, **Enter** to keep a saved one, or type `pass` to skip for now | Every customer skill reads the Doc. If you skip it, setting up the recap check asks for the folder |
| 6 | At the end, after installing: Turn on the automated workflows (the hourly recap check)? | **y** to set it up now (see below), or **Enter** to skip and do it later | The recap check runs as a scheduled task in the Claude desktop app, which the installer can only hand you off to |

After question 5 it shows **"Please confirm your selections"**, with every answer and your Jira
project key.
Check them, then press **Enter** to install, or type `n` to stop without changing anything.
An answer that doesn't fit (a "yes" where a folder or site should be) is asked again, never saved.

**Question 6, the automated workflows.** After installing, it asks whether to turn on the
hourly recap check. A shell script can't create the scheduled task: only a session in the
Claude desktop app can, and the setup needs the app's Slack and Glean sign-ins. On **y** it:

1. Shows two Claude Code permission rules and, if you agree, adds them to this clone's
   `.claude/settings.local.json` (on your Mac only, ignored by git). They let **Auto** mode
   delete and create the scheduled task; Auto mode's automatic check blocks that otherwise.
2. Copies the setup prompt to your clipboard (and prints it, in case the copy didn't reach your
   clipboard), and opens the Claude app.
3. Tells you what to do there: a **brand-new** Code session (one already open hasn't read the
   rules) in this clone, worktree off, permission mode **Auto**, then paste the prompt.

Why Auto: the task runs in the folder **and the permission mode** of the session that creates
it. In Auto, the hourly runs never stop to ask you; in Ask permissions they could wait, unattended,
for an approval nobody gives. Press **Enter** to skip, and rerun `./install.sh` to turn them on
later. Run from a temporary worktree, it tells you to use your main clone instead.

**What it replaces, and what it leaves alone,** when things already exist (it's safe to rerun):

| Already there | What the installer does |
|---|---|
| The installed skills it installs (`customer-meeting-recap`, `customer-session-prep`, `customer-engagement-prep`, `customer-recap-check`, `customer-shared-notes`) in the skills folder | **Replaced** with this repo's copy. Any edits you made to the installed copy are lost: edit `claude-code/` instead |
| Other skills in the same skills folder | Left alone |
| Your customer folders and each customer's `CLAUDE.md` | Left alone. It only creates the top folder if it's missing |
| `~/.config/sa-skills/config.json` | Your answers are updated; everything else in it (Jira project key, Slack self-DM, recap check mode) is kept |
| The processed-calls log, run log and shared-notes ledger in `~/.config/sa-skills/` | Left alone |
| Your Active Customers Doc | Left alone: it finds the Doc already in the folder instead of making a second one |
| Google and Jira sign-ins | Never read or changed |
| The Drive helper's Python libraries | Reused; only missing ones are installed |

It also installs the Drive helper's Python libraries, then shows which sign-ins are still needed
and the link to your Active Customers Doc. The Doc needs the Google Drive sign-in, so on a first
install it's created when you run `./install.sh` again after signing in.
Your answers are saved in `~/.config/sa-skills/config.json` and offered as defaults next time.
Rerunning it keeps the settings the skills saved there themselves, such as your Slack self-DM.
Rerun it any time: to change an answer, or after `git pull` brings newer skills. The commands
below assume the recommended `~/.claude/skills`; if you chose a project folder, use
`<project>/.claude/skills` in their place.

The installer never asks for, reads or prints a token or secret.

**Then sign in, once (about 25 minutes),** with the two sections below: Jira (about 10 minutes),
then Google Drive (about 15). If a step fails, see [Troubleshooting](#troubleshooting).

### Sign in to Jira

**1. Install `acli`** (the Atlassian CLI), one command at a time in your terminal:

```bash
brew tap atlassian/homebrew-acli
```

```bash
brew trust atlassian/acli
```

```bash
brew install acli
```

Trusting a Homebrew tap is a security setting, so run these yourself. `brew install` fails with
"Refusing to load formula … from untrusted tap" until the trust step has worked;
`brew trust --json=v1` should list `atlassian/acli` under `"taps"`.

**2. Create an API token** in your Atlassian account's **Security** settings (not Jira's
Personal settings): https://id.atlassian.com/manage-profile/security/api-tokens, or in Jira, your
profile picture → **Manage account** → **Security** → **Create and manage API tokens**. Click
**Create API token**. Pick the plain one, not "with scopes": it gets exactly your own Jira
permissions, and the skills need nothing more than you already have (view and create issues
in your own project and comment on them). Name it e.g. `acli-claude-code`, pick an expiry date,
then **Copy**. It's shown only once.

**3. Save it to a private file,** `~/.config/acli/token.txt`, right after clicking Copy, before
you copy anything else:

```bash
mkdir -p ~/.config/acli && pbpaste > ~/.config/acli/token.txt && chmod 600 ~/.config/acli/token.txt
```

The file holds only the token, on one line, no quotes or label. It looks like this (made up,
and much shorter than a real one, which is about 190 characters):

```text
ATATT3xFfGF0Ex4mPleT0kenN0tReal1234567890abcdef=A1B2C3D4
```

Check its size without printing it: `wc -c < ~/.config/acli/token.txt` should say about 190.
A small number like 23 means the clipboard held something else: copy the token again and rerun
the command. Never paste the token into a chat or a repo file.

**4. Sign `acli` in to Jira.** This uses the token file from step 3, so you never type the token.
Replace the site and email with yours:

```bash
acli jira auth login --site yourcompany.atlassian.net --email you@yourcompany.com --token < ~/.config/acli/token.txt
```

You should see `✓ Authentication successful`. `acli` remembers the sign-in, so the skills can create
and read your tickets from then on; `acli jira auth status` checks it.

### Sign in to Google Drive

The skills save Docs to your Drive with their own small app, which you create once in Google
Cloud. Do these in order, each in your browser with your work Google account:

**1. Create a project:** https://console.cloud.google.com/projectcreate. Name it e.g.
`ai-sa-skills-<yourname>`, set **Organization** to your company's Google Workspace organization
(not "No organization"), then select it in the project picker at the top.

**2. Turn on the Drive API:** https://console.cloud.google.com/apis/library/drive.googleapis.com.
Check that the top bar shows your project, then click **Enable**.

**3. Set up the consent screen:** https://console.cloud.google.com/auth/overview → **Get started**.
App name `SA skills`, your email as contact, **Audience: Internal** (no Google review needed).

**4. Create the OAuth client:** https://console.cloud.google.com/auth/clients → **Create client** →
**Desktop app** → **Create**. Keep the dialog open: it shows the **Client ID** (ends in
`.apps.googleusercontent.com`) and the **Client secret** (starts with `GOCSPX-`, about 35
characters). Lost the secret? Open the client, click **Add secret** under "Client secrets", and
copy the new one right away: newer consoles show a secret only once.

**5. Save the client** in your terminal. It asks for the ID, then the secret, which stays hidden
as you paste:

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore ~/.claude/skills/customer-meeting-recap/scripts/gdrive.py setup-client
```

It saves them to `~/.config/sa-skills/google/client_secret.json`, readable only by you, and
prints `{"saved": ".../client_secret.json"}`. The file is Google's standard format. With made-up
values it looks like this; never paste yours into a chat or a repo file:

```json
{"installed": {"client_id": "123456789012-abc123def456.apps.googleusercontent.com",
               "client_secret": "GOCSPX-MadeUpExampleNotReal123456",
               "auth_uri": "https://accounts.google.com/o/oauth2/auth",
               "token_uri": "https://oauth2.googleapis.com/token",
               "redirect_uris": ["http://localhost"]}}
```

To check the secret without showing it, run this. A good one prints `GOCSPX- 35`:

```bash
python3 -c 'import json,os; s=json.load(open(os.path.expanduser("~/.config/sa-skills/google/client_secret.json")))["installed"]["client_secret"]; print(s[:7], len(s))'
```

(If you'd rather use Google's **Download JSON** button, save that file as
`~/.config/sa-skills/google/client_secret.json` and `chmod 600` it. In our test it didn't
download anything, so `setup-client` is the safer way.)

**6. Sign in:**

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore ~/.claude/skills/customer-meeting-recap/scripts/gdrive.py login
```

A browser opens: pick your work account and click **Allow**. The only permission it asks for is
"See, edit, create and delete only the specific Google Drive files you use with this app": it can't
see the rest of your Drive. The terminal prints `{"signed_in_as": "you@yourcompany.com"}`, and the
sign-in is saved in `~/.config/sa-skills/google/token.json`.

### After signing in: Active Customers, dry run, then live

Do these in order. The recap check needs both sign-ins and your Active Customers Doc, so turn it
on in step 2, not on the very first install (skip question 6 then, with **Enter**).

**1. Run `./install.sh` again.** It fills in your Jira site for you, shows that both sign-ins
are done, and creates your Active Customers Doc. Open it from the link it prints and add a row
per customer, marked Active, with its Gong account and Drive folder link.

**2. Turn on the recap check.** Still in that install, answer **y** to question 6 and follow its
steps (a brand-new Code session in this clone, worktree off, Auto mode, paste the prompt). The
check starts in **dry-run mode**: it writes nothing and only tells you what it would do.

**3. Check the dry run.** For your next few customer calls, look in your Slack self-DM after each
hourly run. For each call it should post "Dry run: Saw the Gong meeting…", then "Dry run: would recap
*\<title\>* with \<Customer\>…; links missing: …". Not waiting for a call? Say **"run the recap
check now"** in a Code session in this clone, to run one check right away (still a dry run).

| What you see | What to fix |
|---|---|
| Nothing for a call you were on | The row's **Gong account** must be exactly the account name Gong shows, and Status **Active** |
| "links missing: …" | Add the missing links to the customer's `CLAUDE.md`, or reply in the thread once live |
| No posts at all | The desktop app must be open and your Mac awake. Say "what did the recap check do today?" to read the run log |

**4. Go live** when the dry runs look right: say **"switch the recap check to live"** in any Code
session. From then on it writes the recaps, creates the Jira tickets and updates the Master
Engagement Doc. Calls the dry run reported in the last 2 days are recapped for real.

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
| `/customer-session-prep` | Before a call: one-page prep brief from the current folder's recaps |
| `/customer-engagement-prep` | Before a call, with the engagement's history: new engagements and accounts you're picking up |
| `/customer-shared-notes` | After a recap: add it to the customer-facing Master Engagement Doc (the recap check does this for you after each automatic recap) |
| `/customer-recap-check` | Set up, check on or change the automatic recaps. Usually said in words instead: see step 5 |

You can also just ask ("recap this call", "prep me for Thursday's session") and Claude picks the
right skill. The slash command makes sure.

### 3. Add links as needed

The skill only knows what's in your prompt, the customer's `CLAUDE.md` and the opportunity's
Drive folder. Give it links the first time, and whenever something new comes up. It saves them
to `CLAUDE.md`, so later runs need only the call.

**First recap for a new customer:** give it everything you have.

```
/customer-meeting-recap <Gong link>
Drive folder: <Drive folder link>
Salesforce opportunity: <Salesforce link>
Vitalstatistix: <Vitalstatistix link>
```

**Every recap after that:** just the call. Paste the transcript instead if there's no recording.

```
/customer-meeting-recap <Gong link>
```

**A new opportunity for an existing customer:** add its Salesforce link. The skill adds a new
opportunity to `CLAUDE.md` and asks, link by link, whether to reuse the existing Drive folder and
Vitalstatistix links or use new ones.

```
/customer-meeting-recap <Gong link>
New opportunity: <new Salesforce link>
```

**Before a call:** name the session or date if it isn't the next one, and the opportunity if the
customer has several.

```
/customer-session-prep
/customer-session-prep for the 2026-11-04 session, RSA100 opportunity
```

**Picking up an existing customer:** use `/customer-engagement-prep`, and point it at the earlier
engagement's Drive folders.
It finds the customer's folder through Glean and checks the old session plan against the Gong
calls. If the new Drive folder doesn't exist yet, say so: the skill keeps the brief as a local
draft and saves it once you send the folder.

```
/customer-engagement-prep use the latest Gong recording. Earlier work is in <Drive folder link>. Don't save yet, no Drive folder.
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

### 5. Let recaps happen on their own

Once the recap and its links work for a customer, let `customer-recap-check` do it for you. Set
it up from the installer (its last question) or in a Code session in your `ai-sa-skills` clone,
worktree off, in Auto mode: the scheduled task runs from the folder and in the permission mode of
the session that creates it. The other requests work in any Claude Code session. Say:

| Say | It does |
|---|---|
| "Set up the recap check" | Asks for your Drive folder, creates the Active Customers Doc there, finds your Slack self-DM, and schedules the hourly check (it asks which hours) in **dry-run** mode |
| "Add Acme to my active customers" | Adds a row to the Active Customers Doc (you can also edit the Doc yourself) |
| "Switch the recap check to live" | Starts writing recaps and creating tickets; until then it only reports what it would do |
| "Run the recap check now" | One check, right away, in this session |
| "Pause the recap check" | Stops the schedule until you resume it |
| "What did the recap check do today?" | Reads the run log, `~/.config/sa-skills/recap-check-log.md` |

To answer a question it asks in Slack, reply in that post's thread, e.g. with the Drive folder
link. It needs Gong's "call is ready" emails turned on (they are by default) and Glean able to
read your Gmail. The desktop app must be open and your Mac awake for a check to run; a missed check runs at
the next one.

## What works and what's blocked

What we found when setting this up (macOS, Claude Code in the desktop app's Code tab). Useful if
your IT team asks why it's set up this way.

| Access | Status | Notes |
|---|---|---|
| **Glean** connector | ✅ Works | Read-only. Reads Gong transcripts, Salesforce, Jira, Google Drive and Slack, limited to what you can see. **Can't create tickets or Docs** |
| **Jira through `acli` + API token** | ✅ Works | Creates epics and tickets with epic link, due date, assignee and formatted description |
| **Google Drive through your own OAuth client** | ✅ Works | Creates and updates Google Docs in the customer folder and reads them back |
| **Gmail through Glean** | ✅ Works | Glean reaches your Gmail live. The recap check uses it only to find Gong's "call recording and analysis is ready" emails |
| **Slack** connector, posting by file share | ✅ Works | The recap check posts to your self-DM by sharing a small file with a message, and reads your replies. Only the file-upload tools can post |
| **Slack** connector, reading a customer's channels | ✅ Works | The recap reads only the channels and chats you listed for that customer |
| Jira through `acli` browser sign-in (`--web`) | ❌ Blocked | Approving in the browser still returns `access_denied`, most likely an admin policy on OAuth apps |
| Atlassian Rovo MCP connector | ❌ Blocked | Couldn't be connected. Probably the same admin policy |
| Google Drive connector for Claude | ❌ Not enabled | Not available to Claude at the time of writing. Ask IT if that has changed |
| Slack connector, plain send-message tool | ❌ Not offered | Not among the connector's tools at the time of writing. The recap check would switch to it |
| Gong / Salesforce connectors | ➖ Not available | Glean covers both |
| Gong webhooks | ➖ Not needed | Need a Gong admin and a public endpoint. The recap check reads Gong's emails instead |
| API keys in `.env` for the desktop app's **Chat tab** | ❌ Won't work | Chats run in the cloud and can't see your Mac's files or tools. That's why these skills run in Claude Code |

## Troubleshooting

| Problem | Fix |
|---|---|
| `acli` says `unauthorized` | The Jira token expired or was revoked. Repeat steps 2 to 4 of [Sign in to Jira](#sign-in-to-jira) with a new token, and delete the old one |
| The Drive helper says `not signed in` | Rerun step 6 of [Sign in to Google Drive](#sign-in-to-google-drive) (`login`) |
| `invalid_client: The provided client secret is invalid` after clicking Allow | The saved secret doesn't match. Check it with the command in step 5; if it's wrong, add a new secret (step 4), then redo steps 5 and 6 |
| The Drive helper says the client file is missing | Run step 5 (`setup-client`) |
| Saving a Doc fails with "can't add files to it" | You need edit access to the customer's Drive folder: ask its owner to make you an editor |
| No "Create API token" button, or no permission to create a Google Cloud project | Ask your IT team |
| `brew install acli` says "Refusing to load formula … from untrusted tap" | Run `brew trust atlassian/acli` first (step 1 of [Sign in to Jira](#sign-in-to-jira)) |
| You can't find `~/.config` in Finder | It's hidden: press ⌘ + Shift + . to show hidden folders, or check from the terminal |
| Python warns that Python 3.9 is end-of-life | Harmless; the commands' `-W ignore` hides it |
| "no such file or directory" for a command you stored in a shell variable | zsh doesn't split a variable into words (`G="python script.py"; $G list` fails). Write the command out in full |

**Things we learned about Jira and Drive** (the skills already handle these):

- `acli jira auth login --web` needs keyboard focus in the terminal at the site picker, and is
  blocked at many companies anyway. `--site` works only with `--email` and `--token`.
- Jira search can't return `duedate`: use `acli jira workitem view <KEY> --fields duedate`.
- `acli` can't change a ticket's parent epic after it's created: fix it in the Jira UI, or create
  the ticket again.
- To set the epic link and due date when creating a ticket, `acli jira workitem create
  --from-json` takes `"parentIssueId"` and `"additionalAttributes": {"duedate": "YYYY-MM-DD"}`,
  and the description must be Atlassian Document Format. `scripts/jira_ticket.py` does all of this.
- The Drive helper only sees the Docs it created (the `drive.file` permission working as
  intended). The skills use Glean to read other files in the folder.

## What's in this repo

| Path | What it is |
|---|---|
| `install.sh` | Asks the questions, then installs the skills and the Drive helper's libraries |
| `claude-code/customer-meeting-recap/` | The recap skill: `SKILL.md`, `scripts/jira_ticket.py` (Markdown → Jira ticket), `scripts/gdrive.py` (Drive helper), `scripts/gong_transcript.py` (Gong transcript → readable file), `references/` |
| `claude-code/customer-session-prep/` | The quick prep skill: `SKILL.md` |
| `claude-code/customer-engagement-prep/` | The prep skill with the engagement's history: `SKILL.md` |
| `claude-code/customer-recap-check/` | The automatic recap check: `SKILL.md`, `scripts/recap_check.py` (settings, processed calls, Active Customers Doc, the run log, Slack uploads, Gong emails) |
| `claude-code/customer-shared-notes/` | The Master Engagement Doc skill: `SKILL.md`, `scripts/shared_notes.py` (ledger of recaps already in each Doc); uses the recap skill's Drive helper |

## Rules for this repo

- **No customer data, no links.** No customer names, customer or internal links, account IDs or
  colleagues' names, anywhere: skills, examples, docs or commit messages. Use made-up examples
  (`Acme`, `Alex`, `KEY-123`).
- **No credentials or personal settings.** They live in each person's `~/.config/`. The
  `.gitignore` blocks common credential files and `CLAUDE.md` as a backstop.
- **Edit `claude-code/`, then rerun `./install.sh`.** The installed copies are replaced on every
  install. The master copy uses `{{SKILLS_DIR}}`, `{{CUSTOMERS_DIR}}`, `{{JIRA_SITE}}`,
  `{{JIRA_PROJECT}}` and `{{HISTORY_DRIVE_FOLDER}}` wherever a personal setting goes; keep those placeholders as they are.
