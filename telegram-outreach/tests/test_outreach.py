import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram_outreach import Contact, OutreachError, QueueItem, build_plan, clean_username, telegram_deep_link


class OutreachTests(unittest.TestCase):
    def setUp(self):
        self.contacts = {
            "a": Contact("a", "valid_user", True, True),
            "b": Contact("b", "second_user", True, False),
            "c": Contact("c", "third_user", False, True),
        }

    def test_only_enabled_opted_in_contacts_are_planned(self):
        queue = [
            QueueItem("2026-01-01", "a", "Hello"),
            QueueItem("2026-01-01", "b", "No opt-in"),
            QueueItem("2026-01-01", "c", "Disabled"),
        ]
        plan = build_plan(self.contacts, queue, [], "2026-01-01", 15)
        self.assertEqual([item.contact_id for _, item in plan], ["a"])

    def test_one_message_per_contact_per_day(self):
        queue = [
            QueueItem("2026-01-01", "a", "First"),
            QueueItem("2026-01-01", "a", "Second"),
        ]
        plan = build_plan(self.contacts, queue, [], "2026-01-01", 15)
        self.assertEqual(len(plan), 1)

    def test_journal_prevents_duplicate(self):
        item = QueueItem("2026-01-01", "a", "Hello")
        journal = [{
            "send_date": "2026-01-01",
            "contact_id": "a",
            "fingerprint": item.fingerprint,
            "status": "sent",
        }]
        self.assertEqual(build_plan(self.contacts, [item], journal, "2026-01-01", 15), [])

    def test_limit_is_enforced(self):
        contacts = {
            str(i): Contact(str(i), f"valid_user_{i}", True, True)
            for i in range(20)
        }
        queue = [QueueItem("2026-01-01", str(i), f"Message {i}") for i in range(20)]
        self.assertEqual(len(build_plan(contacts, queue, [], "2026-01-01", 10)), 10)
        with self.assertRaises(OutreachError):
            build_plan(contacts, queue, [], "2026-01-01", 16)

    def test_deep_link_contains_encoded_draft(self):
        link = telegram_deep_link("valid_user", "Привет & hello")
        self.assertTrue(link.startswith("tg://resolve?"))
        self.assertIn("domain=valid_user", link)
        self.assertIn("%26", link)

    def test_username_validation(self):
        self.assertEqual(clean_username("@valid_user"), "valid_user")
        with self.assertRaises(OutreachError):
            clean_username("bad user")


if __name__ == "__main__":
    unittest.main()
