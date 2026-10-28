---
name: customer-meeting-recap
description: Turn a LaunchDarkly customer meeting (Gong/Zoom recording, transcript or notes) into a recap saved as a Google Doc in the customer's Drive folder, and create my follow-up Jira tickets with acli under the customer's epic in your Jira project ({{JIRA_PROJECT}}). Use when the user (a LaunchDarkly Solutions Architect) asks to recap, summarize or "close out" a customer call, pull action items or next steps from a meeting, or create Jira tasks from a meeting, usually from inside a customer folder like {{CUSTOMERS_DIR}}/<customer>/.
---

# Customer Meeting Recap + Jira Tickets (Claude Code)

You are helping a LaunchDarkly Solutions Architect (SA). Produce:

1. **A meeting recap**, saved as a Google Doc in the customer's Drive folder and posted in chat.
2. **Jira tickets** for every task the SA owns, under the customer's epic in Jira project `{{JIRA_PROJECT}}`, created with `acli`.

Don't stop for approval before creating tickets: create them, then list them. The SA will
ask for edits afterwards.

**Everything you produce goes to Google Drive, never to the local customer folder.** The only
local file is the customer folder's `CLAUDE.md` (links, epic key, team). Write temporary files
(Markdown to upload, ticket descriptions) in your scratchpad directory, and delete them when
you're done.

**Settings:** customer folders live in `{{CUSTOMERS_DIR}}/`, the skills in `{{SKILLS_DIR}}/`, and
tickets go to Jira project `{{JIRA_PROJECT}}` on `{{JIRA_SITE}}`. `install.sh` filled these in
from the SA's answers, which are saved in `~/.config/sa-skills/config.json`. If any of them
still shows a placeholder in double curly braces, the skill was copied by hand. In that case,
read `customers_dir`, `skills_dir`, `jira_site` and `jira_project` from that config file if it
exists. Otherwise ask the SA for them (suggest `~/work/customers` for the folders), and tell
them to run `install.sh` from their clone of the `ai-sa-skills` repo so this is set for good.

## Drive helper

Every Drive command has this form. Write it out in full each time: putting it in a shell
variable breaks under zsh.

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore {{SKILLS_DIR}}/customer-meeting-recap/scripts/gdrive.py <command> ...
```

| Command | Does |
|---|---|
| `save --folder <FOLDER_ID> --name "<Doc name>" --file <file.md>` | Creates a Google Doc from Markdown, or updates the Doc already saved under that name. Prints `webViewLink` |
| `list --folder <FOLDER_ID> [--contains "<text>"]` | Docs this helper created in the folder, newest first |
| `read --id <DOC_ID>` | Prints a Doc as Markdown |

The folder ID is the last part of the Drive folder URL in `CLAUDE.md`. The helper only sees
Docs it created itself (Google's `drive.file` permission). Use Glean to read anything else
in the folder.

If it prints `not signed in to Google Drive`, stop and tell the SA to run the same command
with `login` in their terminal. Never read `~/.config/sa-skills/google/` (client secret and
token).

## Unattended mode (automatic runs)

The `customer-recap-check` skill runs this skill on its own, with no one watching. Its prompt
starts with `UNATTENDED RUN` and gives the Gong link and call ID, the transcript file it already
made (Step 2), the customer's folder, the meeting title and date. In an unattended run,
everything below applies, and it overrides any step that says to ask the SA:

- **Never ask and never wait.** The check asks the SA in Slack for you. Where Step 1 says to ask,
  do what this table says instead.

  | Prompt starts with | Links still missing after Step 1.3 | What to do |
  |---|---|---|
  | `UNATTENDED RUN` | The Drive folder (with or without other links) | Stop before writing anything: there's nowhere to save the recap. Return `held` with every missing link in `needs`, and one `question` asking for all of them |
  | `UNATTENDED RUN` | Only Salesforce, Vitalstatistix, session plan, Slack channels, or which opportunity / a new opportunity | Don't wait for them. Write `Not found` for them, and finish. Return `done` with `missing` naming them, and one `question` asking for all of them |
  | `UNATTENDED RUN, RESUME` (gives the SA's answer) | Whatever the answer didn't give | Save the answer to `CLAUDE.md` (Step 1.5). Still no Drive folder: return `held` again. Otherwise write `Not found` for the rest, and finish. Return `done` with `missing` naming them |
  | `UNATTENDED RUN, NO ANSWER` (a call held by a recap the SA ran by hand) | Salesforce, Vitalstatistix, session plan, Slack channels | Write `Not found` for them, and finish. Return `done` with `missing` naming them |

- **Which opportunity isn't clear, or it looks new:** don't wait, and add no entry to
  `CLAUDE.md`. Write the recap in the Drive folder you have, with `Opportunity: Not found`, and
  `Not found` for the Salesforce, Vitalstatistix and session plan links: never take them from
  another opportunity's entry. Put `opportunity` in `missing`.
- **Never take a link from a Glean or Slack search,** not even as a suggestion. Only the prompt,
  the customer's `CLAUDE.md` and the opportunity's Drive folder count.
- **Tickets:** create them as usual, even when a link is `Not found`. A held run stops before
  writing anything, so it creates none.
- **Transcript:** use the transcript file the prompt gives. If there's none, make it as Step 2
  says; if the call has no transcript yet, return `waiting` before writing anything.
- **Don't post the recap in chat.** End with the result block below, and nothing after it.

End every unattended run with exactly one block like this:

```text
RECAP_RESULT
{"status": "done" | "held" | "waiting" | "error",
 "gong_call_id": "<id>",
 "opportunity": "<opportunity name from CLAUDE.md, or Not found>",
 "recap": {"name": "<Doc name>", "id": "<Doc ID>", "link": "<webViewLink>"} | null,
 "tickets": [{"key": "KEY-123", "title": "Alex: …", "link": "<url>"}],
 "needs": ["drive_folder" | "opportunity" | "new_opportunity" | "salesforce" | "vitalstatistix" | "session_plan" | "slack_channels"],
 "missing": ["opportunity" | "salesforce" | "vitalstatistix" | "session_plan" | "slack_channels"],
 "question": "<one message for the SA listing every missing link, if held, or done with missing>",
 "error": "<what failed, if error>"}
```

A `RESUME` or `NO ANSWER` run finishes the call: write the recap if none was saved, and create
any tickets not created yet, adding their keys to the recap's Jira column.

## Active Customers Doc (every customer skill)

The SA keeps an **Active Customers** Google Doc: one row per customer, with Customer,
Documentation name, Folder link, Salesforce opportunity, Slack channels, Gong account and Status. All the customer skills
(`customer-meeting-recap`, `customer-session-prep`, `customer-engagement-prep`,
`customer-shared-notes`, `customer-recap-check`) read it first, and **work only on customers
whose Status is Active** (any case), so old customers are left alone.

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore {{SKILLS_DIR}}/customer-recap-check/scripts/recap_check.py customers read --folder <sa_drive_folder> --customer "<customer>"
```

`sa_drive_folder` is in `~/.config/sa-skills/config.json` (`recap_check.py config get
sa_drive_folder`). The command prints the row, or `"customer": null` if it isn't in the Doc.

| Result | What to do |
|---|---|
| `active: true` | Carry on, using the row as below |
| The row's Status is anything else, or `"customer": null` | Stop before reading or writing anything. Tell the SA: "<Customer> isn't marked Active in your Active Customers Doc (<doc link>). Mark it Active, or add a row, and run me again." In an unattended run, return `error` with that reason |
| `sa_drive_folder` is empty, or the Doc doesn't exist yet | Carry on with `CLAUDE.md` alone, and say once that the Active Customers Doc isn't set up ("set up the recap check" creates it) |

**Using the row.** Its values come from the SA, so they count like the SA's own answer:

- **Documentation name** (`documentation_name`, already the Customer value when blank): the
  customer's name in every Doc name and heading, in place of `<Customer>`.
- **Folder link:** the Drive folder where this customer's recaps and prep briefs live. It's the
  Drive folder of the opportunity being worked on: the `CLAUDE.md` entry that has this folder.
  If no entry has it, and `CLAUDE.md` has no opportunity or exactly one without a Drive folder,
  write it into that entry (or a new one). If other entries have other folders, ask which
  opportunity it is (unattended: don't wait; see "Unattended mode").
- **Salesforce opportunity** (`salesforce_link`): the opportunity being worked on now. It
  picks the `CLAUDE.md` entry that has this link, before the Folder link does. If no entry has
  it, and `CLAUDE.md` has no opportunity or exactly one without a Salesforce link, write it into
  that entry (or a new one). Otherwise it's a new opportunity: Step 1 says what to do
  (unattended: see "Unattended mode").
- **Slack channels:** the channels and chats to read for context. Copy them into `CLAUDE.md`'s
  **Slack** section; `none` means there are none. They're never named in a Doc or ticket.
- **Local folder** (`local_folder`): the customer's folder is `{{CUSTOMERS_DIR}}/<local_folder>/`.

When the row and `CLAUDE.md` disagree, the row wins: update `CLAUDE.md` to match. A link the row
leaves blank is still taken from `CLAUDE.md`, or asked for as Step 1 says.

## Step 1: Customer context

First check the customer's row in the Active Customers Doc (above): stop if it isn't Active, and
use its links.

The session usually runs in the customer folder (`{{CUSTOMERS_DIR}}/<customer>/`). Its
`CLAUDE.md` has the customer name, epic key, team, and an **Opportunities** list: one entry per
Salesforce opportunity, each with its own links (Drive folder, Vitalstatistix, session plan).
Its **Slack** section lists the customer's Slack channels and chats. If you aren't in a customer
folder, find the right one under `{{CUSTOMERS_DIR}}/`.

**If there's no folder for this customer, create it now:** make
`{{CUSTOMERS_DIR}}/<customer-slug>/` (lowercase, hyphens, e.g. `acme-corp`) containing just a
`CLAUDE.md` from `references/customer-folder-template.md`. Fill in the customer name, the SA
(from the `acli` sign-in, marked SA in the Team list), and whatever the prompt gave you. Leave
everything else as placeholders; the rest of this run fills it in (see "Keep CLAUDE.md current"
at the end).

### Links belong to one opportunity

A customer can have **several opportunities**: RSA50, then RSA100, then a second RSA50. Each
has **its own links**: Salesforce opportunity, Drive folder, Vitalstatistix and session plan.
Some may be shared, such as one Drive folder for two opportunities. A link from the wrong
opportunity is worse than no link, so:
- **Never copy links from one opportunity to another without asking.**
- **Never search Glean for these links and use the result on your own.**

In `CLAUDE.md`, each opportunity is a `###` entry under **Opportunities**, named
`<Offering> opportunity (<n>)`, e.g. `RSA50 opportunity (1)`, `RSA100 opportunity`,
`RSA50 opportunity (2)`. Add the number when the same offering repeats. The Salesforce
opportunity link is what makes an opportunity unique.

**1. Work out which opportunity this run is for.**

| What the prompt has | What to do |
|---|---|
| A Salesforce opportunity link that's already in an entry | Use that entry |
| A Salesforce opportunity link that's **in no entry** | It's a **new opportunity**: go to step 2 |
| The SA says it's a new opportunity, or names an offering with no entry | New opportunity: go to step 2 |
| An opportunity name, or a Drive folder that belongs to exactly one entry | Use that entry |
| A Drive folder shared by several entries, or nothing, with several entries in `CLAUDE.md` | Ask which opportunity, listing them by name, plus "a new one" |
| Nothing, and `CLAUDE.md` has exactly one entry | Use it, and say which one you used |
| Nothing, and there's no entry yet | New opportunity: go to step 2 |

**2. New opportunity: add an entry and ask about every link.** Add an entry under
Opportunities with the name (ask the SA to confirm it, suggesting `<Offering> opportunity (<n>)`)
and the Salesforce link, if you have it. Then ask **one** question covering every link the
prompt didn't give: Salesforce opportunity, Drive folder, Vitalstatistix, session plan, plus
the customer's Slack channels if `CLAUDE.md` has none (see step 4). For each link, offer to reuse an existing opportunity's link (show it), or to have the SA give a new
one. For example:

> New opportunity: **RSA100 opportunity**. For each link, reuse one or send a new one:
> - **Drive folder:** reuse RSA50 opportunity (1)'s Drive folder, or a new folder?
> - **Vitalstatistix:** reuse RSA50 opportunity (1)'s Vitalstatistix link, or a new account?
> - **Session plan:** a new link, or skip?

Wait for the answer before saving anything to Drive or creating tickets.

**3. Existing opportunity: fill in missing links from its own sources.** For each link the
entry doesn't have, stop at the first source that has it:
1. The SA's prompt.
2. The **Customer links** section of the newest recap in the opportunity's Drive folder **that
   names this opportunity** (`list --folder <ID> --contains "Meeting Recap"`, then `read`).
   Skip recaps for other opportunities in a shared folder.
3. Docs in that Drive folder. Read them with Glean `search` with `container_filter` set to the
   folder URL; the SA handoff doc's "Sources" usually links the opportunity.

**4. Still missing? Ask once, then wait.** Before you create the recap Doc or any ticket, ask
the SA for **every** missing link in **one** message, naming the opportunity:
- Drive folder, Salesforce opportunity, Vitalstatistix and session plan, if this opportunity's
  entry doesn't have them;
- the customer's **Slack channels and chats**, if neither the Active Customers row nor
  `CLAUDE.md` has them: the shared
  customer channel, an internal account channel, group DMs. Ask for each one's link (in Slack:
  right-click it → Copy link).

For example:

> Missing links for **Acme, RSA50 opportunity (1)**. Send any you have, or say skip:
> - **Salesforce opportunity**
> - **Session plan**
> - **Slack:** the shared Acme channel, an internal Acme channel, any group DMs (or "none")

Read the transcript while you wait, but don't save anything to Drive or create tickets until the
SA answers. You may suggest Salesforce or Vitalstatistix candidates you found in Glean (see
`references/sources.md`), but present them as a question ("Is this the right opportunity?"),
and use one only after the SA confirms it.

**Ask in chat and in the SA's Slack self-DM.** Post the same question to the self-DM, so the SA
can answer from Slack too:

1. The self-DM is `slack_dm_channel` in `~/.config/sa-skills/config.json`. If it's empty, find it
   as the `customer-recap-check` skill's "Slack self-DM" section says, and save it. Never post
   anywhere else. If Slack isn't available, ask in chat only, and say so.
2. Post it as that section's "To post" steps describe, starting
   "*<Customer>* recap waiting: <the question> Reply in this thread." Keep the post's `ts`.
3. If the call has a Gong call ID, record it, so the hourly recap check takes over if the SA
   answers in Slack or not at all:
   `recap_check.py calls mark --id <call ID> --status held --customer <Customer> --date <YYYY-MM-DD> --title "<meeting title>" --url <Gong link> --note <missing, comma-separated: drive_folder, opportunity, new_opportunity, salesforce, vitalstatistix, session_plan, slack_channels> --slack-ts <ts> --reminded <today>`
   (full helper command in that skill's "Helpers").
4. In chat, say the question is also in the self-DM, and that the SA can answer in either place.
   If they answer in Slack, they tell you "check Slack", and you read the thread
   (`slack_read_thread`, replies from `slack_user_id` only).

When the SA answers in chat or Slack, first run `calls get --id <call ID>`. If it's `done`, the
check has already made the recap with `Not found`: save the answer to `CLAUDE.md`, fill in that
recap's Customer links (`read` it into the scratchpad, edit, `save` under its exact name), and
create no new Doc or tickets. Otherwise carry
on, and when you finish, run `calls mark --id <call ID> --status done --missing <still missing,
or none>` and reply in the Slack thread with the recap link, so the check doesn't recap it again.

**Never work out Slack channels yourself:** don't search Slack or Glean for them, and don't
guess from channel names. Only the SA's answer counts.

If the SA answers without some links, or says skip, write `Not found` for them and carry on. At
the end, list the links still needed. If the SA says a link doesn't exist (e.g. "no shared
channel"), write `none` for it in `CLAUDE.md`, so later runs don't ask again.

**5. Save what you learned.** Write each link from the prompt, the folder or the SA's answer
into **this opportunity's** entry in `CLAUDE.md`, and Slack channels into its **Slack** section.
The next run then needs no questions. Slack channels are only for reading (Step 3): never write
their names or links into a Doc or ticket.

The epic and team are per customer, not per opportunity. Take them from `CLAUDE.md`, or find
the epic in Step 5.

Also ask the SA if you can't tell which customer this is, or there's no source for the
meeting content.

## Step 2: Get the full transcript

Write the recap **only from the call's full transcript** (or the SA's own notes). Never use
Gong's "call is ready" email or its Key points, Gong's call summary, or Glean search snippets as
the source: they leave things out.

Use the first one that works:

1. A transcript or notes the SA pasted, or a file they named.
2. A Gong link (`https://<host>.app.gong.io/call?id=<id>`). Drop everything after the `id`
   (Gong's tracking), then Glean `read_document` on that link. If you don't have the link, find
   the call with Glean `search` (`app: gong`, the customer name or call title), and read it.
   The result is usually saved to a file because it's large; if it came back inline, write it to
   a scratchpad file. Then turn it into a readable transcript:

   ```bash
   python3 {{SKILLS_DIR}}/customer-meeting-recap/scripts/gong_transcript.py --file <saved result> --out <scratchpad>/transcript.txt
   ```

   It writes one `[HH:MM:SS] speaker: text` line per utterance, timed from the start of the call,
   and prints the number of utterances, the length in minutes and each speaker. Read the whole
   file. Gong's own summary, also in the result, is left out on purpose.
3. If none of these works, ask the SA to paste the transcript. If the call isn't in Glean yet,
   say so: Gong takes a while after the call.

**Speakers.** LaunchDarkly people show as their email: use their names from `CLAUDE.md`'s Team
list, or Glean `employee_search`. Some external speakers show only as `Speaker <6 hex
characters>`. Work out who they are from the transcript (introductions, people addressing each
other) and from Glean: `search` with `app: gong` for the call title shows snippets like
`Name: <words>` (find those words in the transcript to see whose hash it is) and the call's
external participants. Then rerun the helper with `--speaker '<hash>=<Name>'` for each one
(quote it). Mark a name you're unsure of, e.g. `--speaker 'A1B2C3=Sam (unsure)'`, and keep the
mark in the recap's Attendees line. Leave one you can't tell as `Speaker <hash>`.

Note the meeting date, title and attendees (theirs and ours). If the transcript was pasted
(rather than in Gong), save it to Drive as `<Customer> – Transcript – <YYYY-MM-DD> – <short title>`
so the prep skill can use it later.

## Step 3: Read what came before

- **Earlier recaps:** run `list --folder <ID> --contains "Meeting Recap"`, then `read` the newest one.
- **Session plan and other docs:** use Glean `search` with `container_filter` set to the Drive folder URL.
- **The customer's Slack channels,** if `CLAUDE.md` lists them: `slack_read_channel` on each
  one's ID (the part of its link after `/archives/`), with `oldest` set to the previous call's
  date as a Unix timestamp (`date -j -f %Y-%m-%d <date> +%s`; the last 14 days if there's no
  previous call). Read threads with `slack_read_thread` where the replies matter. Look for
  follow-ups, questions, items someone promised, and decisions. Read no other channel.

Use them to tell what's new and to mark earlier action items as done or still open. Use what
the Slack channels add in the recap and its action items, in your own words. **Never name or
link a Slack channel** in the recap or a ticket; write "on Slack" if you need to say where
something came from.

## Step 4: Write the recap

Use this structure. Keep each bullet to one line, and be specific: name flags, SDKs,
environments, numbers and people.

```
# <Customer> – Meeting Recap – <YYYY-MM-DD>
**Opportunity:** <opportunity name from CLAUDE.md, e.g. RSA50 opportunity (1)>
**Attendees:** <customer people (role)> · <LaunchDarkly people (role)>
**Recording:** <Gong/Zoom link> (Gong call ID <id>)

## Summary
3–5 bullets: goal of the call, where the engagement stands, the most important outcome.

## What was discussed
Topic-by-topic bullets, including decisions made.

## Artifacts & resources
- Things shown or shared (demos, decks, code, diagrams), with links.
- LaunchDarkly docs relevant to what was discussed: confirmed `https://launchdarkly.com/docs/...` links only.

## Scheduled meetings
| Date (with timezone) | Meeting | Attendees | Purpose |

## Action items – LaunchDarkly team
| # | Task | Owner | Due | Jira |
## Action items – <Customer>
| # | Task | Owner | Due |

## Next steps
What happens next that isn't already an action item: their questions we still need to answer,
questions we have for them, decisions still to make. Nothing that's in either Action items table.

## Previous action items
Items from the last recap, each marked ✅ done / ⏳ still open.

## Customer links
- Opportunity: <opportunity name>
- Salesforce opportunity: <url>
- Drive folder: <url>
- Vitalstatistix: <url>
- Jira epic: <KEY and url>
- Sales / PS team: <AE>, <SA>, <CSM>, <PS>
- Session plan: <url or "Not found">
```

Always fill in the **Customer links** section with this opportunity's links from Step 1. Write
`Not found` only for a link the SA skipped or didn't give. Slack channels never go here. The next recap and prep brief for this
opportunity read their links from it; the Opportunity line tells them which opportunity a recap
belongs to when several share a Drive folder.

Rules:
- Turn relative dates ("next Tuesday") into absolute dates, using the meeting date.
- If the call doesn't give a due date, use `TBD`. Don't make one up.
- **Next steps** never repeat an action item. If something has an owner and a task, it goes in
  an Action items table, not here.
- **LaunchDarkly team** items are anything someone at LaunchDarkly committed to: the SA, the AE,
  a specialist, PS, or "we" in general. The **Owner** is the person who said they'd do it, by
  first name. If it was "we" or unclear, the owner is the SA. Every LaunchDarkly team item gets a
  Jira ticket. Customer items don't.
- **Docs links:** find pages with the LaunchDarkly MCP `search-docs` / `get-doc` tools, or
  WebFetch on `launchdarkly.com/docs`. Include a link only after you've confirmed the page
  exists.

## Step 5: Find or create the epic (acli)

If `CLAUDE.md` already has an epic key, use it. Otherwise search:

```bash
acli jira workitem search --jql 'project = {{JIRA_PROJECT}} AND issuetype = Epic AND summary ~ "<Customer>"' --fields key,summary --json
```

If no epic matches the customer name (ignoring case), create one. The summary is the
customer name in **Title Case**, keeping the brand's own casing (e.g. `Acme`, `BrightPath`, `iZeta`):

```bash
python3 {{SKILLS_DIR}}/customer-meeting-recap/scripts/jira_ticket.py \
  --project {{JIRA_PROJECT}} --type Epic --summary "<Customer>" --description-file <scratchpad>/epic.md
```

Then write the epic key into the customer folder's `CLAUDE.md`.

If `acli` reports `unauthorized`, stop. Tell the SA the API token has expired or been
revoked, and that they need to rerun
`acli jira auth login --site {{JIRA_SITE}} --email <email> --token < ~/.config/acli/token.txt`
with a new token. Never read or print the token file.

## Step 6: Create the tickets

First list the open tickets under the epic, so you don't create duplicates:

```bash
acli jira workitem search --jql 'parent = <EPIC> AND statusCategory != Done' --fields key,summary,status --json
```

For each LaunchDarkly team action item that doesn't already have a ticket, write the
description to a scratchpad `.md` file using the template below, then run:

```bash
python3 {{SKILLS_DIR}}/customer-meeting-recap/scripts/jira_ticket.py \
  --project {{JIRA_PROJECT}} --summary "<Owner>: <Short Task In Title Case>" \
  --description-file <scratchpad>/<file>.md --parent <EPIC> [--due YYYY-MM-DD] [--unassigned]
```

**Assignee:**
- **The SA's own task:** omit `--unassigned`, and the script assigns it to the SA. The SA is the
  person signed in to `acli`; their name is in `CLAUDE.md`'s Team list, marked SA.
- **Anyone else's task:** pass `--unassigned`, and the ticket is created with no assignee. Don't
  assign it to the owner either: that would notify them, and they may not have access to the
  project. The owner's name at the start of the title shows whose it is.

The script converts the Markdown for Jira and prints the key, URL and assignee. If it prints
`warnings` (parent or due date not set), pass them on to the SA.

Summary rules:
- **Format:** `<Owner first name>: <task>`. The owner is the person doing it, so the SA can
  see at a glance which tickets they only need to follow up on. Use the SA's own first name for
  their tasks.
- **No customer name:** the epic already says which customer it's for.
- **As short as possible:** start with a verb, use Title Case, and aim for under 60 characters.
  Drop filler words ("if", "whether", "the", "a", "do") and anything the description already says.
- **Example:** `Alex: Confirm Big Segments Need Persistent Store`, not
  `Acme: Confirm If The Big Segments Need A Persistent Store`.

Description template (keep these exact headings):

```
## The ask
<One or two sentences: what to do.>

## Background
<What happened in the meeting that led to this, with the meeting date and the people involved.>

## Why it matters
<Why the customer needs this: the business or technical outcome it unlocks.>

## Definition of done
<One short sentence.>

## Customer links
- Opportunity: <opportunity name> (Salesforce: <url>)
- Drive folder: <url>
- Sales / PS team: <AE>, <CSM>, <PS>, ...
- Vitalstatistix: <url>
- Source meeting: <Gong/Zoom link> (<YYYY-MM-DD>)
```

If a link is missing, write `Not found` instead of removing the line. Never add a Slack channel.

## Step 7: Save to Drive and report

1. Fill in the recap's Jira column with the new ticket keys, then save it:
   `save --folder <ID> --name "<Customer> – Meeting Recap – <YYYY-MM-DD>" --file <scratchpad>/recap.md`.
   Before saving, check `list --folder <ID> --contains "Meeting Recap – <YYYY-MM-DD>"`:
   - **A recap for the same date already names this Gong call ID** on its Recording line: it's
     the same call, so update that Doc (save under its exact name).
   - **It names a different call:** this is a second meeting that day, so name this one
     `<Customer> – Meeting Recap – <YYYY-MM-DD> – <meeting title>`, and neither overwrites the other.
2. Delete the scratchpad files you created.
3. In chat, link the recap Doc first (its `webViewLink`), then post the full recap and a ticket list:
   `- [KEY-123](https://{{JIRA_SITE}}/browse/KEY-123) Alex: …`
   Also say whether the epic was found or newly created.
4. If any link is still `Not found`, end by listing the links still needed, so the SA can send
   them for next time.

## Keep CLAUDE.md current

Before you finish, update the customer's `CLAUDE.md` with what this run learned, so the next
run starts with it. Edit it in place: update existing lines, don't add duplicates, and keep it
short. It's an address book, not notes; meeting content belongs in the Drive recap.

| Section | Add or update |
|---|---|
| Customer-wide | The epic key, if it's new |
| Opportunities → this opportunity | Its Salesforce opportunity, Drive folder, Vitalstatistix and session plan or handoff link (only from the sources Step 1 allows). A new opportunity gets a new entry; never overwrite another opportunity's links |
| Slack | The customer's channels and chats, only from the SA's answer: what each is, its link and ID, or `none` |
| Team | New attendees from this call, both sides, as `Name (role)`; fix a role if the call made it clearer. Keep the SA marked SA |
| Calls | This call's recording link and date, as the latest call |
| Tech stack | Facts confirmed on the call (SDKs, languages, warehouse, infra, integrations) |

In chat, list in one line what you added or changed. If you created the folder during this run,
say so and suggest the SA start future sessions for this customer in
`{{CUSTOMERS_DIR}}/<customer-slug>/`.
