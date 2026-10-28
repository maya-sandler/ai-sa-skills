---
name: customer-session-prep
description: Prepare a quick one-page brief for the next LaunchDarkly customer session from the customer's current Drive folder only, and save it as a Google Doc there. Reads the earlier recaps in that folder, the follow-up items from them that are still open, the customer's support tickets, tech stack, session plan and links, and the Slack channels listed in the SA's Active Customers Doc. No history check of earlier engagements, older folders or Gong calls (that's customer-engagement-prep). Use when the user (a LaunchDarkly Solutions Architect) runs /customer-session-prep, or asks to prep for, get ready for, or brief them on the next session or call with a customer, usually from inside a customer folder like {{CUSTOMERS_DIR}}/<customer>/.
---

# Customer Session Prep Brief (Claude Code)

You are helping a LaunchDarkly Solutions Architect (SA) get ready for their next session with a
customer. The goal is a brief they can read in **2 minutes**: one page, bullets, and each item
saying what to *do or say* in the session.

**Look only at the current folder.** The sources are: the customer's Drive folder (the one the SA
gives, or the Folder link in the Active Customers Doc), the recaps in it, the session plan, the
customer's support tickets, and the Slack channels in the Active Customers Doc. Don't look for
earlier engagements, older Drive folders or the customer's other Gong calls: that history check is
`customer-engagement-prep`. If the SA asks for history, suggest `/customer-engagement-prep`.

**Everything you produce goes to Google Drive, never to the local customer folder.** Write the
brief's Markdown in your scratchpad directory, upload it, then delete it.

**Settings:** customer folders live in `{{CUSTOMERS_DIR}}/`, the skills in `{{SKILLS_DIR}}/`, and
Jira tickets are in project `{{JIRA_PROJECT}}` on `{{JIRA_SITE}}`. If a placeholder in double
curly braces shows instead, follow the "Settings" note in the recap skill.

The Drive helper commands (`save`, `list`, `read`), and what to do if it isn't signed in, are
described in `{{SKILLS_DIR}}/customer-meeting-recap/SKILL.md` under "Drive helper". Always write
the full command:

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore {{SKILLS_DIR}}/customer-meeting-recap/scripts/gdrive.py <command> ...
```

## Step 1: Customer, folder and session

1. **Active Customers Doc.** Check the customer's row, as the recap skill's "Active Customers
   Doc" section says. Stop if it isn't Active. Use its Documentation name for `<Customer>`, its
   Folder link, its Salesforce opportunity and its Slack channels.
2. **Customer folder.** Read `{{CUSTOMERS_DIR}}/<local_folder>/CLAUDE.md` for the epic key, team,
   tech stack and the opportunity's links (Salesforce, Vitalstatistix, session plan). If there's
   no folder, create it as the recap skill's Step 1 says.
3. **Drive folder.** The folder the SA gives wins; otherwise the row's Folder link; otherwise the
   opportunity's Drive folder in `CLAUDE.md`. None of them: ask the SA for the folder link before
   doing anything else. The folder ID is the part after `/folders/`.
4. **Session.** Find the next session's name, date and topic in this order: what the SA said, the
   "Scheduled meetings" table in the latest recap, then the session plan. If you can't find the
   date, write "date TBD" and keep going. Don't ask.

## Step 2: Gather (in parallel where possible)

How to reach each source is in `{{SKILLS_DIR}}/customer-meeting-recap/references/sources.md`.

1. **Recaps in the folder.** `list --folder <ID> --contains "Meeting Recap"`, then `read` each one,
   newest first. If there are none, say so and work from the session plan and `CLAUDE.md`.
2. **Follow-ups still open.** From every recap's action-item tables and Next steps (older recaps
   call them Open questions), keep the items not marked done in a later recap's "Previous action
   items". For LaunchDarkly items with a Jira key in the recap, check the ticket:
   `acli jira workitem view <KEY> --fields summary,status,duedate --json`. Done tickets are things
   to *show or explain*; open ones due on or before the session are warnings.
3. **Session plan.** The link in `CLAUDE.md`, or Glean `search` with `container_filter` set to the
   Drive folder URL. Work out what the next session covers and its success criteria.
4. **Support tickets.** Glean: tickets the customer opened (Zendesk, plus Jira tickets that
   mention them). List the open ones and anything from the last 30 days, with status and link.
5. **Tech stack.** From `CLAUDE.md` and the recaps: languages, LaunchDarkly SDKs (server-side and
   client-side), Relay Proxy, cloud/infra, data warehouse, CI/CD, observability, integrations.
6. **Slack.** Read the row's Slack channels since the latest recap's date (`slack_read_channel`,
   and `slack_read_thread` where the replies matter): new questions, promises and blockers. Never
   name or link the channels in the brief. No channels in the row or `CLAUDE.md`: skip this and
   say so at the end. Never search Slack for them.

Never make up facts. If a source returns nothing, write "None found".

## Step 3: Write the brief

```
# <Customer> – Session Prep – <session name> (<YYYY-MM-DD or "date TBD">)
**Session:** <#/name from session plan> · <topic> · <opportunity name> · <attendees if known>

**Goal for this session:** <one sentence>

## Latest status
- 2–4 bullets from the latest recap and Slack: where things stand, risks.

## Deliver in <session name> (<YYYY-MM-DD or "date TBD">)
- ✅ <Done task> → show/explain: <what to demo or say> ([KEY-123](https://{{JIRA_SITE}}/browse/KEY-123))
- ⚠️ <Still-open task due by now> → <suggested way to handle it> ([KEY-124](...))

## <Customer> next steps and questions
- <Question or next step> (<who>, <date>) → <draft answer / doc link / "need to find out from X">

## Follow up on (<Customer> action items)
- <Owner>: <item> (due <date>)

## Follow up on (LD internal action items)
- <LD owner>: <item> (promised <date>)

## Support tickets
| Ticket | Subject | Status | Opened |

## Tech stack
One or two lines: languages · LD SDKs · Relay Proxy · cloud/infra · warehouse · CI/CD · observability · integrations

## Session plan: where the <Customer> engagement stands
- Done: <sessions/topics, with dates> · **Upcoming (<session name>, <date or "date TBD">):** <topic> · Next: <topic>

## Links
- <Customer> Drive folder · Session plan · Last recap
- <Customer> Salesforce opportunity · Vitalstatistix <Customer> account · Jira epic
```

Rules:
- Use absolute dates, and make every ticket, doc and call a clickable link.
- Keep each section to 5 bullets at most.
- **Name things explicitly.** Write the customer's name and "LD", never "they", "them", "we" or
  "our". Leave quotes exactly as spoken.
- **Label every link** with the customer and what it is.
- **Keep owners apart.** Never list LD people's action items under the customer's heading.
- For a draft answer, give a confirmed `launchdarkly.com/docs/...` link (LaunchDarkly MCP
  `search-docs`) where one fits.

## Step 4: Save to Drive and link

1. Save the brief:
   `save --folder <ID> --name "<Customer> – Session Prep – <session name> (<YYYY-MM-DD or date TBD>)" --file <scratchpad>/prep.md`.
   If a brief with that name already exists, this updates it.
2. **Changes to a brief that's already saved:** `read --id <DOC_ID>` into the scratchpad, edit that
   file, and `save` it under the same name. Don't rebuild it from scratch: the SA may have edited
   the Doc.
3. Delete the scratchpad file.
4. In chat, give the Doc link (`webViewLink`) first, then a 3-line preview: the goal, the top thing
   to deliver, and the most important open question. Say which sources had nothing.

Before you finish, update `CLAUDE.md` with what this run learned (the epic key, session plan link,
team members and tech stack facts), following "Keep CLAUDE.md current" in the recap skill, and
list what changed in one line in chat.

If `acli` reports `unauthorized`, keep going without Jira: take the status from the recaps, say
Jira wasn't checked, and tell the SA their API token needs to be renewed.
