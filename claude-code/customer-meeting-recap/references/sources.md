# Where to find customer information (Claude Code)

Check the customer folder's `CLAUDE.md` first, then the sources below. Glean results depend on what the SA is allowed to see. An empty result means
"not found", not an error.

| Need | Where to look |
|---|---|
| Gong call transcript | Glean `read_document` with the Gong URL, or Glean `search` for `<customer>` with `app: gong` |
| Every Gong call for the account (engagement history) | Glean `search` for `<customer>` with `app: gong`, `sort_by_recency` and `num_results: 30`. Page with the cursor until there are no more results. Titles often don't match session names, so match by date and transcript |
| Earlier engagement folders (another SA's, a pilot) | Glean `search` with the customer's name and `container_filter` set to the parent folder URL to find the customer folder, then `query: *` with that folder's URL to list its decks and sheets. The Drive helper only sees Docs it created, so it lists nothing here |
| Internal account overview | Slack `#ask-riley` threads that mention the account ID. Read the thread replies, since the search result often shows only the question |
| Recaps, prep briefs, transcripts the skills saved | Drive helper: `gdrive.py list --folder <ID> --contains "<Meeting Recap / Session Prep / Transcript>"`, then `gdrive.py read --id <DOC_ID>`. Shows new Docs right away (Glean can take a while to index them) |
| Other Drive folder contents | Glean `search` with `query: *` and `container_filter` set to the folder URL, then `read_document` on the results |
| Drive folder, Salesforce opportunity, Vitalstatistix, session plan | **Per opportunity.** Only from the SA's prompt, that opportunity's `CLAUDE.md` entry, its Drive folder (newest recap for that opportunity, other docs), or the SA's answer. A new opportunity: ask whether to reuse each link from an existing opportunity or use a new one. See the recap skill's Step 1 |
| *Suggestions* to offer when asking the SA (never use them unconfirmed) | **Salesforce account + Vitalstatistix:** Glean `search` for `<customer>` with `app: salescloud`, result type `account`. Its text has a "Link to Vitalstatistix" field. Note this is the company's *main* LaunchDarkly account, which may not be the one for this opportunity. **Opportunities:** Glean `search` for `<customer> opportunity` (no app filter). `app: salesforce` with extra keywords returned nothing in testing |
| PS team / active projects | Glean `search` for `<customer> active projects` with `app: salesforce`. `employee_search` gives someone's role. Also check the SA handoff doc in the Drive folder |
| Support tickets they opened | Glean `search` for `<customer>` with `app: zendesk`. Also try `app: jira`, which turns up engineering tickets that mention the customer. Add `sort_by_recency` |
| Tech stack (SDKs, languages, infra) | Earlier recaps and discovery docs; Glean `search` for `<customer> SDK` or `<customer> architecture`; Glean `chat` for "What tech stack and LaunchDarkly SDKs does <customer> use?" |
| Internal Slack discussion | Glean `search` with `app: slack`, or the Slack connector |
| My Jira tickets for this customer | `acli jira workitem search --jql 'parent = <EPIC>' --fields key,summary,status --json --paginate` (search can't return `duedate`) |
| One ticket's details | `acli jira workitem view <KEY> --fields summary,status,duedate,description --json` |
| LaunchDarkly docs | LaunchDarkly MCP `search-docs` / `get-doc`, or WebFetch on `launchdarkly.com/docs` |

Vitalstatistix is an internal LaunchDarkly tool and may not be readable from here. If you
can't open it, just include its link. Don't guess what's on the page.

Never read `.env` files, `~/.config/acli/token.txt`, or anything in `~/.config/sa-skills/google/`.
