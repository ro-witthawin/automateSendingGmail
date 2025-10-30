import os
import base64
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from app.email_utils import gmail_service, build_message, send_message, parse_recipients

load_dotenv()

app = FastAPI(title="FastAPI Gmail Sender", version="1.0")

class SendEmailJSON(BaseModel):
    sender: Optional[str] = None  # default to DELEGATED_USER if omitted
    to: List[str]
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/send", response_class=JSONResponse)
async def send_email_json(payload: SendEmailJSON):
    """Send email with JSON body (no file attachments)."""
    try:
        service = gmail_service()
        sender = payload.sender or os.getenv("DELEGATED_USER")
        if not sender:
            raise HTTPException(status_code=500, detail="DELEGATED_USER not set")

        if not payload.text_body and not payload.html_body:
            raise HTTPException(status_code=400, detail="Provide text_body or html_body")

        msg = build_message(
            sender=sender,
            to=payload.to,
            subject=payload.subject,
            html_body=payload.html_body or (payload.text_body or ""),
            text_body=payload.text_body,
            cc=payload.cc,
            bcc=payload.bcc,
            attachments=None,
        )
        result = send_message(service, msg)
        return {"message_id": result.get("id"), "labelIds": result.get("labelIds", [])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-form", response_class=JSONResponse)
async def send_email_form(
    sender: Optional[str] = Form(None),
    to: str = Form(...),  # comma or space separated
    subject: str = Form(...),
    text_body: Optional[str] = Form(None),
    html_body: Optional[str] = Form(None),
    cc: Optional[str] = Form(None),
    bcc: Optional[str] = Form(None),
    attachments: Optional[List[UploadFile]] = File(None),
):
    """Send email via multipart/form-data with optional file attachments.

    Example form fields:
    - to: "a@x.com,b@y.com" or "a@x.com b@y.com"
    - cc / bcc: same format
    - attachments: one or more files
    """
    # print(attachments)
    attachments = [f for f in (attachments or []) if getattr(f, "filename", "")]
    print(attachments)
    try:
        print("A")
        if not text_body and not html_body:
            raise HTTPException(status_code=400, detail="Provide text_body or html_body")

        service = gmail_service()
        _sender = sender or os.getenv("DELEGATED_USER")
        if not _sender:
            raise HTTPException(status_code=500, detail="DELEGATED_USER not set")

        to_list = parse_recipients(to)
        cc_list = parse_recipients(cc) if cc else None
        bcc_list = parse_recipients(bcc) if bcc else None
        print("B")
        # Prepare attachments as (filename, content_type, bytes)
        att_payloads = []
        print(attachments)
        if attachments:
            for up in attachments:
                data = await up.read()
                att_payloads.append((up.filename, up.content_type, data))

        msg = build_message(
            sender=_sender,
            to=to_list,
            subject=subject,
            html_body=html_body or (text_body or ""),
            text_body=text_body,
            cc=cc_list,
            bcc=bcc_list,
            attachments=att_payloads,
        )
        result = send_message(service, msg)
        return {"message_id": result.get("id"), "labelIds": result.get("labelIds", [])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))