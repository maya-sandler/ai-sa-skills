# ai-sa-skills

Claude Code skills for Solutions Architects who work with customers.

| Skill | What it does |
|---|---|
| `customer-meeting-recap` | Turns a customer call (Gong link or transcript) into a recap Google Doc in the customer's Drive folder, and creates Jira tickets for the team's follow-ups under the customer's epic |
| `customer-session-prep` | Writes a one-page prep brief for the next customer session as a Google Doc: status, what's owed, open questions, support tickets, tech stack |

Both run in **Claude Code** (the desktop app's Code tab or a terminal), not the desktop app's
Chat tab. They use Glean for reading, the Atlassian CLI (`acli`) for Jira, and a small Drive
helper with your own Google sign-in for writing Docs.

## Get started

```bash
git clone <this repo's URL>
```

```bash
cd ai-sa-skills && ./install.sh
```

The installer asks where to put the skills and your customer folders, and which Jira site and
project to use. Then follow [ACCESS-AND-SETUP.md](ACCESS-AND-SETUP.md) to sign in to Jira and
Google Drive (about 25 minutes, once).

## Rules for this repo

- **No customer data or links.** No customer names, customer or internal links, or account IDs,
  anywhere: skills, examples, docs or commit messages. Use made-up examples (`Acme`, `Alex`,
  `KEY-123`).
- **No credentials.** Tokens, client secrets and personal settings live in each person's
  `~/.config/`, never in the repo.
- **Edit `claude-code/`, then rerun `./install.sh`.** The installed copies get replaced on every
  install.
