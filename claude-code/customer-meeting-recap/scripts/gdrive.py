#!/usr/bin/env python3
"""Save Markdown as Google Docs in a customer's Drive folder, and read them back.

Uses your own OAuth client (Desktop app) with the drive.file scope: it can only see and
change files it created itself, so it can't touch anything else in your Drive.

Setup files (never commit or share them; Claude never reads them):
  ~/.config/sa-skills/google/client_secret.json   your OAuth client, downloaded from Google Cloud
  ~/.config/sa-skills/google/token.json           created on first sign-in

Commands:
  gdrive.py setup-client                           paste your OAuth client ID and secret (run it yourself)
  gdrive.py login                                 sign in (opens a browser once)
  gdrive.py save --folder ID --name NAME --file X.md   create the Doc, or update it if NAME exists
  gdrive.py list --folder ID [--contains TEXT]     Docs this tool created in the folder
  gdrive.py read --id DOC_ID                       print a Doc as Markdown

Every command prints JSON.
"""
import argparse
import json
import os
import sys

CONFIG_DIR = os.path.expanduser(os.environ.get("SA_SKILLS_GOOGLE_DIR", "~/.config/sa-skills/google"))
CLIENT_SECRET = os.path.join(CONFIG_DIR, "client_secret.json")
TOKEN = os.path.join(CONFIG_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DOC_MIME = "application/vnd.google-apps.document"

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except ImportError:
    sys.exit("Google libraries missing. Run: ~/.local/share/sa-skills/venv/bin/pip install "
             "google-api-python-client google-auth-oauthlib")


def fail(msg):
    print(json.dumps({"error": msg}))
    sys.exit(1)


def setup_client():
    """Write client_secret.json from a pasted client ID and secret. The secret isn't echoed."""
    import getpass
    client_id = input("OAuth Client ID (ends in .apps.googleusercontent.com): ").strip()
    secret = getpass.getpass("OAuth Client secret (hidden while you paste): ").strip()
    if not client_id.endswith(".apps.googleusercontent.com") or not secret:
        fail("that doesn't look like a Desktop OAuth client ID and secret; nothing was saved")
    client = {"installed": {"client_id": client_id, "client_secret": secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": ["http://localhost"]}}
    os.makedirs(CONFIG_DIR, exist_ok=True)
    fd = os.open(CLIENT_SECRET, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(client, f)
    print(json.dumps({"saved": CLIENT_SECRET}))


def credentials(interactive):
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    if not (creds and creds.valid):
        if not interactive:
            fail("not signed in to Google Drive: run gdrive.py login")
        if not os.path.exists(CLIENT_SECRET):
            fail("missing %s: see ACCESS-AND-SETUP.md, Google Drive section" % CLIENT_SECRET)
        creds = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES).run_local_server(port=0)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    fd = os.open(TOKEN, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(creds.to_json())
    return creds


def drive(interactive=False):
    return build("drive", "v3", credentials=credentials(interactive), cache_discovery=False)


def find(svc, folder, name=None, contains=None):
    q = ["'%s' in parents" % folder, "trashed = false", "mimeType = '%s'" % DOC_MIME]
    if name:
        q.append("name = '%s'" % name.replace("\\", "\\\\").replace("'", "\\'"))
    if contains:
        q.append("name contains '%s'" % contains.replace("\\", "\\\\").replace("'", "\\'"))
    res = svc.files().list(q=" and ".join(q), orderBy="modifiedTime desc", pageSize=100,
                           fields="files(id,name,modifiedTime,webViewLink)",
                           supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    return res.get("files", [])


def save(svc, folder, name, path):
    media = MediaFileUpload(path, mimetype="text/markdown", resumable=False)
    existing = find(svc, folder, name=name)
    if existing:
        f = svc.files().update(fileId=existing[0]["id"], media_body=media,
                               fields="id,name,webViewLink", supportsAllDrives=True).execute()
        f["action"] = "updated"
    else:
        meta = {"name": name, "mimeType": DOC_MIME, "parents": [folder]}
        f = svc.files().create(body=meta, media_body=media, fields="id,name,webViewLink",
                               supportsAllDrives=True).execute()
        f["action"] = "created"
    return f


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup-client")
    sub.add_parser("login")
    s = sub.add_parser("save")
    s.add_argument("--folder", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--file", required=True)
    l = sub.add_parser("list")
    l.add_argument("--folder", required=True)
    l.add_argument("--contains")
    r = sub.add_parser("read")
    r.add_argument("--id", required=True)
    a = p.parse_args()

    if a.cmd == "setup-client":
        setup_client()
        return
    try:
        if a.cmd == "login":
            about = drive(interactive=True).about().get(fields="user(emailAddress)").execute()
            print(json.dumps({"signed_in_as": about["user"]["emailAddress"]}))
        elif a.cmd == "save":
            print(json.dumps(save(drive(), a.folder, a.name, a.file)))
        elif a.cmd == "list":
            print(json.dumps(find(drive(), a.folder, contains=a.contains)))
        elif a.cmd == "read":
            data = drive().files().export(fileId=a.id, mimeType="text/markdown").execute()
            print(data.decode("utf-8") if isinstance(data, bytes) else data)
    except HttpError as e:
        status = getattr(e.resp, "status", None)
        hint = ""
        if status == 404:
            hint = " (folder not found or you can't add files to it)"
        elif status == 403:
            hint = " (no permission: check you can edit this folder, and that the Drive API is enabled)"
        fail("Google API %s%s: %s" % (status, hint, e))


if __name__ == "__main__":
    main()
