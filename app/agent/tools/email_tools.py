import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import re

from imap_tools import AND, MailBox
from langchain_core.tools import tool

from app.config import settings


def _imap_ready() -> bool:
    return bool(settings.imap_host and settings.imap_user and settings.imap_password)


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip())
    return cleaned.strip("_") or "untitled"


def _safe_filename(name: str, fallback: str = "file.bin") -> str:
    raw = (name or fallback).strip()
    raw = re.sub(r"[\\/:*?\"<>|]+", "_", raw)
    raw = raw.replace("\x00", "")
    return raw or fallback


def _strip_html(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", no_tags).strip()


def _fetch_email_by_uid(uid: str, folder: str) -> tuple[dict[str, str], object | None]:
    try:
        with MailBox(settings.imap_host).login(
            settings.imap_user,
            settings.imap_password,
            folder,
        ) as mailbox:
            rows = list(mailbox.fetch(AND(uid=uid), mark_seen=False))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}, None

    if not rows:
        return {"status": "not_found", "message": "Email not found", "uid": uid}, None

    return {"status": "ok"}, rows[0]


@tool
def list_unread_emails(limit: int = 5, sender: str | None = None) -> str:
    """List unread emails from IMAP account."""
    if not _imap_ready():
        return json.dumps(
            {
                "status": "not_configured",
                "message": "IMAP settings are missing in .env",
            }
        )

    criteria = AND(seen=False)
    if sender:
        criteria = AND(seen=False, from_=sender)

    results: list[dict[str, str]] = []
    try:
        with MailBox(settings.imap_host).login(
            settings.imap_user,
            settings.imap_password,
            settings.imap_folder,
        ) as mailbox:
            for msg in mailbox.fetch(criteria, limit=limit, reverse=True, mark_seen=False):
                results.append(
                    {
                        "uid": msg.uid,
                        "subject": msg.subject or "",
                        "sender": msg.from_ or "",
                        "date": str(msg.date),
                    }
                )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"status": "error", "message": str(exc)})

    return json.dumps({"status": "ok", "emails": results})


@tool
def summarize_email(uid: str) -> str:
    """Fetch one email body by UID and return a truncated text."""
    if not _imap_ready():
        return json.dumps(
            {
                "status": "not_configured",
                "message": "IMAP settings are missing in .env",
            }
        )

    try:
        with MailBox(settings.imap_host).login(
            settings.imap_user,
            settings.imap_password,
            settings.imap_folder,
        ) as mailbox:
            rows = list(mailbox.fetch(AND(uid=uid), mark_seen=False))
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"status": "error", "message": str(exc)})

    if not rows:
        return json.dumps({"status": "not_found", "message": "Email not found", "uid": uid})

    body = rows[0].text or rows[0].html or ""
    return json.dumps({"status": "ok", "uid": uid, "body_preview": body[:3000]})


@tool
def extract_action_items_from_email(uid: str) -> str:
    """Extract likely action items and deadline-like patterns from an email body."""
    if not _imap_ready():
        return json.dumps(
            {"status": "not_configured", "message": "IMAP settings are missing in .env"}
        )

    meta, msg = _fetch_email_by_uid(uid, settings.imap_folder)
    if not msg:
        return json.dumps(meta)

    body = (msg.text or _strip_html(msg.html or "") or "").strip()
    if not body:
        return json.dumps({"status": "ok", "uid": uid, "action_items": [], "deadlines": []})

    keyword_re = re.compile(
        r"\b(please|lütfen|todo|action|gerek|yap|tamamla|deadline|until|by)\b",
        re.IGNORECASE,
    )
    date_re = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)\b")

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    candidates: list[str] = []
    for line in lines:
        if keyword_re.search(line):
            candidates.append(line)

    if not candidates:
        chunks = re.split(r"(?<=[.!?])\s+", body)
        for chunk in chunks:
            clean = chunk.strip()
            if clean and keyword_re.search(clean):
                candidates.append(clean)

    unique_actions: list[str] = []
    seen = set()
    for item in candidates:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique_actions.append(item)

    deadlines = sorted(set(date_re.findall(body)))
    return json.dumps(
        {
            "status": "ok",
            "uid": uid,
            "action_items": unique_actions[:20],
            "deadlines": deadlines,
        },
        ensure_ascii=False,
    )


@tool
def list_attachments(uid: str) -> str:
    """List attachment metadata for an email by UID."""
    if not _imap_ready():
        return json.dumps(
            {"status": "not_configured", "message": "IMAP settings are missing in .env"}
        )

    meta, msg = _fetch_email_by_uid(uid, settings.imap_folder)
    if not msg:
        return json.dumps(meta)

    attachment_rows: list[dict[str, str | int]] = []
    for idx, attachment in enumerate(getattr(msg, "attachments", []) or [], start=1):
        payload = getattr(attachment, "payload", b"") or b""
        filename = _safe_filename(getattr(attachment, "filename", "") or f"attachment_{idx}.bin")
        content_type = getattr(attachment, "content_type", "application/octet-stream") or "application/octet-stream"
        attachment_rows.append(
            {
                "index": idx,
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(payload),
            }
        )

    return json.dumps(
        {"status": "ok", "uid": uid, "attachments": attachment_rows, "count": len(attachment_rows)},
        ensure_ascii=False,
    )


@tool
def save_emails_by_topic(topic: str, max_results: int = 20, output_dir: str = "email_exports") -> str:
    """Search emails by topic and save outputs in a topic/date folder structure."""
    if not _imap_ready():
        return json.dumps(
            {
                "status": "not_configured",
                "message": "IMAP settings are missing in .env",
            }
        )

    criteria = AND(text=topic)
    results: list[dict[str, str]] = []

    try:
        with MailBox(settings.imap_host).login(
            settings.imap_user,
            settings.imap_password,
            settings.imap_folder,
        ) as mailbox:
            for msg in mailbox.fetch(criteria, limit=max_results, reverse=True, mark_seen=False):
                results.append(
                    {
                        "uid": msg.uid,
                        "subject": msg.subject or "",
                        "sender": msg.from_ or "",
                        "date": str(msg.date),
                    }
                )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"status": "error", "message": str(exc)})

    now = datetime.now()
    topic_slug = _slug(topic)
    day_folder = now.strftime("%Y-%m-%d")
    batch_folder = now.strftime("%H%M%S")
    export_root = Path(output_dir) / topic_slug / day_folder / batch_folder
    export_root.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    for index, item in enumerate(results, start=1):
        safe_uid = _slug(item.get("uid", f"item_{index}"))
        file_path = export_root / f"{index:03d}_{safe_uid}.json"
        file_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        saved_files.append(str(file_path))

    index_path = export_root / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "topic": topic,
                "saved_count": len(results),
                "generated_at": now.isoformat(timespec="seconds"),
                "files": saved_files,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return json.dumps(
        {
            "status": "ok",
            "topic": topic,
            "saved_count": len(results),
            "folder_path": str(export_root),
            "index_file": str(index_path),
        }
    )


@tool
def save_attachments_by_topic(topic: str, max_results: int = 20, output_dir: str = "email_exports") -> str:
    """Save attachments from topic-matching emails to topic/date/time folder structure."""
    if not _imap_ready():
        return json.dumps(
            {"status": "not_configured", "message": "IMAP settings are missing in .env"}
        )

    criteria = AND(text=topic)
    now = datetime.now()
    topic_slug = _slug(topic)
    root = Path(output_dir) / "attachments" / topic_slug / now.strftime("%Y-%m-%d") / now.strftime("%H%M%S")
    root.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    scanned_messages = 0
    try:
        with MailBox(settings.imap_host).login(
            settings.imap_user,
            settings.imap_password,
            settings.imap_folder,
        ) as mailbox:
            for msg in mailbox.fetch(criteria, limit=max_results, reverse=True, mark_seen=False):
                scanned_messages += 1
                uid_folder = root / _slug(msg.uid or f"msg_{scanned_messages}")
                uid_folder.mkdir(parents=True, exist_ok=True)

                for idx, attachment in enumerate(getattr(msg, "attachments", []) or [], start=1):
                    payload = getattr(attachment, "payload", b"") or b""
                    filename = _safe_filename(
                        getattr(attachment, "filename", "") or f"attachment_{idx}.bin"
                    )
                    file_path = uid_folder / f"{idx:02d}_{filename}"
                    file_path.write_bytes(payload)
                    saved_files.append(str(file_path))
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"status": "error", "message": str(exc)})

    index_path = root / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "topic": topic,
                "generated_at": now.isoformat(timespec="seconds"),
                "scanned_messages": scanned_messages,
                "saved_attachments": len(saved_files),
                "files": saved_files,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return json.dumps(
        {
            "status": "ok",
            "topic": topic,
            "folder_path": str(root),
            "saved_attachments": len(saved_files),
            "index_file": str(index_path),
        },
        ensure_ascii=False,
    )


@tool
def draft_email_in_user_style(
    purpose: str,
    recipient_name: str = "",
    tone: str = "formal",
    max_sent_samples: int = 30,
) -> str:
    """Create a draft email using simple style signals extracted from sent emails."""
    if not _imap_ready():
        return json.dumps(
            {"status": "not_configured", "message": "IMAP settings are missing in .env"}
        )

    greetings: list[str] = []
    closings: list[str] = []
    vocab_counter: Counter[str] = Counter()

    word_re = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü']{3,}")
    try:
        with MailBox(settings.imap_host).login(
            settings.imap_user,
            settings.imap_password,
            settings.imap_sent_folder,
        ) as mailbox:
            for msg in mailbox.fetch(AND(all=True), limit=max_sent_samples, reverse=True, mark_seen=False):
                body = msg.text or _strip_html(msg.html or "") or ""
                lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
                if lines:
                    greetings.append(lines[0][:120])
                    closings.append(lines[-1][:120])
                vocab_counter.update(word_re.findall(body.lower()))
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"status": "error", "message": str(exc)})

    common_greeting = Counter(greetings).most_common(1)[0][0] if greetings else "Merhaba,"
    common_closing = Counter(closings).most_common(1)[0][0] if closings else "Saygilariyla,"
    top_vocab = [word for word, _ in vocab_counter.most_common(8)]

    greeting_line = common_greeting
    if recipient_name:
        greeting_line = f"Merhaba {recipient_name},"

    tone = tone.lower().strip()
    if tone == "friendly":
        body_line = f"{purpose} konusunda kisa bir mesaj birakmak istedim."
    elif tone == "concise":
        body_line = f"{purpose} konusunda kisa not: geri donusunu bekliyorum."
    else:
        body_line = f"{purpose} konusunda bilgilendirme paylasmak isterim."

    draft = (
        f"{greeting_line}\n\n"
        f"{body_line}\n"
        f"Uygun oldugunda geri donusunu rica ederim.\n\n"
        f"{common_closing}"
    )

    return json.dumps(
        {
            "status": "ok",
            "draft": draft,
            "style_profile": {
                "sample_count": len(greetings),
                "common_greeting": common_greeting,
                "common_closing": common_closing,
                "top_vocabulary": top_vocab,
            },
        },
        ensure_ascii=False,
    )
