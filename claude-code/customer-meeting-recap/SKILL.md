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

## Step 1: Customer context

The session usually runs in the customer folder (`{{CUSTOMERS_DIR}}/<customer>/`). Its
`CLAUDE.md` has the customer name, epic key, team, and an **Opportunities** list: one entry per
Salesforce opportunity, each with its own links (Drive folder, Vitalstatistix, session plan).
If you aren't in a customer folder, find the right one under `{{CUSTOMERS_DIR}}/`.

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
prompt didn't give: Salesforce opportunity, Drive folder, Vitalstatistix, session plan. For
each one, offer to reuse an existing opportunity's link (show it), or to have the SA give a new
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

**4. Still missing? Ask once.** Ask the SA for **all** the missing links in **one** message,
naming the opportunity. Do it at the start, while you work on the transcript: don't create any
tickets until you have the answer. You may suggest candidates you found in Glean (see
`references/sources.md`), but present them as a question ("Is this the right opportunity?").
Use one only after the SA confirms it. If the SA says to skip a link, write `Not found`.

**5. Save what you learned.** Write each link from the prompt, the folder or the SA's answer
into **this opportunity's** entry in `CLAUDE.md`. The next run then needs no questions.

The epic and team are per customer, not per opportunity. Take them from `CLAUDE.md`, or find
the epic in Step 5.

Also ask the SA if you can't tell which customer this is, or there's no source for the
meeting content.

## Step 2: Get the meeting content

Use the first one that works:

1. A transcript or notes the SA pasted, or a file they named.
2. A Gong link (`app.gong.io/call?id=...`). Use Glean `read_document` with the URL, or Glean
   `search` with `app: gong` for the customer name or call title.
3. If none of these works, ask the SA to paste the transcript.

Note the meeting date, title and attendees (theirs and ours). If the transcript was pasted
(rather than in Gong), save it to Drive as `<Customer> – Transcript – <YYYY-MM-DD> – <short title>`
so the prep skill can use it later.

## Step 3: Read what came before

- **Earlier recaps:** run `list --folder <ID> --contains "Meeting Recap"`, then `read` the newest one.
- **Session plan and other docs:** use Glean `search` with `container_filter` set to the Drive folder URL.

Use them to tell what's new and to mark earlier action items as done or still open.

## Step 4: Write the recap

Use this structure. Keep each bullet to one line, and be specific: name flags, SDKs,
environments, numbers and people.

```
# <Customer> – Meeting Recap – <YYYY-MM-DD>
**Opportunity:** <opportunity name from CLAUDE.md, e.g. RSA50 opportunity (1)>
**Attendees:** <customer people (role)> · <LaunchDarkly people (role)>
**Recording:** <Gong/Zoom link>

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

## Open questions
Their questions we still need to answer, plus questions we have for them.

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
`Not found` only for a link the SA chose to skip. The next recap and prep brief for this
opportunity read their links from it; the Opportunity line tells them which opportunity a recap
belongs to when several share a Drive folder.

Rules:
- Turn relative dates ("next Tuesday") into absolute dates, using the meeting date.
- If the call doesn't give a due date, use `TBD`. Don't make one up.
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
customer name in **Title Case**, keeping the brand's own casing (e.g. `Acme`, `GitHub`, `eBay`):

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

If a link is missing, write `Not found` instead of removing the line.

## Step 7: Save to Drive and report

1. Fill in the recap's Jira column with the new ticket keys, then save it:
   `save --folder <ID> --name "<Customer> – Meeting Recap – <YYYY-MM-DD>" --file <scratchpad>/recap.md`
2. Delete the scratchpad files you created.
3. In chat, link the recap Doc first (its `webViewLink`), then post the full recap and a ticket list:
   `- [KEY-123](https://{{JIRA_SITE}}/browse/KEY-123) Alex: …`
   Also say whether the epic was found or newly created.

## Keep CLAUDE.md current

Before you finish, update the customer's `CLAUDE.md` with what this run learned, so the next
run starts with it. Edit it in place: update existing lines, don't add duplicates, and keep it
short. It's an address book, not notes; meeting content belongs in the Drive recap.

| Section | Add or update |
|---|---|
| Customer-wide | The epic key, if it's new |
| Opportunities → this opportunity | Its Salesforce opportunity, Drive folder, Vitalstatistix and session plan or handoff link (only from the sources Step 1 allows). A new opportunity gets a new entry; never overwrite another opportunity's links |
| Team | New attendees from this call, both sides, as `Name (role)`; fix a role if the call made it clearer. Keep the SA marked SA |
| Calls | This call's recording link and date, as the latest call |
| Tech stack | Facts confirmed on the call (SDKs, languages, warehouse, infra, integrations) |

In chat, list in one line what you added or changed. If you created the folder during this run,
say so and suggest the SA start future sessions for this customer in
`{{CUSTOMERS_DIR}}/<customer-slug>/`.
