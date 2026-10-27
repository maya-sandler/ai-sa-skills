# Customer folder template

To set up a new customer, create `{{CUSTOMERS_DIR}}/<customer-slug>/` containing only a
`CLAUDE.md` like the one below. Recaps, prep briefs and transcripts are saved to each
opportunity's Drive folder, not here.

Fill in only links that came from the SA's prompt, the opportunity's Drive folder, or the SA's
answer. Don't add Salesforce or Vitalstatistix links found by searching Glean unless the SA has
confirmed them. Slack channels come only from the SA's answer: never search for them.

```markdown
# <Customer>

Customer folder for <Customer>. Use the `customer-meeting-recap`, `customer-session-prep` and
`customer-engagement-prep` skills here. Everything they produce is saved as Google Docs in the opportunity's Drive folder.
Nothing is saved locally except this file.

Never read `.env` files, `~/.config/acli/token.txt`, or anything in `~/.config/sa-skills/google/`.

## Customer-wide
- Jira: project {{JIRA_PROJECT}} on {{JIRA_SITE}}
- Jira epic: <KEY, filled in by the recap skill>

## Opportunities
Each opportunity has its own links. Only use links from the entry for the opportunity you're
working on. For a new opportunity, add a new entry and ask the SA whether to reuse each link
from an existing one or use a new one.

### <Offering> opportunity (<n>)
- Salesforce opportunity: <url>
- Drive folder: https://drive.google.com/drive/folders/<FOLDER_ID>
- Drive folder ID: <FOLDER_ID>
- Vitalstatistix: <url>
- Session plan: <url or "not found yet">
- SA handoff: <url>

## Slack
The customer's Slack channels and chats, from the SA. The skills read them for context since the
last call, and never name or link them in a Doc or ticket. Write `none` if there are none.
- Shared customer channel: <link> (ID <C…>)
- Internal account channel: <link> (ID <C…>)
- Group DM: <link> (ID <C… or G…>)

## Team
- LaunchDarkly: <SA name> (SA), <AE> (AE), <CSM>, <PS>
- Customer: <name> (<role>), ...

## Calls
- Latest call: <recording link> (<YYYY-MM-DD>, <opportunity name>)

## Tech stack (known so far)
<languages · LD SDKs · warehouse · infra · integrations>
```

Name each opportunity `<Offering> opportunity`, adding `(<n>)` when the same offering repeats,
for example:

```
### RSA50 opportunity (1)
### RSA100 opportunity
### RSA50 opportunity (2)
```
