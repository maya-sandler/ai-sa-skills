---
name: customer-recap-check
description: Automatically recap LaunchDarkly customer calls. On a schedule, finds Gong's "call recording is ready" emails (Gmail through Glean) for calls with the SA's active customers, waits for each call's full transcript in Glean, skips calls already recapped, runs customer-meeting-recap unattended, adds each finished recap to the customer's Master Engagement Doc (customer-shared-notes), and reports in the SA's Slack self-DM, asking there for any missing links. Also sets the check up and changes its settings. Use when a scheduled task runs the recap check, or when the user (a LaunchDarkly Solutions Architect) asks to set up, run, pause, switch to live, or check on automatic meeting recaps.
---

# Customer Recap Check (Claude Code)

This skill turns every call with an **active customer** into a recap and Jira tickets, with no
prompt from the SA. A Claude Code scheduled task runs it every hour on the SA's Mac. Each run
looks for new **Gong "call is ready" emails** in the SA's Gmail, recaps those calls with
`customer-meeting-recap`, adds each finished recap to the customer-facing Master Engagement Doc with
`customer-shared-notes`, and tells the SA in their **Slack self-DM**, asking there when links
are missing.

Gong emails the SA when a call's recording is ready, about two hours before Glean's Gong search
returns the call, and only to the call's participants. So an email means the SA was on the call,
and no calendar check is needed.

It uses only sign-ins the SA already has (Glean and Slack connectors, the Drive helper, `acli`). Never read or print anything in `~/.config/sa-skills/google/`,
`~/.config/acli/token.txt` or any `.env` file.

## Helpers

Write every helper command out in full; putting it in a shell variable breaks under zsh.

```bash
~/.local/share/sa-skills/venv/bin/python -W ignore {{SKILLS_DIR}}/customer-recap-check/scripts/recap_check.py <command> ...
```

| Command | Does |
|---|---|
| `config get [KEY]` / `config set KEY VALUE` | Reads or sets one setting in `~/.config/sa-skills/config.json`, keeping the rest |
| `customers init --folder ID` / `customers read --folder ID` | Creates the Active Customers Doc / returns its Active rows |
| `calls get --id ID` / `calls mark --id ID --status S ...` | The processed-calls log in `~/.config/sa-skills/processed-calls.json`. Statuses: `waiting`, `done`, `held`, `skipped`, `error`, `dry-run` |
| `calls waiting` / `calls held` | Calls still to recap (`waiting` or `dry-run`) / calls waiting for the SA in Slack (`held`, or `done` with links still missing) |
| `gong-email --file PATH` | Reads a saved Gong "call is ready" email and prints its call ID, clean call link, title, account, date and duration |
| `log add --kind activity\|audit --run RUN --text TEXT [--dry-run]` | Appends one line, stamped with the current time, to the run log `~/.config/sa-skills/recap-check-log.md` (one section per run) |
| `slack-upload --url URL --file PATH` | Uploads a file's bytes to a Slack upload URL |

`calls mark` options: `--customer`, `--date`, `--title`, `--url`, `--duration`, `--note`,
`--slack-ts`, `--missing <links, comma-separated>` (`none` clears it) and `--reminded
<YYYY-MM-DD>`. It keeps fields you leave out.

The Drive helper (`gdrive.py`) and the transcript helper (`gong_transcript.py`) are described in
the `customer-meeting-recap` skill.

**Settings** (`config get`): `sa_drive_folder` (folder ID of the SA's Drive folder, holding the
Active Customers Doc), `customers_dir`, `recap_check_mode` (`dry-run` or `live`;
missing means `dry-run`), `slack_user_id` and `slack_dm_channel` (found by the run), and
`gong_emails_since` (when the last run looked for Gong emails, set by the run).

## Set up the check (when the SA asks)

Do these in order, telling the SA what each step did.

1. **SA Drive folder.** If `config get sa_drive_folder` is empty, ask the SA for their Drive
   folder link (the folder for the Active Customers Doc). Save the folder ID (the
   part after `/folders/`, without `?usp=...`) with `config set sa_drive_folder <ID>`.
2. **Active Customers Doc.** Run `customers init --folder <ID>` and give the SA its link. Ask
   them to add a row per customer they're working with (Customer, Folder, Gong account, Meeting
   title words, Status Active). No links or email domains go in that Doc.
3. **Slack self-DM.** Find it as "Slack self-DM" below describes, and save it.
4. **Mode.** Set `config set recap_check_mode dry-run` unless the SA asks for live.
5. **Schedule.** Ask which hours to run (suggest every hour, 9:00 to 21:00 on weekdays, so a call that ends by about 20:00 is recapped the same day). Then
   create the task with the scheduled-tasks tool `create_scheduled_task`:
   - `taskId`: `customer-recap-check`, `title`: `Customer recap check`
   - `cronExpression`: e.g. `5 9-21 * * 1-5` (five past each hour, in local time)
   - `description`: `Recap new Gong calls with active customers`
   - `notifyOnCompletion`: `false` (the run notifies the SA itself, only when there's news)
   - `prompt`: `Run the customer-recap-check skill for one scheduled check now, following its "Each run" steps exactly. This run is unattended: never ask questions or wait for answers; post to my Slack self-DM as the skill says.`
6. Tell the SA:
   - The desktop app must be open, and the Mac awake, for a check to run; a missed check runs
     at the next one.
   - Gong must email them when a call is ready (Gong's email notifications on, the default),
     and Glean must reach their Gmail. The check reads nothing else in their mail.
   - On the first runs, approve the tools it uses when asked (Glean, Slack, Bash for the helpers
     and `acli`), so later runs don't stop for permission.
   - It starts in **dry run**: for a week it only reports what it would do. To go live, they
     ask "switch the recap check to live".

**Other requests:**

- **Switch to live / back to dry run:** `config set recap_check_mode live` (or `dry-run`).
- **Pause or resume:** the scheduled-tasks tool `update_scheduled_task` on `customer-recap-check`.
- **Run it now:** do one run of "Each run" below, in this session.
- **What did it do?** Read the run log, `~/.config/sa-skills/recap-check-log.md` (newest run
  at the end).

## Slack self-DM

The check posts **only** to the SA's self-DM (their conversation with themselves): never to a
channel, another person or a group. A recap the SA runs by hand asks for missing links there
too, and records the call as `held`, so step 3 handles its thread like the check's own. It reads the self-DM, and, through the recap skill, only
the customer channels and chats the SA listed in the customer's `CLAUDE.md`.

- **Find it once:** the Slack tools' descriptions state the signed-in user's ID ("Current logged
  in user's user_id is U…"). Read the DM with that ID: `slack_read_channel` with `channel_id` =
  the user ID and `limit` 1. Its reply starts `Channel: DM (D…)`; that `D…` ID is the self-DM.
  Save both: `config set slack_user_id <U…>` and `config set slack_dm_channel <D…>`.
- **Check it every run before posting:** the same read must return the saved `D…` ID. If it
  doesn't, post nothing to Slack, and log it.

**To post** a message (the connector posts by sharing a small file with a message):

1. Write the details to a temporary Markdown file in your scratchpad, e.g. `acme-2026-10-26.md`.
2. `slack_get_file_upload_url` with that filename and its exact size in bytes
   (`wc -c < <file>`). It returns an upload URL and a file ID.
3. `recap_check.py slack-upload --url '<upload URL>' --file <file>`, copying the URL exactly as
   returned. A 401 means the URL expired or was changed: get a new one.
4. `slack_complete_file_upload` with the file ID, `channel_id` = the self-DM, a `title`, and the
   message as `initial_comment`. For a follow-up to an earlier post, also pass its `thread_ts`.
5. `slack_read_channel` on the self-DM with `limit` 1 to get the new post's timestamp (`ts`).
6. Delete the temporary file.

Slack doesn't notify the SA about posts made as them. So after posting anything the SA must act
on, also send a Claude notification with the `PushNotification` tool, if this session has it,
with the same first line.

## Each run

Keep a **run ID**, the local start time as `YYYYMMDD-HHMM`. Also note the start time in UTC
(`date -u +%Y-%m-%dT%H:%M:%SZ`) for step 10. Log as you go, in the one local run log: an **activity**
line for each step and tool call (`log add --kind activity`), and an **audit** line for each
change made in Drive, Jira or Slack (`log add --kind audit`). Logs never go to Drive. In dry-run mode, add `--dry-run` to every log line.
`log add` stamps each line with the time it runs, so run it right after the step or tool call it
describes, in the same message as the next step's call. Never save lines up and add them
together at the end: they'd all get the same time. Log lines name a call by customer, date and
Gong call ID; never put transcript text, recap content, email content, tokens or secrets in
them.

Recap at most **5 calls per run**; leave the rest waiting for the next run.

**Missing links.** A recap needs the opportunity's links from the customer's `CLAUDE.md`: Drive
folder, Salesforce opportunity, Vitalstatistix, session plan, and the customer's Slack channels
and chats. When any are missing, the recap skill returns `held` with the list, and the check
asks the SA **once**, in one Slack post listing all of them. What happens next:

| Missing | No reply by the next run | Reply after the recap was made |
|---|---|---|
| **Drive folder**, or which opportunity it is | Stays held: no Doc can be made. Remind in the thread at most once a day | — |
| Only other links (Salesforce, Vitalstatistix, session plan, Slack channels) | Recap and tickets are made with `Not found` for them; a follow-up in the thread lists the links still needed | Saved to `CLAUDE.md` for the next recap |

Never work out a missing link yourself, and never search Slack or Glean for the customer's
channels. Only the SA's answer counts.

**1. Load settings.** `config get`. If `sa_drive_folder` is empty, the check isn't set up: post
nothing, send a Claude notification ("The recap check isn't set up yet: ask Claude to set up the
recap check"), and stop. Note the mode (`recap_check_mode`, default `dry-run`),
`customers_dir` and `gong_emails_since`.

**2. Slack self-DM.** Find or check it (above). If it can't be confirmed, carry on without
Slack: use Claude notifications only, and log it. With no Slack, nothing can be asked, so a call
that would be held stays `waiting` and is tried again on the next run.

**3. Replies in Slack.** `calls held`. For each call with a `slack_ts`: `slack_read_thread` on
the self-DM and that `ts`. Look only at replies from the SA (`slack_user_id`) after the post (or
after the last follow-up the check posted in that thread).

| Call | SA's reply | Do |
|---|---|---|
| `held`, note `unclear-customer` | "yes" | `calls mark --status waiting --customer <C>`; it's recapped in step 7 |
| `held`, any note | Links, an opportunity name, or "skip" | In live mode, read the transcript (step 7, "Transcript") and run `customer-meeting-recap` with a prompt starting `UNATTENDED RUN, RESUME`, giving the call details as in step 8 and the SA's answer word for word. Handle its `RECAP_RESULT` as in step 9, posting in the same thread |
| `held`, any note | "Not a customer call" or "ignore" | `calls mark --status skipped`, and confirm in the thread |
| `held`, its note lists only links other than the Drive folder and opportunity | None | In live mode, run the recap with a prompt starting `UNATTENDED RUN, NO ANSWER` (call details as in step 8). It writes `Not found` for the missing links. Handle its `RECAP_RESULT` as in step 9, in the same thread: the "recap ready" post lists the links still needed |
| `held`, its note has `drive_folder`, `opportunity`, `new_opportunity` or `unclear-customer` (older runs wrote `needs-drive-folder`) | None | If `reminded` is before today: post in the thread "Still waiting: <the question>", and `calls mark --reminded <today>`. Otherwise nothing |
| `done` with `missing` | Links | Save each link to the customer's `CLAUDE.md` as the recap skill's "Keep CLAUDE.md current" says (Slack channels in its **Slack** section). Then `calls mark --missing <what's still missing, or none>`, and confirm in the thread |
| `done` with `missing` | None | Nothing |

**4. Active customers.** `customers read --folder <sa_drive_folder>`. No Active rows: log
"no active customers", and stop quietly.

**5. New Gong emails, for active customers only.** Look only for emails about the Active rows
from step 4, so calls with anyone else are never opened or worked on. For each Active row, search
Glean with `app: gmail`, query `Call recording and analysis is ready <Gong account>`,
`sort_by_recency`, `num_results: 20`; if the row has **Meeting title words**, search again with
those in place of the Gong account. Results from Gong have Source `gmailnative`, Owner `Gong`,
and a subject like `<meeting title>: Call recording and analysis is ready`. Keep those
**created** (the `Created` time, in UTC) after `gong_emails_since` (also UTC) minus one hour, or
after the start of today if it's empty; never more than 3 days back. If all 20 are that new, page
with the cursor. Drop duplicates found by more than one search. Never search for Gong emails in
general, ignore every other email, and read no other mail.

For each email kept, in order:

1. Glean `read_document` on its `mail.google.com` link. The result has no structured content,
   only the raw Gmail message, and is usually saved to a file because it's large. If it came
   back inline, write it to a file in your scratchpad.
2. `recap_check.py gong-email --file <that file>`. It prints `gong_call_id`, `call_url` (the
   link without Gong's tracking), `title`, `account`, `date` and `duration`. It never prints the
   email's "Key points", and you must not read or use them: the recap is written only from the
   transcript.
3. `calls get --id <gong_call_id>`. Any status at all: it's already known, skip it.
4. **Match it to a customer:**

   | Email | Customer |
   |---|---|
   | `account` is one row's **Gong account** (ignoring case) | That row |
   | No account matches, but the title contains exactly one row's **Meeting title words** | Unclear: post once to Slack ("Is *<title>* (<date>) a call with <customer>? Reply yes, or 'not a customer call'"), and `calls mark --status held --note unclear-customer --title ... --date ... --url ... --duration ... --slack-ts <ts> --reminded <today>` |
   | No account matches, and the title has two rows' Meeting title words | Unclear, as above, naming both |
   | No row matches (the search matched other text in the email) | Not an active customer's call: skip it, `calls mark --status skipped --note "not an active customer"` so it isn't opened again, and log only that |

5. Matched: `calls mark --id <gong_call_id> --status waiting --customer <Customer> --date <date>
   --title <title> --url <call_url> --duration <duration>`.

Delete any email files you wrote to the scratchpad when done.

**6. Skip what's already done.** `calls waiting`. In dry-run mode, leave out calls with status
`dry-run` (already reported). In live mode, a `dry-run` call first seen more than 2 days ago is
`calls mark --status skipped --note "dry run only"`; recap the others like `waiting` ones. Take
the calls left oldest first, at most 5 (with those resumed in step 3). For each:

- The customer's folder is `<customers_dir>/<Folder from the Active Customers Doc>`. **No folder
  yet:** create it with a `CLAUDE.md` from the recap skill's
  `references/customer-folder-template.md`, filling in only the customer name and the SA.
- In its `CLAUDE.md`, find the opportunity's Drive folder. If there is one, `gdrive.py list
  --folder <ID> --contains "Meeting Recap – <YYYY-MM-DD>"` and `read` each result. One naming
  this Gong call ID on its Recording line → `calls mark --status done --note "recap already in
  Drive"`, and skip it.

**7. Transcript.** The recap is always written from the call's full transcript. For each call:

1. Glean `read_document` on its `url` (the clean call link). If it returns no
   `richDocumentData.content`, Gong or Glean is still processing.
2. `python3 {{SKILLS_DIR}}/customer-meeting-recap/scripts/gong_transcript.py --file <saved
   result> --out <scratchpad>/<customer>-<date>-transcript.txt`. It writes the transcript and
   prints its length in `minutes`.
3. **Not ready** (no content, the helper prints an error, or `minutes` is under half the call's
   `duration`): log "waiting for transcript" and leave it for the next run. First seen more than
   2 days ago: post once to Slack ("*<Customer>* call *<title>* (<date>): no transcript in Glean
   after 2 days; recap it by hand"), and `calls mark --status error --note
   "no transcript after 2 days"`.

Never fall back to the email's Key points, Gong's call summary or Glean search snippets.

**8. Recap it.**

- **Dry run:** don't run the recap skill. Post one Slack message per call ("Dry run: would recap
  *<title>* with <Customer> and add it to the Master Engagement Doc; links missing: <the links
  from the list above that `CLAUDE.md` doesn't have, or none>"), and `calls mark --status
  dry-run`.
- **Live:** run the `customer-meeting-recap` skill with a prompt starting `UNATTENDED RUN`:

  ```text
  UNATTENDED RUN
  Gong link: <url>
  Gong call ID: <id>
  Transcript file: <scratchpad>/<customer>-<date>-transcript.txt
  Customer folder: <customers_dir>/<Folder>
  Meeting: <title>, <YYYY-MM-DD>
  ```

**9. Handle the result.** Read the `RECAP_RESULT` block the recap skill ends with:

| Status | Post to Slack | Then |
|---|---|---|
| `done` | First update the Master Engagement Doc (below). Then "*<Customer>* recap ready: <n> tickets", with the recap and ticket links in the file, and the Master Engagement Doc line. If `missing` isn't empty, add "Links still needed: <links>. Reply in this thread to add them" | `calls mark --status done --missing <missing, or none> --slack-ts <ts>` (for a thread reply, keep the first post's `ts`); audit lines for the recap Doc and each ticket |
| `held` | "*<Customer>* recap waiting: <its question> Reply in this thread." | `calls mark --status held --note <needs, comma-separated> --slack-ts <ts> --reminded <today>` |
| `waiting` | Nothing | Leave it `waiting` for the next run |
| `error` | "*<Customer>* recap failed: <error>" | `calls mark --status error --note <error>`; the next run doesn't retry it |

Send a Claude notification for every `held` and `error`, and for `done`. Delete the transcript
file once the call is handled.

**Master Engagement Doc.** Every time a recap ends `done` (a first run, or a resumed held call),
add it to the customer-facing `<Customer>-LaunchDarkly Master Engagement Doc`. Run the
`customer-shared-notes` skill once, only after the recap Doc is saved, with this prompt:

```text
UNATTENDED RUN
Customer folder: <customers_dir>/<Folder>
Opportunity: <RECAP_RESULT opportunity>
Recap Doc ID: <RECAP_RESULT recap.id, or the ID in recap.link after /d/>
```

Read the `SHARED_NOTES_RESULT` block it ends with:

| Status | Add to the "recap ready" post | Log |
|---|---|---|
| `added` | "Added to the Master Engagement Doc: <doc link>" | An audit line naming the shared Doc and the meeting added |
| `already_there` | Nothing | An activity line |
| `held` or `error` | "Master Engagement Doc not updated: <reason>" | An activity line with the reason |

Don't retry a `held` or `error` on a later run. Never run it in dry-run mode, or for a recap
that isn't `done`.

**10. Finish.** `config set gong_emails_since <this run's start time in UTC>`. Log the
run's end with a one-line summary (emails found, done, held, waiting, skipped). When the run
found nothing new, post nothing and send no notification.
