---
name: customer-internal-notes
description: Turn the SA's own notes from an internal LaunchDarkly meeting about a customer (only LD people, often on Zoom with no recording) into a block in the customer's ongoing internal notes Google Doc, "<Customer> – Internal Notes", in the customer's Drive folder, newest meeting on top, and create Jira tickets under the customer's epic for the LD action items (the SA's own assigned to the SA, anyone else's unassigned with the owner's name). Never customer-facing. Use when the user (a LaunchDarkly Solutions Architect) runs /customer-internal-notes, or pastes notes from an internal sync, internal connect or account team meeting and asks to write them up, add them to the internal notes, or make tickets from them, usually from inside a customer folder like {{CUSTOMERS_DIR}}/<customer>/.
---

# Customer Internal Notes (Claude Code)

You are helping a LaunchDarkly Solutions Architect (SA) keep **one internal notes Doc per
customer**: a running record of the internal meetings about that customer (with the AE, SE, CSM,
PS or a specialist), where there's no recording to recap. The SA writes their own notes, pastes
them in chat, and this skill:

1. Adds a block for the meeting to `<Customer> – Internal Notes` in the customer's Drive folder,
   **newest meeting on top**, creating the Doc the first time.
2. Creates a Jira ticket under the customer's epic for each LD action item in the notes.

**It's internal only.** Never add any of it to the customer-facing Master Engagement Doc
(`customer-shared-notes`), never post it to Slack, and never write it into a customer recap.

**Settings:** customer folders live in `{{CUSTOMERS_DIR}}/`, the skills in `{{SKILLS_DIR}}/`, and
Jira tickets are in project `{{JIRA_PROJECT}}` on `{{JIRA_SITE}}`. If a placeholder in double
curly braces shows instead, follow the "Settings" note in the recap skill.

The Drive helper (`save`, `list`, `read`), the Active Customers Doc check, the epic and ticket
commands, and "Keep CLAUDE.md current" are all described in
`{{SKILLS_DIR}}/customer-meeting-recap/SKILL.md`. Follow them as written there; this skill only
says where it differs. Always write the full Drive helper command:

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore {{SKILLS_DIR}}/customer-meeting-recap/scripts/gdrive.py <command> ...
```

Write every file you make (the block, ticket descriptions, the Doc) in your scratchpad, and
delete them at the end. Nothing goes in the local customer folder except `CLAUDE.md` updates.

## Step 1: Customer, folder and meeting

1. **Active Customers Doc.** Check the customer's row, as the recap skill's "Active Customers
   Doc" section says. Stop if it isn't Active. Use its Documentation name for `<Customer>` and its
   Folder link.
2. **Customer folder.** Read `{{CUSTOMERS_DIR}}/<local_folder>/CLAUDE.md` for the epic key, the
   team (the SA is marked SA) and the opportunity's links. If there's no folder, create it as the
   recap skill's Step 1 says.
3. **Drive folder.** The folder the SA gives wins; otherwise the row's Folder link; otherwise the
   opportunity's Drive folder in `CLAUDE.md`. None of them: ask the SA for the folder link before
   writing anything. The folder ID is the part after `/folders/`.
4. **The notes.** The SA pastes them in chat. No notes in the prompt: ask for them, and wait.
   Use only what the notes say.
5. **The meeting.** Its date, title and attendees, in this order: what the SA said, then the SA's
   calendar, then defaults. For the calendar, use the Google Calendar connector's `list_events`
   with `fullText` = the customer's name, on the meeting date (today unless the SA said
   otherwise): take the event whose title names the customer and that the SA didn't decline. Its
   title is the meeting title, and its attendees who accepted (not the SA, not rooms) are the
   attendees, named by display name or `CLAUDE.md`'s Team section. Nothing found: the date is
   today, the title is `Internal sync`, and the attendees are whoever the notes name.

## Step 2: Read what came before

1. `list --folder <ID> --contains "Internal Notes"`. If `<Customer> – Internal Notes` is there,
   `read --id <its ID>` into `<scratchpad>/internal-notes.md`. Keep it exactly as it is, including
   the SA's own edits: you only add a block at the top.
2. **Same meeting already there?** A block with the same date and title: ask the SA whether to
   replace that block or add a second one (named `<title> (2)`). Never replace one silently.
3. Read the latest recap (`list --folder <ID> --contains "Meeting Recap"`, newest) and the
   latest block in the Internal Notes, to resolve names and items the notes only hint at
   ("Alex's question from last week"). Use them only to clarify the notes, never to add topics.

## Step 3: Write the block

```
## <YYYY-MM-DD> – <meeting title>
**Attendees:** <LD people (role)>
**Source:** <SA first name>'s notes

### Summary
2–4 bullets: why the meeting happened and the main outcome.

### Discussed and decided
Topic-by-topic bullets, including decisions and who made them.

### Action items
| # | Task | Owner | Due | Jira |

### Open questions
What's still undecided or needs an answer, and who it's for. Nothing that's an action item.
```

Rules:
- **Only what the notes say.** Tidy the wording, but add no facts, no topics and no due dates
  the notes don't give (use `TBD`). If a note is unclear, keep the SA's wording and add
  "(unclear in notes)" rather than guessing.
- Turn relative dates ("Thursday") into absolute dates, using the meeting date.
- **Action items** are anything someone committed to, LD or the customer. The **Owner** is that
  person's first name; "we", "I" or unclear means the SA. A customer item (someone at the
  customer will do it) gets `Owner` = their name and no ticket.
- Name the customer and "LD", never "they" or "we". Keep the section headings exactly as above.
- Omit a section only if the notes have nothing for it.

## Step 4: Tickets

1. **The epic:** the key in `CLAUDE.md`, or find or create it as the recap skill's Step 5 says.
2. **No duplicates:** list the open tickets under the epic (`acli jira workitem search --jql
   'parent = <EPIC> AND statusCategory != Done' --fields key,summary,status --json`). An action
   item that already has a ticket gets that key in the Jira column, and no new ticket.
3. **One ticket per LD action item** (not customer items), with the recap skill's
   `jira_ticket.py` command, summary rules (`<Owner first name>: <Short Task In Title Case>`, no
   customer name) and description template. Pass `--due` only for a due date the notes give.
   - **The SA's own item:** assigned to the SA (omit `--unassigned`).
   - **Anyone else's item** (the AE, CSM, PS, a specialist): `--unassigned`, so the owner isn't
     notified. The owner's name at the start of the title shows whose it is, and it sits on the
     SA's board to follow up on.
   - In the description, **Background** says it came from the internal meeting (date, title,
     attendees), and the **Customer links** section's last line is `Source meeting: internal
     notes, <YYYY-MM-DD> (<Customer> – Internal Notes)` instead of a recording link.
4. Fill in each item's Jira column with its key, as a link
   (`[KEY-123](https://{{JIRA_SITE}}/browse/KEY-123)`).

If `acli` reports `unauthorized`, still save the notes (Step 5) with an empty Jira column, and
tell the SA their API token needs to be renewed, as the recap skill says.

## Step 5: Save the Doc

1. Put the Doc together in `<scratchpad>/internal-notes.md`:
   - **New Doc:** the header below, then the block.
   - **Existing Doc:** the new block goes right under the header, above the newest block; the rest
     stays exactly as it was read.

   ```
   # <Customer> – Internal Notes
   Internal only: LaunchDarkly's notes from internal meetings about <Customer>, newest on top. Don't share with <Customer>.
   ```

2. `save --folder <ID> --name "<Customer> – Internal Notes" --file <scratchpad>/internal-notes.md`.
   It updates the Doc if it exists. It stays private to the SA.
3. Delete the scratchpad files.

## Step 6: Report, and keep CLAUDE.md current

In chat: the Doc link (`webViewLink`) first, then the new block as written, then the tickets:
`- [KEY-123](https://{{JIRA_SITE}}/browse/KEY-123) Alex: …` (assigned to you / unassigned).
Say whether the epic was found or newly created, and name any notes you marked unclear.

Then update `CLAUDE.md` as the recap skill's "Keep CLAUDE.md current" says, for what this run
learned (the epic key, LD team members and their roles). Add a line under **Calls** only for
recordings, not for internal notes. List in one line what you changed.
