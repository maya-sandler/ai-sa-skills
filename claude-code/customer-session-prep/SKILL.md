---
name: customer-session-prep
description: Prepare a short pre-meeting brief for an upcoming LaunchDarkly customer session and save it as a Google Doc in the customer's Drive folder. Covers latest status, what I owe the customer this session (from my Jira tickets via acli), their open questions, support tickets they opened, tech stack and where we are in the session plan. Use when the user (a LaunchDarkly Solutions Architect) asks to prep for, get ready for, or brief them on an upcoming customer meeting, session or call, usually from inside a customer folder like {{CUSTOMERS_DIR}}/<customer>/.
---

# Customer Session Prep Brief (Claude Code)

You are helping a LaunchDarkly Solutions Architect (SA) get ready for their next session with
a customer. The goal is a brief they can read in **2 minutes**: one page, bullets, and each item
saying what to *do or say* in the session. Save it as a Google Doc in the customer's Drive
folder and link it in chat.

**Everything you produce goes to Google Drive, never to the local customer folder.** Write the
brief's Markdown in your scratchpad directory, upload it, then delete it.

**Settings:** customer folders live in `{{CUSTOMERS_DIR}}/`, the skills in `{{SKILLS_DIR}}/`, and
Jira tickets are in project `{{JIRA_PROJECT}}` on `{{JIRA_SITE}}`. If a placeholder in double
curly braces shows instead, follow the "Settings" note in the recap skill.

The Drive helper commands (`save`, `list`, `read`), and what to do if it isn't signed in, are
described in `{{SKILLS_DIR}}/customer-meeting-recap/SKILL.md` under "Drive helper". Always
write the full command:

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore {{SKILLS_DIR}}/customer-meeting-recap/scripts/gdrive.py <command> ...
```

## Step 1: Customer context and session date

Read the customer folder's `CLAUDE.md` (`{{CUSTOMERS_DIR}}/<customer>/`) for the epic key,
team and Opportunities list. If you aren't in a customer folder, find the right one under
`{{CUSTOMERS_DIR}}/`. If there's no folder for this customer, create it exactly as the recap
skill's Step 1 describes. The folder ID is the last part of the Drive folder URL.

Work out which **opportunity** the session is for, and get its links, exactly as the recap
skill's Step 1, "Links belong to one opportunity", describes
(`{{SKILLS_DIR}}/customer-meeting-recap/SKILL.md`):
- **Which opportunity:** match the prompt's Salesforce link, opportunity name or Drive folder to
  an entry. If several entries could fit, or none is named, ask which. A Salesforce link that's
  in no entry means a new opportunity.
- **New opportunity:** add an entry, and ask once, for each link, whether to reuse an existing
  opportunity's link or use a new one.
- **Existing opportunity:** fill in missing links from the prompt, then the newest recap for
  this opportunity in its Drive folder, then that folder's other docs. Ask once for anything
  still missing. Glean finds are only suggestions to confirm.
- **Afterwards:** write what you learned into this opportunity's entry in `CLAUDE.md`.

The brief's header names the opportunity:
`**Session:** <#/name> · <topic> · <opportunity name> · <attendees>`.

Find the **upcoming session date and topic** in this order: what the SA said, the "Scheduled
meetings" table in the latest recap, then the session plan. If you can't find the date, say
"next session" and keep going. Don't ask.

## Step 2: Gather (in parallel where possible)

How to reach each source is in `{{SKILLS_DIR}}/customer-meeting-recap/references/sources.md`.

1. **Latest recaps.** Run `list --folder <ID> --contains "Meeting Recap"`, then `read` the newest
   one or two. If there aren't any, look for recap or notes docs in the folder through Glean.
2. **Session plan.** Use Glean `search` with `container_filter` set to the Drive folder URL.
   Work out which session comes next, what it covers, and its success criteria.
3. **My tasks (acli):**
   ```bash
   acli jira workitem search --jql 'parent = <EPIC> ORDER BY status, duedate' --fields key,summary,status --json --paginate
   ```
   Search can't return due dates, so for each ticket that matters run
   `acli jira workitem view <KEY> --fields summary,status,duedate,description --json`.
   - **Done** tickets → *show or explain* in this session. Use the description for the details.
   - **Open** tickets due on or before the session → warn the SA.
4. **Open questions.** Take the "Open questions" from the recaps, plus anything still
   unanswered in the session plan. For each one, give a draft answer or a confirmed
   `launchdarkly.com/docs/...` link (LaunchDarkly MCP `search-docs`).
5. **Support tickets.** Use Glean to find tickets the customer opened (Zendesk, plus Jira
   tickets that mention them). List the open ones and anything from the last 30 days, with
   status and link.
6. **Tech stack.** Use `CLAUDE.md`, earlier recaps, the handoff/discovery docs and Glean:
   languages, LaunchDarkly SDKs (server-side and client-side), Relay Proxy, cloud/infra, data
   warehouse, CI/CD, observability, integrations.
7. **Customer action items.** List the customer's open items from the last recap, to follow up
   on.

Never make up facts. If a source returns nothing, write "None found".

## Step 3: Write the brief

```
# <Customer> – Session Prep – <YYYY-MM-DD of session>
**Session:** <#/name from session plan> · <topic> · <attendees if known>
**Goal for this session:** <one sentence>

## Latest status
- 2–4 bullets: where the engagement is, what last happened, and any risks.

## Deliver in this session
- ✅ <Done task> → show/explain: <what to demo or say> ([KEY-123](https://{{JIRA_SITE}}/browse/KEY-123))
- ⚠️ <Still-open task due by now> → <suggested way to handle it> ([KEY-124](...))

## Their open questions
- <Question> → <draft answer / doc link / "need to find out from X">

## Follow up on (their action items)
- <Owner>: <item> (due <date>)

## Support tickets
| Ticket | Subject | Status | Opened |

## Tech stack
One or two lines: languages · LD SDKs · Relay Proxy · cloud/infra · warehouse · CI/CD · observability · integrations

## Session plan: where we are
- Done: <sessions/topics> · **Today:** <topic> · Next: <topic>

## Links
Drive folder · Session plan · Last recap · Salesforce opp · Vitalstatistix · Jira epic · Last call recording
```

Rules: use absolute dates, make every ticket and doc a clickable link, and keep each section
to 5 bullets at most.

## Step 4: Save to Drive and link

1. Save the brief:
   `save --folder <ID> --name "<Customer> – Session Prep – <YYYY-MM-DD>" --file <scratchpad>/prep.md`.
   If a brief already exists for that date, this updates it.
2. Delete the scratchpad file.
3. In chat, give the Doc link (`webViewLink`) first, then a 3-line preview: the goal, the top
   thing to deliver, and the most important open question.

Before you finish, update `CLAUDE.md` with what this run learned, following "Keep CLAUDE.md
current" at the end of the recap skill. For a prep run that's usually: the epic key, if you
found it; the session plan link; team members and tech stack facts from the recaps and docs
you read. List what changed in one line in chat.

If `acli` reports `unauthorized`, keep going without Jira: work out the SA's tasks from the
latest recap, say the Jira status wasn't checked, and tell the SA their API token needs to be
renewed.
