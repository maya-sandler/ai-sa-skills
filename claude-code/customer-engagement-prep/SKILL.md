---
name: customer-engagement-prep
description: Prepare a full engagement prep brief, with the whole engagement history, for an upcoming LaunchDarkly customer session and save it as a Google Doc in the customer's Drive folder. Covers latest status, where any earlier engagement left off (which planned sessions really happened, from older Drive folders and Gong calls), what I owe the customer this session (from my Jira tickets via acli), the customer's open questions, support tickets the customer opened, tech stack and where the engagement stands in the session plan. Works for a new customer and for an existing customer (an existing logo) being picked up again. Use when the user (a LaunchDarkly Solutions Architect) runs /customer-engagement-prep, or asks for an engagement prep, a full history check, or to pick up an existing account before a session. For a quick prep from the current folder's recaps only, use customer-session-prep instead. Usually run from inside a customer folder like {{CUSTOMERS_DIR}}/<customer>/.
---

# Customer Engagement Prep Brief (Claude Code)

You are helping a LaunchDarkly Solutions Architect (SA) get ready for their next session with
a customer, with the **whole engagement history**: earlier engagements, older Drive folders and
every Gong call. (`customer-session-prep` is the quick version: it reads only the current
folder's recaps.) The goal is a brief they can read in **2 minutes**: one page, bullets, and each item
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

First check the customer's row in the Active Customers Doc, as the recap skill's "Active
Customers Doc" section says: stop if it isn't Active, and use its Documentation name, Folder link,
Salesforce opportunity and Slack channels.

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
meetings" table in the latest recap, then the session plan. If you can't find the date, write
"date TBD" and keep going. Don't ask.

**Existing customer (an existing logo).** This customer had an earlier engagement: another SA,
an earlier opportunity, a pilot, or the SA says they're picking up an account. Find that
engagement's history before you write anything. It holds what was promised and what was
delivered.
- **Start with the team's base Drive folder for customer projects:** `{{HISTORY_DRIVE_FOLDER}}`.
  Customer folders sit below it, named like `YY/MM - <Customer> - <engagement>`, so one
  customer can have several (a pilot, then an RSA). Always search it, along with any folders
  `CLAUDE.md` or the prompt names. If the placeholder is unfilled or reads `none`, read
  `history_drive_folder` from `~/.config/sa-skills/config.json`. If that's empty too, ask once
  for the Drive folders where the earlier work might be (a parent folder of customer folders is
  fine).
- **Look inside them through Glean** (`search` with `container_filter` set to the folder URL).
  First use the customer's name as the query to find a customer folder, then use `*` with that
  folder's URL to list everything in it. The Drive helper can't do this, because it only sees
  Docs it created itself.
- **Record the earlier folder in `CLAUDE.md` as reference only.** Save new Docs only to the
  current opportunity's Drive folder. If there isn't one yet, see Step 4.

## Step 2: Gather (in parallel where possible)

How to reach each source is in `{{SKILLS_DIR}}/customer-meeting-recap/references/sources.md`.

1. **Latest recaps.** Run `list --folder <ID> --contains "Meeting Recap"`, then `read` the newest
   one or two. If there aren't any, look for recap or notes docs in the folder through Glean.
   - **Latest call, if it has no recap:** list the customer's Gong calls (Glean `search` for
     `<customer>` with `app: gong` and `sort_by_recency`). If the newest call is newer than the
     newest recap, read its whole transcript with `read_document` and `gong_transcript.py`, as
     the recap skill's Step 2 says. Use it for the latest status, open questions and action
     items. If the SA names a call, use that one.
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
4. **Open questions.** Take the open questions from the recaps' "Next steps" section (older
   recaps call it "Open questions"), plus anything still unanswered in the session plan. For
   each one, give a draft answer or a confirmed `launchdarkly.com/docs/...` link (LaunchDarkly
   MCP `search-docs`).
5. **Support tickets.** Use Glean to find tickets the customer opened (Zendesk, plus Jira
   tickets that mention them). List the open ones and anything from the last 30 days, with
   status and link.
6. **Tech stack.** Use `CLAUDE.md`, earlier recaps, the handoff/discovery docs and Glean:
   languages, LaunchDarkly SDKs (server-side and client-side), Relay Proxy, cloud/infra, data
   warehouse, CI/CD, observability, integrations.
7. **Action items.** List the open items from the last recap's Action items tables (or the
   call), to follow up on. Its "Next steps" may hold other things to follow up on. Split them
   by owner: the customer's items, and LD people's items (AE, CSM, SE).
8. **Engagement history (existing customer only).** Work out what was delivered before. Don't
   rely on what someone says was delivered.
   - **Planned sessions:** take them from the earlier engagement's kickoff deck or session plan,
     e.g. Platform Readiness S0, S1, S2, … with each session's name and phase.
   - **Calls:** list every Gong call for the account (Glean `search`, `<customer>`, `app: gong`,
     `sort_by_recency`, `num_results: 30`). Page through until there are no more results.
   - **Match each planned session to a call.** Use dates: a session's deck is usually created
     the same day as its call. Gong titles often differ from session names (S1 Project
     Architecture might be called "Implementation Kickoff"), so check the transcript when a match
     isn't clear. Mark each session ✅ happened, ⚠️ partly happened (topics or deliverables left
     open), or ❌ never happened.
   - **Read the transcript of the last session that happened.** Note what was promised and never
     delivered, such as a role JSON, an SSO session or a doc.
   - **Open the earlier worksheets** (prerequisites, custom roles planning). Say whether they
     were filled in with the customer's data or still hold template examples.
   - **Gaps:** note long stretches with no calls, and whether the hours used match the sessions
     that happened.
   - **Account overview:** also check internal account overviews, e.g. a Slack `#ask-riley`
     thread for the account ID. Read the replies, not just the question.

Never make up facts. If a source returns nothing, write "None found".

## Step 3: Write the brief

```
# <Customer> – Engagement Prep and Next Session (<session name>, <YYYY-MM-DD or "date TBD">)
**Session:** <#/name from session plan> · <topic> · <opportunity name> · <attendees if known>

**Goal for this session:** <one sentence>

## Latest status
- 2–4 bullets: where the engagement is, what last happened (with the date and call link), and any risks.

## Where the previous engagement left off (existing customer only; leave out otherwise)
| Planned session (<earlier deck>) | Phase | Happened? | Evidence |
| <S1 name> | <phase> | ✅ <date> / ⚠️ Partly, <date> / ❌ | <deck link>, <Gong link and title>, one-line outcome |
- Promises still open from the last session that happened: <item> (<who>, <date>)
- Worksheets never filled in: <links>
- Suggested pickup: <which unfinished sessions to finish first, and why>

## Deliver in <session name> (<YYYY-MM-DD or "date TBD">; <who schedules it, if not booked>)
- ✅ <Done task> → show/explain: <what to demo or say> ([KEY-123](https://{{JIRA_SITE}}/browse/KEY-123))
- ⚠️ <Still-open task due by now> → <suggested way to handle it> ([KEY-124](...))

## <Customer> open questions
- <Question> (<who asked>, <date>) → <draft answer / doc link / "need to find out from X">

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
- <Customer> Drive folder · <Customer> previous engagement folder (existing customer only)
- Session plan · Last recap
- <Customer> current Salesforce opportunity · Vitalstatistix <Customer> account
- Jira epic · Last call recording (Gong, <date>)
```

Rules:
- Use absolute dates, and make every ticket, doc and call a clickable link.
- Keep each section to 5 bullets at most. The history table doesn't count toward this.
- **Name things explicitly.** Never write "they", "them" or "their" for the customer, or "we",
  "us" or "our" for LaunchDarkly. Write the customer's name (e.g. "Acme open questions", "Acme
  uses New Relic") and "LD". This applies to headings, bullets and link labels. Leave quotes
  exactly as spoken.
- **Label every link** with the customer and what it is ("Acme current Salesforce opportunity",
  not "Salesforce phase").
- **Make clear which session a section is about.** With history in the brief, "this session"
  is ambiguous, so every heading about the upcoming session names it and gives its date or
  "date TBD".
- **Keep owners apart.** Never list LD people's action items under the customer's heading.

## Step 4: Save to Drive and link

1. **No Drive folder yet, or the SA says not to save:** don't upload. Keep the draft in the
   scratchpad, give the SA its full path and the 3-line preview, and ask for the folder. Once
   the SA gives it, add it to `CLAUDE.md` and save.
2. Save the brief:
   `save --folder <ID> --name "<Customer> – Engagement Prep and Next Session (<session name>, <YYYY-MM-DD or date TBD>)" --file <scratchpad>/prep.md`,
   e.g. `Acme Corp – Engagement Prep and Next Session (kickoff, date TBD)`. `<Customer>` is the
   Documentation name. If a brief with that name already exists, this updates it.
3. **Changes to a brief that's already saved:** run `read --id <DOC_ID>` (its output is the
   Markdown) into the scratchpad, edit that file, and `save` it under the same name. Don't
   rebuild the brief from scratch, because the SA may have edited the Doc. A renamed Drive
   folder keeps its ID, so the same `--folder` still works.
4. Delete the scratchpad file.
5. In chat, give the Doc link (`webViewLink`) first, then a 3-line preview: the goal, the top
   thing to deliver, and the most important open question.

Before you finish, update `CLAUDE.md` with what this run learned, following "Keep CLAUDE.md
current" at the end of the recap skill. For a prep run that's usually:
- the epic key, if you found it;
- the session plan link;
- team members and tech stack facts from the recaps and docs you read;
- for an existing customer: the earlier engagement folder (reference only), which planned
  sessions happened or didn't, and the promises still open.

List what changed in one line in chat.

If `acli` reports `unauthorized`, keep going without Jira: work out the SA's tasks from the
latest recap, say the Jira status wasn't checked, and tell the SA their API token needs to be
renewed.
