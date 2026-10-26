---
name: customer-recap-check
description: Automatically recap LaunchDarkly customer calls. On a schedule, finds today's finished meetings with the SA's active customers (Google Calendar), waits for each Gong call to appear in Glean, skips calls already recapped, runs customer-meeting-recap unattended, and reports in the SA's Slack self-DM, asking there when something is missing. Also sets the check up and changes its settings. Use when a scheduled task runs the recap check, or when the user (a LaunchDarkly Solutions Architect) asks to set up, run, pause, switch to live, or check on automatic meeting recaps.
---

# Customer Recap Check (Claude Code)

This skill turns every call with an **active customer** into a recap and Jira tickets, with no
prompt from the SA. A Claude Code scheduled task runs it every hour on the SA's Mac. Each run
checks today's finished meetings, recaps the new ones with `customer-meeting-recap`, and tells
the SA in their **Slack self-DM**, asking there when something is missing.

It uses only sign-ins the SA already has (Google Calendar, Glean and Slack connectors, the Drive
helper, `acli`). Never read or print anything in `~/.config/sa-skills/google/`,
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
| `calls get --id ID` / `calls mark --id ID --status S ...` / `calls held` | The processed-calls log in `~/.config/sa-skills/processed-calls.json` |
| `log add --kind activity\|audit --run RUN --text TEXT [--dry-run]` / `log flush --folder ID` | Queues log lines, then appends them to this month's log Docs |
| `slack-upload --url URL --file PATH` | Uploads a file's bytes to a Slack upload URL |

The Drive helper (`gdrive.py`) is described in the `customer-meeting-recap` skill.

**Settings** (`config get`): `sa_drive_folder` (folder ID of the SA's Drive folder, holding the
Active Customers Doc and the logs), `customers_dir`, `recap_check_mode` (`dry-run` or `live`;
missing means `dry-run`), `slack_user_id` and `slack_dm_channel` (found by the run).

## Set up the check (when the SA asks)

Do these in order, telling the SA what each step did.

1. **SA Drive folder.** If `config get sa_drive_folder` is empty, ask the SA for their Drive
   folder link (the folder for the Active Customers Doc and the logs). Save the folder ID (the
   part after `/folders/`, without `?usp=...`) with `config set sa_drive_folder <ID>`.
2. **Active Customers Doc.** Run `customers init --folder <ID>` and give the SA its link. Ask
   them to add a row per customer they're working with (Customer, Folder, Gong account, Meeting
   title words, Status Active). No links or email domains go in that Doc.
3. **Slack self-DM.** Find it as "Slack self-DM" below describes, and save it.
4. **Mode.** Set `config set recap_check_mode dry-run` unless the SA asks for live.
5. **Schedule.** Ask which hours to run (suggest every hour, 9:00 to 18:00 on weekdays). Then
   create the task with the scheduled-tasks tool `create_scheduled_task`:
   - `taskId`: `customer-recap-check`, `title`: `Customer recap check`
   - `cronExpression`: e.g. `5 9-18 * * 1-5` (five past each hour, in local time)
   - `description`: `Recap today's finished calls with active customers`
   - `notifyOnCompletion`: `false` (the run notifies the SA itself, only when there's news)
   - `prompt`: `Run the customer-recap-check skill for one scheduled check now, following its "Each run" steps exactly. This run is unattended: never ask questions or wait for answers; post to my Slack self-DM as the skill says.`
6. Tell the SA:
   - The desktop app must be open, and the Mac awake, for a check to run; a missed check runs
     at the next one.
   - On the first runs, approve the tools it uses when asked (Calendar, Glean, Slack, Bash for
     the helpers and `acli`), so later runs don't stop for permission.
   - It starts in **dry run**: for a week it only reports what it would do. To go live, they
     ask "switch the recap check to live".

**Other requests:**

- **Switch to live / back to dry run:** `config set recap_check_mode live` (or `dry-run`).
- **Pause or resume:** the scheduled-tasks tool `update_scheduled_task` on `customer-recap-check`.
- **Run it now:** do one run of "Each run" below, in this session.
- **What did it do?** Read this month's Activity Log and Audit Log Docs in the SA Drive folder
  (`gdrive.py list --folder <ID> --contains "Recap Workflow"`, then `read`).

## Slack self-DM

The check posts **only** to the SA's self-DM (their conversation with themselves): never to a
channel, another person or a group, and it reads no other conversation.

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

Keep a **run ID**, the local start time as `YYYYMMDD-HHMM`. Log as you go: an **activity** line
for each step and tool call (`log add --kind activity`), and an **audit** line for each change
made in Drive, Jira or Slack (`log add --kind audit`). In dry-run mode, add `--dry-run` to every
log line. Log lines name a call by customer, date and Gong call ID; never put transcript text,
recap content, tokens or secrets in them.

Handle at most **5 calls per run**; leave the rest for the next run.

**1. Load settings.** `config get`. If `sa_drive_folder` is empty, the check isn't set up: post
nothing, send a Claude notification ("The recap check isn't set up yet: ask Claude to set up the
recap check"), and stop. Note the mode (`recap_check_mode`, default `dry-run`) and
`customers_dir`.

**2. Slack self-DM.** Find or check it (above). If it can't be confirmed, carry on without
Slack: use Claude notifications only, and log it.

**3. Answers to held calls.** `calls held`. For each held call with a `slack_ts`:
`slack_read_thread` on the self-DM and that `ts`. Look only at replies from the SA
(`slack_user_id`) after the post.

- **An answer** (a Drive folder link, an opportunity name, other links, or "skip"): in live mode,
  run `customer-meeting-recap` with a prompt starting `UNATTENDED RUN, RESUME`, giving the Gong
  link, the customer folder, the meeting, and the SA's answer word for word. Read its
  `RECAP_RESULT` and handle it as in step 9, posting in the same thread.
- **"Not a customer call" or "ignore":** `calls mark --status skipped`, and confirm in the thread.
- **No reply yet:** leave it held, and post nothing.

**4. Active customers.** `customers read --folder <sa_drive_folder>`. No Active rows: log
"no active customers", flush the logs (step 10), and stop quietly.

**5. Today's finished meetings.** Google Calendar `list_events` on the primary calendar, from
the start of today to now. Keep events that:

- ended at least 15 minutes ago,
- have the SA as an attendee who didn't decline, and
- have a title containing one customer's **Meeting title words** (ignoring case).

An event matching two customers is **unclear** (step 6). Ignore all other events, including
internal meetings, and never read their details beyond the title, time and attendees.

**6. Find each meeting's Gong call.** Search Glean with `app: gong` for the meeting title,
sorted by recency, updated today. The call matches when it's from today, its title matches the
meeting, and its `account:` filter is the customer's **Gong account**. The Gong call ID is the
`id=` in its link.

- **Not found yet:** Gong or Glean is still processing. Log "waiting" and leave it for the next
  run. After 2 days, log it once as not found and stop looking.
- **The title matches but the Gong account doesn't, or two customers match:** unclear. Post once
  to Slack ("Is *<meeting title>* a call with <customer>? Reply yes, or 'not a customer call'"),
  and `calls mark --status held --note unclear-customer --slack-ts <ts>`.

**7. Skip what's already done.** For each call:

1. `calls get --id <call ID>`. Status `done`, `held` or `skipped` → skip it (held calls are
   handled in step 3). Status `dry-run` → skip it in dry-run mode (already reported), and
   handle it in live mode.
2. In the customer's `CLAUDE.md`, find the opportunity's Drive folder (see step 8). If there is
   one, `gdrive.py list --folder <ID> --contains "Meeting Recap – <YYYY-MM-DD>"` and `read` each
   result. One naming this Gong call ID on its Recording line → `calls mark --status done
   --note "recap already in Drive"`, and skip it.

**8. Customer folder and Drive folder.** The customer's folder is
`<customers_dir>/<Folder from the Active Customers Doc>`.

- **No folder yet:** create it with a `CLAUDE.md` from the recap skill's
  `references/customer-folder-template.md`, filling in only the customer name and the SA.
- **No Drive folder** (no opportunity in `CLAUDE.md` has one): post to Slack ("*<Customer>*
  recap waiting: reply in this thread with the Drive folder link for this engagement"), and
  `calls mark --status held --note needs-drive-folder --slack-ts <ts>`. Go to the next call.

**9. Recap it.**

- **Dry run:** don't run the recap skill. Post one Slack message per call ("Dry run:
  would recap *<meeting title>* with <Customer>; Drive folder found / missing"), and
  `calls mark --status dry-run`.
- **Live:** run the `customer-meeting-recap` skill with a prompt starting `UNATTENDED RUN`:

  ```text
  UNATTENDED RUN
  Gong link: <link>
  Customer folder: <customers_dir>/<Folder>
  Meeting: <title>, <YYYY-MM-DD>
  ```

  Then read the `RECAP_RESULT` block it ends with:

  | Status | Post to Slack | Then |
  |---|---|---|
  | `done` | "*<Customer>* recap ready: <n> tickets", with the recap and ticket links in the file | `calls mark --status done`; audit lines for the recap Doc and each ticket |
  | `held` | "*<Customer>* recap waiting: <its question> Reply in this thread.", listing the held tickets | `calls mark --status held --note <needs> --slack-ts <ts>` |
  | `error` | "*<Customer>* recap failed: <error>" | `calls mark --status error --note <error>`; the next run doesn't retry it |

  Send a Claude notification for every `held` and `error`, and for `done`.

**10. Finish.** Log the run's end with a one-line summary (calls found, done, held, skipped).
Then `log flush --folder <sa_drive_folder>`. If the flush fails, the lines stay on the Mac and
the next run adds them. When the run found nothing new, post nothing and send no notification.
