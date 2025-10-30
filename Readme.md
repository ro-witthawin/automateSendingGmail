# FastAPI Gmail Sender (Service Account + DWD)

A small FastAPI service that sends emails through **Gmail API** using a **Google Workspace service account with domain-wide delegation (DWD)**.
It supports:

* JSON request (no attachments)
* `multipart/form-data` request (with one or more attachments)
* HTML and/or plain text body
* `to`, `cc`, `bcc` recipients
* Sending **as** a delegated Workspace user

---

## 1. Features

* ✅ Uses **service account** + **delegated user** (Google Workspace)
* ✅ `/send-form` → send by form + attachments
* ✅ Multiple recipients (comma or space separated)
* ✅ Works with Gmail API scope: `https://www.googleapis.com/auth/gmail.send`

---

## 2. Project Structure

```text
.
├── app
│   ├── main.py          # FastAPI endpoints
│   └── email_utils.py   # Gmail helper functions
├── requirements.txt
├── .env.example
└── Dockerfile
```

---

## 3. Prerequisites (Google Workspace)

You need **a Google Cloud service account** that can impersonate a Workspace user.

1. **Create a Service Account** in Google Cloud Console.
2. **Enable Gmail API** for your project.
3. In the service account settings, **enable domain-wide delegation**.
4. Go to **Google Admin Console** (admin.google.com) →
   **Security → Access and data control → API controls → Domain-wide delegation** → Add new:

   * **Client ID**: the **Unique ID** of the service account
   * **Scopes**:

     ```text
     https://www.googleapis.com/auth/gmail.send
     ```
5. Make sure the user you will delegate to (e.g. `you@your-edu-domain.ac.th`) is a real user in your Workspace and is allowed to send mail.

> Note: If your organization enforces **“Disable service account key creation”**, you must ask an org admin to create the key for you or set up another credential path. The code itself expects a path to the service account JSON.

---

## 4. Environment Variables

Copy `.env.example` to `.env` and edit:

```env
SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
DELEGATED_USER=you@your-edu-domain.ac.th
```

**Meaning:**

* `SERVICE_ACCOUNT_FILE`: local path to the service account JSON key.
* `DELEGATED_USER`: the Workspace user you want to “send as”.

---

## 5. Install & Run (local)

```bash
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

# run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Now the API is available at:
[http://localhost:8000](http://localhost:8000)

Open the docs at:
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## 6. API Endpoints

### 6.1 `GET /health`

Simple healthcheck.

**Response:**

```json
{"status": "ok"}
```

---

### 6.2 `POST /send-form` (multipart, with attachments)

Send an email and upload files in the same request.

**Request:**

```http
POST /send-form
Content-Type: multipart/form-data
```

**Form fields:**

* `to` (required) — `a@x.com,b@y.com` or `a@x.com b@y.com`
* `subject` (required)
* `text_body` (optional)
* `html_body` (optional)
* `cc` (optional, same format as `to`)
* `bcc` (optional)
* `attachments` (optional, **can repeat**)

**curl example:**

```bash
curl -X POST http://localhost:8000/send-form \
  -F "to=recipient@example.com" \
  -F "subject=Attach test" \
  -F "text_body=See attachment" \
  -F "attachments=@/path/to/file1.pdf" \
  -F "attachments=@/path/to/image.png"
```

**What happens inside:**

* FastAPI reads each uploaded file as bytes.
* We pass a list of **tuples** to the Gmail builder:

  ```python
  (filename, content_type, data_bytes)
  ```
* The message is built with proper MIME types.
* Gmail API sends it on behalf of `DELEGATED_USER` (or the `sender` you passed).

---

## 7. Code Notes

### 7.1 `app/email_utils.py` (core idea)

* Create Gmail service from service account:

  ```python
  from google.oauth2 import service_account
  from googleapiclient.discovery import build

  SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

  def gmail_service():
      creds = service_account.Credentials.from_service_account_file(
          SERVICE_ACCOUNT_FILE, scopes=SCOPES
      )
      delegated = creds.with_subject(DELEGATED_USER)
      return build("gmail", "v1", credentials=delegated)
  ```

* Build a message that accepts **both**:

  * path-based attachments (`["/tmp/a.pdf"]`)
  * in-memory form upload (`[("a.pdf", "application/pdf", b"...")]`)

This is what fixed the error you saw:

> `expected str, bytes or os.PathLike object, not tuple`

because form uploads give you tuples, not file paths.

---

## 8. Docker (local build)

Here’s a Dockerfile that runs the app:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build:**

```bash
docker build -t fastapi-gmail-sender .
```

**Run:**

```bash
docker run -p 8000:8000 \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/service-account.json:/secrets/service-account.json:ro \
  -e SERVICE_ACCOUNT_FILE=/secrets/service-account.json \
  fastapi-gmail-sender
```

---

## 9. Troubleshooting

* **401 / 403 errors** → usually DWD not set, wrong scope, or SA not authorized in Admin Console.
* **“Precondition check failed”** → the delegated user cannot send mail or Gmail is disabled.
* **“expected str, bytes or os.PathLike object, not tuple”** → you passed form-upload tuples to a function that expected file paths. The current version in this project already handles both.
* **Org policy “Disable service account key creation”** → ask your Workspace / Cloud admin to create the key or allow you to create it for this service account.

---

That’s it. This README is focused only on **what the service does, how to run it locally, and how to call it** — no Cloud Run deploy steps included.
