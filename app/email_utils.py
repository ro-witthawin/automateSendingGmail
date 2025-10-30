import os
import base64
from email.message import EmailMessage
from mimetypes import guess_type
from typing import List, Optional, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def gmail_service():
    service_account_file = os.getenv("SERVICE_ACCOUNT_FILE")
    delegated_user = os.getenv("DELEGATED_USER")
    if not service_account_file:
        raise RuntimeError("SERVICE_ACCOUNT_FILE not set")
    if not delegated_user:
        raise RuntimeError("DELEGATED_USER not set")

    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    delegated = creds.with_subject(delegated_user)
    return build("gmail", "v1", credentials=delegated)


def _ensure_ctype(filename: str, content_type: Optional[str]) -> Tuple[str, str]:
    if content_type:
        maintype, subtype = content_type.split("/", 1)
        return maintype, subtype
    ctype, encoding = guess_type(filename)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    return ctype.split("/", 1)[0], ctype.split("/", 1)[1]


def build_message(
    sender: str,
    to: List[str] | str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    # Accept EITHER a list of file paths (str) OR a list of in-memory tuples
    attachments: Optional[List[Tuple[str, Optional[str], bytes]] | List[str]] = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to) if isinstance(to, list) else to
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        # Header optional; Gmail API will still deliver to BCCs
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject

    if text_body:
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
    else:
        msg.set_content(html_body, subtype="html")

    # Handle attachments
    for att in attachments or []:
        # Path-like (backward compatible with path-based API)
        if isinstance(att, str):
            from mimetypes import guess_type as _guess
            ctype, encoding = _guess(att)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(att, "rb") as f:
                msg.add_attachment(
                    f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(att)
                )
        else:
            # Tuple: (filename, content_type|None, bytes)
            filename, content_type, data = att
            maintype, subtype = _ensure_ctype(filename, content_type)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    return msg


def send_message(service, message: EmailMessage):
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


def parse_recipients(raw: str) -> List[str]:
    if not raw:
        return []
    # split on comma or space, strip empties
    parts = [p.strip() for p in raw.replace("\n", " ").replace("\t", " ").replace(",", " ").split(" ")]
    return [p for p in parts if p]