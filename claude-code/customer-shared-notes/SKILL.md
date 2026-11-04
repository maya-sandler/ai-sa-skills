---
name: customer-shared-notes
description: Keep one customer-facing Google Doc of meeting notes per opportunity, the <Customer>-LaunchDarkly Master Engagement Doc, built from the recaps that customer-meeting-recap saved in the opportunity's Drive folder. Stacks one block per meeting, newest on top, and leaves out everything internal (Jira tickets, internal links, internal-only tasks), so the SA can share the Doc with the customer. Also runs unattended after each automatic recap from customer-recap-check, and never adds a meeting twice. Use when the user (a LaunchDarkly Solutions Architect) asks to update, build or refresh the Master Engagement Doc (the shared, customer-facing meeting notes), or to get the recaps ready to share with the customer, usually after a recap and from inside a customer folder like {{CUSTOMERS_DIR}}/<customer>/.
---

# Master Engagement Doc, Shared With the Customer (Claude Code)

You are helping a LaunchDarkly Solutions Architect (SA). Keep **one Google Doc per opportunity**
that the SA shares with the customer: a block for every meeting, **newest meeting on top**. It's
named `<Customer>-LaunchDarkly Master Engagement Doc` and saved in the opportunity's Drive folder.

The SA runs this after `/customer-meeting-recap`, and the `customer-recap-check` skill runs it
automatically after each recap it finishes. Each run adds the meetings the Doc doesn't have yet.

**It only copies.** The only source is the recap Docs in the opportunity's Drive folder. Never
read Gong, Jira or Slack, and never write new content: every line in the Doc comes from a
recap, with the internal parts left out. If a recap is wrong, the SA fixes the recap, then asks
you to refresh that meeting.

**Everything goes to Google Drive.** Write the Markdown in your scratchpad directory, upload it,
then delete it.

**Settings:** customer folders live in `{{CUSTOMERS_DIR}}/`, the skills in `{{SKILLS_DIR}}/`, and
Jira tickets are in project `{{JIRA_PROJECT}}` on `{{JIRA_SITE}}`. If a placeholder in double
curly braces shows instead, follow the "Settings" note in the recap skill.

The Drive helper commands (`save`, `list`, `read`), and what to do if it isn't signed in, are
described in `{{SKILLS_DIR}}/customer-meeting-recap/SKILL.md` under "Drive helper". Always
write the full command:

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore {{SKILLS_DIR}}/customer-meeting-recap/scripts/gdrive.py <command> ...
```

## The ledger: no meeting is added twice

A local ledger, `~/.config/sa-skills/shared-notes.json`, records which recaps are already in
each shared Doc: the shared Doc's ID, each recap's Doc ID, and the recap's Gong call ID. It holds
only IDs. Never edit it by hand; use the helper:

```bash
python3 {{SKILLS_DIR}}/customer-shared-notes/scripts/shared_notes.py ledger <action> ...
```

| Command | Does |
|---|---|
| `ledger check --doc <SHARED_DOC_ID> --recap <RECAP_DOC_ID> [--call <GONG_CALL_ID>]` | `already_there: true` if that recap, or another recap of the same Gong call, is already in the shared Doc |
| `ledger add --doc <SHARED_DOC_ID> --recap <RECAP_DOC_ID> [--call <GONG_CALL_ID>]` | Records that the recap was added. Keeps every other entry |
| `ledger get --doc <SHARED_DOC_ID>` | Every recap recorded for that shared Doc, or `null` |

The Gong call ID is the number after `Gong call ID` on the recap's Recording line. Leave out
`--call` if there isn't one.

**The ledger decides first, headings second.** A recap in the ledger is never added again, even
if the SA changed its heading in the shared Doc, or the recap was updated later (for example,
ticket keys added after a held run): it's the same recap Doc ID. The date-and-title heading match
in Step 3 still applies, for meetings added before the ledger existed, by hand, or on another
computer.

## Unattended mode (automatic runs)

The `customer-recap-check` skill runs this skill after each recap it finishes, with no one
watching. Its prompt starts with `UNATTENDED RUN` and gives the customer folder, the opportunity
name and the new recap's Doc ID. In an unattended run, everything below applies, and it
overrides any step that says to ask the SA:

- **Never ask and never wait.** Where a step says to ask, do what this table says instead.

  | Missing or unclear | What to do |
  |---|---|
  | The customer folder, or an opportunity in `CLAUDE.md` with exactly the name the prompt gives | Write nothing. Return `held`, with the reason |
  | That opportunity's **Drive folder** | Write nothing. Return `held` |
  | **Other opportunities share the Drive folder,** and the entry has no `Master Engagement Doc` line | Write nothing. Return `held`: the Doc needs a label from the SA. Don't make one up |
  | The recap's Opportunity line names another opportunity, or the recap is a test or draft | Write nothing. Return `held` |
  | A grep hit in Step 4 you can't tell is customer-facing | Leave it out, and name it in `reason` |

- **The shared Doc doesn't exist yet:** create it, with all of this opportunity's recaps, as an
  interactive run would.
- **The Doc exists:** add only the recap the prompt names. If the ledger or a heading says it's
  already there, change nothing and return `already_there`.
- **Never refresh a meeting** in an unattended run.
- **Post nothing in chat.** End with the result block below, and nothing after it.

End every unattended run with exactly one block like this:

```text
SHARED_NOTES_RESULT
{"status": "added" | "already_there" | "held" | "error",
 "doc": {"name": "<Doc name>", "link": "<webViewLink>"} | null,
 "meetings_added": ["<YYYY-MM-DD> – <title>"],
 "reason": "<why it was held, already there, or failed; and anything left out in doubt>"}
```

## Step 1: Customer and opportunity

First check the customer's row in the Active Customers Doc, as the recap skill's "Active Customers
Doc" section says: stop if it isn't Active (unattended: return `held` with that reason). Use its
Documentation name for `<Customer>` and its Folder link as the Drive folder.

Read the customer folder's `CLAUDE.md` (`{{CUSTOMERS_DIR}}/<customer>/`). If you aren't in a
customer folder, find the right one under `{{CUSTOMERS_DIR}}/`. If you can't tell which customer
it is, or there's no folder for it, ask the SA. Don't create a folder: with no recaps yet, there
is nothing to copy.

Work out which **opportunity** the Doc is for:

| What you have | What to do |
|---|---|
| The SA names the opportunity, or a Drive folder that belongs to exactly one entry | Use that entry |
| `CLAUDE.md` has exactly one opportunity | Use it, and say which one you used |
| Several opportunities could fit | Ask which, listing them by name |

Take the Drive folder ID from that opportunity's entry. If the entry has no Drive folder, ask
the SA for it. Never use a folder found by searching Glean.

**Doc name.** Use the name saved in the entry's `Master Engagement Doc` line (older entries
call it `Shared meeting notes`), if there is one. Otherwise it's
`<Customer>-LaunchDarkly Master Engagement Doc`, with the customer name written as in the recap
names, so anyone who sees it knows it's shared with the customer. If **other opportunities share
this Drive folder**, the name needs a suffix so each opportunity gets its own Doc: ask the SA for
a short label the customer will recognize (such as the project name), and name it
`<Customer>-LaunchDarkly Master Engagement Doc – <label>`.

## Step 2: Find the recaps

```bash
... gdrive.py list --folder <FOLDER_ID> --contains "Meeting Recap"
```

`read` each one. A recap's date is in its name (`<Customer> – Meeting Recap – <YYYY-MM-DD>`).
Keep only the recaps for this opportunity:

| Recap | Use it? |
|---|---|
| Its **Opportunity** line names this opportunity | Yes |
| It names another opportunity | No |
| It has no Opportunity line (an older recap) | Yes if no other opportunity uses this Drive folder. Otherwise ask the SA |
| Its name marks it as a test or draft, e.g. ends in `(skill test)` | No. Mention it in the report |

In what `read` prints, the Opportunity, Attendees and Recording lines often run together in one
paragraph. The opportunity name is the text after `**Opportunity:**`, up to `**Attendees:**`.

If no recap is left, stop and tell the SA to run `/customer-meeting-recap` first.

**Meeting title,** for each recap, from the first of these that has one:
1. The title at the end of the recap's name (a second meeting that day:
   `… – Meeting Recap – 2026-10-26 – Flag Lifecycle`).
2. The text of the Recording link (the call's title), without the link. Drop a leading customer
   or LaunchDarkly prefix: `Acme <> LD Platform Readiness: Flag Lifecycle` becomes
   `Platform Readiness: Flag Lifecycle`.
3. A few words from the Summary's first bullet.

## Step 3: Read the shared Doc, if it exists

```bash
... gdrive.py list --folder <FOLDER_ID> --contains "Master Engagement Doc"
```

- **No Doc with this name:** you'll create it in Step 5. If a Doc in the list looks like this
  one under a different name (the SA may have renamed it), ask the SA which to use.
- **The Doc exists:** `read` it into a scratchpad file. For each recap, check whether it's
  **already in the Doc**, in this order:
  1. **The ledger:** `ledger check --doc <SHARED_DOC_ID> --recap <RECAP_DOC_ID> [--call <ID>]`.
     If it says `already_there`, skip the recap.
  2. **The headings:** each meeting in the Doc starts with a `## <YYYY-MM-DD> – <title>` heading.
     The recap is already there if a heading has the same date and title (ignore case,
     punctuation and backslashes). If a heading has the same date but another title, and only
     one recap has that date, treat it as the same meeting: the SA probably edited the title.
     Record a recap found this way with `ledger add`, so the next run finds it in the ledger.

**Never rebuild the Doc from scratch.** The SA, or the customer, may have edited it. Keep what
`read` returned, exactly as it is, and only add blocks to it.

If every recap is already in the Doc and the SA didn't ask to refresh a meeting, say so, link the
Doc and stop.

## Step 4: Write a block for each new meeting

Each meeting gets this block, with exactly these sections, in this order:

```
## <YYYY-MM-DD> – <meeting title>

### Summary
### What was discussed
### Artifacts & resources
### Scheduled meetings
### Action items – LaunchDarkly team
| # | Task | Owner | Due |
### Action items – <Customer>
| # | Task | Owner | Due |
### Next steps
```

Copy each section from the recap's section of the same name, with these changes:

| Recap section | In the shared Doc |
|---|---|
| Opportunity, Attendees and Recording lines | Leave out |
| Summary, What was discussed | Copy. Leave out bullets that only make sense inside LaunchDarkly |
| Artifacts & resources | Copy, keeping public links. Drop internal links (see below) |
| Scheduled meetings | Copy |
| Action items – LaunchDarkly team | Copy without the **Jira** column. Leave out internal-only items. Renumber |
| Action items – \<Customer\> | Copy |
| Next steps | Copy. An older recap has **Open questions** instead: use those under the Next steps heading, leaving out any that an action item already covers |
| Previous action items, Customer links | Leave out |

**Leave out everything internal:**
- **Jira:** the Jira column, and any ticket key like `{{JIRA_PROJECT}}-123`.
- **Internal links:** Salesforce, Vitalstatistix, Jira, Slack, the Gong recording and call ID,
  the session plan, the SA handoff, and any other Google Doc or Drive link, unless the recap
  says that file was shared with the customer. Keep confirmed public docs links
  (`https://launchdarkly.com/docs/...`) and other public pages.
- **Internal-only LaunchDarkly tasks,** whose result only LaunchDarkly people see: passing a
  feature request to an internal tool's author, syncing with the AE or CSM, updating Salesforce,
  asking a colleague. Keep every task promised to the customer, and anything the customer will
  receive or see.
- **Internal notes:** `Not found` placeholders, deal or commercial notes (pricing, renewal,
  champion, risk), and remarks about how LaunchDarkly works internally.

Rules:
- Don't reword what you keep. Only leave things out, renumber tables, and rename Open questions
  to Next steps.
- If a section is empty after this, keep its heading and write `None.`
- Use the recap's own name for the customer in the "Action items – \<Customer\>" heading.

Write all the new blocks, newest first, to a scratchpad file (`new-blocks.md`). Then check it
for anything internal you missed:

```bash
grep -n -i -E 'gong|lightning\.force\.com|salesforce|vitalstatistix|atlassian\.net|slack\.com|docs\.google\.com|drive\.google\.com|session plan|handoff|not found|\b{{JIRA_PROJECT}}-[0-9]+' <scratchpad>/new-blocks.md
```

Fix every hit, unless it's something the customer was clearly given in the meeting. Check only
your new blocks, not the SA's text in the existing Doc.

## Step 5: Put the Doc together and save it

**A new Doc** starts with this header, followed by the blocks, newest first:

```
# <Customer>-LaunchDarkly Master Engagement Doc

Shared with <Customer>. Notes from each meeting between <Customer> and LaunchDarkly, newest first.
```

**An existing Doc:** put each new block before the first meeting that's older than it. Usually
that's straight after the header, at the top. Leave the rest of the file untouched.

**Refreshing a meeting** (only when the SA asks, e.g. after fixing a recap): re-read that recap,
write its block again as in Step 4, and replace only the text from that meeting's `##` heading up
to the next `##` heading. Any edits in that block are lost, so say so in the report.

Save under the exact Doc name:

```bash
... gdrive.py save --folder <FOLDER_ID> --name "<Doc name>" --file <scratchpad>/notes.md
```

`save` replaces the Doc's whole content with the Markdown. Text edits survive, because you read
them back first. Formatting Markdown can't hold (colors, images, suggestions) may not, and
comments may lose their place.

**Right after the save works,** record every recap you added, using the shared Doc's ID from the
`save` output:
`ledger add --doc <SHARED_DOC_ID> --recap <RECAP_DOC_ID> [--call <GONG_CALL_ID>]`. A refreshed
meeting is already in the ledger. If the save failed, record nothing.

Then delete the scratchpad files you created.

## Step 6: Report, and keep CLAUDE.md current

Add the Doc to this opportunity's entry in `CLAUDE.md`, if it isn't there yet:
`- Master Engagement Doc: <Doc name> (<webViewLink>)`. Don't change anything else in the file.

In an unattended run, end with the `SHARED_NOTES_RESULT` block instead. In chat:
1. The Doc link (`webViewLink`), and whether it was created or updated.
2. The meetings added (`<date> – <title>`), or refreshed.
3. What you left out as internal, one line per meeting, so the SA can check it. Also any recaps
   you skipped, and why.
4. A reminder: **review the Doc, then share it with the customer yourself.** In the Doc, click
   **Share** and add the customer's people. The Drive helper can't change sharing, so the Doc stays
   private to the SA until they do.
