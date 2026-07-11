#!/usr/bin/env python3
"""Send an approved daily queue through Telegram Desktop on macOS.

This tool does not use Telegram APIs. It opens an official Telegram deep link
with a message draft and uses macOS Accessibility to press Return.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")
TRUE_VALUES = {"1", "true", "yes", "y", "да"}


class OutreachError(RuntimeError):
    pass


@dataclass(frozen=True)
class Contact:
    contact_id: str
    username: str
    enabled: bool
    opt_in: bool


@dataclass(frozen=True)
class QueueItem:
    send_date: str
    contact_id: str
    message: str

    @property
    def fingerprint(self) -> str:
        raw = f"{self.send_date}\0{self.contact_id}\0{self.message}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def parse_bool(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def clean_username(value: str) -> str:
    username = value.strip().lstrip("@")
    if not USERNAME_RE.fullmatch(username):
        raise OutreachError(f"Invalid Telegram username: {value!r}")
    return username


def load_contacts(path: Path) -> dict[str, Contact]:
    contacts: dict[str, Contact] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            contact_id = (row.get("contact_id") or "").strip()
            if not contact_id or contact_id in contacts:
                raise OutreachError(f"Missing or duplicate contact_id: {contact_id!r}")
            contacts[contact_id] = Contact(
                contact_id=contact_id,
                username=clean_username(row.get("username") or ""),
                enabled=parse_bool(row.get("enabled") or ""),
                opt_in=parse_bool(row.get("opt_in") or ""),
            )
    return contacts


def load_queue(path: Path) -> list[QueueItem]:
    items: list[QueueItem] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for line_no, row in enumerate(csv.DictReader(handle), start=2):
            send_date = (row.get("send_date") or "").strip()
            contact_id = (row.get("contact_id") or "").strip()
            message = (row.get("message") or "").strip()
            try:
                dt.date.fromisoformat(send_date)
            except ValueError as exc:
                raise OutreachError(f"Invalid send_date on line {line_no}: {send_date!r}") from exc
            if not contact_id or not message:
                raise OutreachError(f"Missing contact_id or message on line {line_no}")
            if len(message) > 3500:
                raise OutreachError(f"Message exceeds 3500 characters on line {line_no}")
            items.append(QueueItem(send_date, contact_id, message))
    return items


def read_journal(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_plan(
    contacts: dict[str, Contact],
    queue: list[QueueItem],
    journal: list[dict],
    target_date: str,
    daily_limit: int,
) -> list[tuple[Contact, QueueItem]]:
    if not 1 <= daily_limit <= 15:
        raise OutreachError("daily_limit must be between 1 and 15")

    sent_fingerprints = {
        row.get("fingerprint")
        for row in journal
        if row.get("send_date") == target_date and row.get("status") == "sent"
    }
    sent_contacts = {
        row.get("contact_id")
        for row in journal
        if row.get("send_date") == target_date and row.get("status") == "sent"
    }
    remaining = daily_limit - len(sent_contacts)
    if remaining <= 0:
        return []

    plan: list[tuple[Contact, QueueItem]] = []
    planned_contacts: set[str] = set()
    for item in queue:
        if item.send_date != target_date:
            continue
        contact = contacts.get(item.contact_id)
        if contact is None:
            raise OutreachError(f"Queue references unknown contact_id: {item.contact_id}")
        if not contact.enabled or not contact.opt_in:
            continue
        if item.fingerprint in sent_fingerprints:
            continue
        if contact.contact_id in sent_contacts or contact.contact_id in planned_contacts:
            continue
        plan.append((contact, item))
        planned_contacts.add(contact.contact_id)
        if len(plan) >= remaining:
            break
    return plan


def telegram_deep_link(username: str, message: str) -> str:
    query = urllib.parse.urlencode({"domain": username, "text": message})
    return f"tg://resolve?{query}"


def run_osascript(script: str) -> str:
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise OutreachError(result.stderr.strip() or "AppleScript failed")
    return result.stdout.strip()


def accessibility_enabled() -> bool:
    return run_osascript('tell application "System Events" to get UI elements enabled').lower() == "true"


def send_via_telegram(contact: Contact, item: QueueItem, open_delay: float) -> None:
    subprocess.run(
        ["/usr/bin/open", telegram_deep_link(contact.username, item.message)],
        check=True,
        timeout=10,
    )
    time.sleep(open_delay)
    frontmost = run_osascript(
        'tell application "System Events" to get name of first application process whose frontmost is true'
    )
    if frontmost != "Telegram":
        raise OutreachError(f"Telegram is not frontmost; found {frontmost!r}")
    run_osascript('tell application "System Events" to keystroke return')


def append_journal(path: Path, contact: Contact, item: QueueItem, status: str, error: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "send_date": item.send_date,
        "contact_id": contact.contact_id,
        "username": contact.username,
        "fingerprint": item.fingerprint,
        "status": status,
    }
    if error:
        record["error"] = error
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    limit = int(data.get("daily_limit", 15))
    if not 1 <= limit <= 15:
        raise OutreachError("daily_limit must be between 1 and 15")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--send", action="store_true", help="Actually send; default is dry-run")
    args = parser.parse_args()

    root = args.config.resolve().parent
    config = load_config(args.config.resolve())
    contacts = load_contacts(root / config.get("contacts_file", "contacts.csv"))
    queue = load_queue(root / config.get("queue_file", "queue.csv"))
    journal_path = root / config.get("journal_file", "state/sent.jsonl")
    journal = read_journal(journal_path)
    plan = build_plan(contacts, queue, journal, args.date, int(config.get("daily_limit", 15)))

    print(f"Date: {args.date}; planned: {len(plan)}; mode: {'SEND' if args.send else 'DRY-RUN'}")
    for contact, item in plan:
        preview = item.message.replace("\n", " ")[:90]
        print(f"- {contact.contact_id} (@{contact.username}): {preview}")

    if not args.send or not plan:
        return 0
    if not bool(config.get("send_enabled", False)):
        raise OutreachError("Sending is disabled in config.json")
    if sys.platform != "darwin":
        raise OutreachError("Automatic sending is supported only on macOS")
    if not accessibility_enabled():
        raise OutreachError("macOS Accessibility is not enabled for the process running this tool")

    lock_path = root / "state/run.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise OutreachError("Another outreach run is already active") from exc

        for index, (contact, item) in enumerate(plan):
            try:
                send_via_telegram(contact, item, float(config.get("open_delay_seconds", 3)))
                append_journal(journal_path, contact, item, "sent")
                print(f"Sent to {contact.contact_id}")
            except Exception as exc:
                append_journal(journal_path, contact, item, "failed", str(exc))
                raise
            if index + 1 < len(plan):
                time.sleep(float(config.get("between_messages_seconds", 30)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OutreachError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
