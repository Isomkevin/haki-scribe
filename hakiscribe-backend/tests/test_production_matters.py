"""Production (org-scoped) matters, contacts, routing and connector tenancy."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

from fastapi import HTTPException

from app.services.production_matters import ProductionMattersRepo
from tests.fake_supabase import FakeSupabase

BACKEND = Path(__file__).resolve().parents[1]


class ProductionMattersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeSupabase()
        self.org, self.other_org = uuid4(), uuid4()
        self.workspace = uuid4()
        self.owner, self.lawyer, self.outsider = str(uuid4()), str(uuid4()), str(uuid4())
        self.db.tables["haki_memberships"] = [
            {"organisation_id": str(self.org), "user_id": self.owner, "role": "owner", "status": "active"},
            {"organisation_id": str(self.org), "user_id": self.lawyer, "role": "lawyer", "status": "active"},
            {"organisation_id": str(self.other_org), "user_id": self.outsider, "role": "owner", "status": "active"},
        ]

    def repo(self, user, org=None):
        return ProductionMattersRepo(self.db, org or self.org, user)

    def test_create_matter_adds_creator_membership_and_client_contact(self):
        matter = self.repo(self.lawyer).create_matter(
            client_name="Acme Ltd", matter_name="Acme v Kenya Power", workspace_id=self.workspace
        )
        memberships = self.db.tables["haki_matter_memberships"]
        self.assertEqual(memberships, [{"matter_id": str(matter.id), "user_id": self.lawyer, "role": "lawyer", "id": memberships[0]["id"], "created_at": memberships[0]["created_at"]}])
        self.assertEqual(len(matter.contact_ids), 1)
        contact = self.repo(self.lawyer).get_contact(matter.contact_ids[0])
        self.assertEqual((contact.name, contact.updates["role"]), ("Acme Ltd", "client"))

    def test_matter_visibility_follows_membership_and_firm_roles(self):
        mine = self.repo(self.lawyer).create_matter(client_name="A", matter_name="Mine", workspace_id=self.workspace)
        theirs = self.repo(self.owner).create_matter(client_name="B", matter_name="Owner's", workspace_id=self.workspace)
        self.assertEqual([m.id for m in self.repo(self.lawyer).list_matters()], [mine.id])
        self.assertEqual({m.id for m in self.repo(self.owner).list_matters()}, {mine.id, theirs.id})
        with self.assertRaises(HTTPException) as ctx:
            self.repo(self.lawyer).get_matter(theirs.id)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_other_organisation_sees_nothing_and_cannot_link(self):
        matter = self.repo(self.owner).create_matter(client_name="A", matter_name="M", workspace_id=self.workspace)
        outsider = self.repo(self.outsider, self.other_org)
        self.assertEqual(outsider.list_matters(), [])
        self.assertEqual(outsider.list_contacts(), [])
        with self.assertRaises(HTTPException):
            outsider.get_matter(matter.id)
        with self.assertRaises(HTTPException):
            outsider.create_contact(name="Spy", matter_id=matter.id)
        with self.assertRaises(HTTPException):
            outsider.get_contact(matter.contact_ids[0])
        with self.assertRaises(HTTPException):
            outsider.update_contact(matter.contact_ids[0], name="renamed")

    def test_contact_update_checks_matter_and_sessions_in_org(self):
        repo = self.repo(self.owner)
        matter = repo.create_matter(client_name="A", matter_name="M", workspace_id=self.workspace)
        contact = repo.create_contact(name="Witness", updates={"phone": "0700"})
        own_session, foreign_session = uuid4(), uuid4()
        self.db.tables["haki_sessions"] = [
            {"id": str(own_session), "organisation_id": str(self.org), "matter_id": None},
            {"id": str(foreign_session), "organisation_id": str(self.other_org), "matter_id": None},
        ]
        updated = repo.update_contact(
            contact.id, updates={"phone": "", "email": "w@x.ke"}, matter_id=matter.id, session_ids=[own_session]
        )
        self.assertEqual(updated.updates, {"email": "w@x.ke"})
        self.assertEqual((updated.matter_id, updated.session_ids), (matter.id, [own_session]))
        with self.assertRaises(HTTPException):
            repo.update_contact(contact.id, session_ids=[foreign_session])
        cleared = repo.update_contact(contact.id, clear_matter=True)
        self.assertIsNone(cleared.matter_id)

    def test_create_matter_links_session_only_within_org(self):
        own_session, foreign_session = uuid4(), uuid4()
        self.db.tables["haki_sessions"] = [
            {"id": str(own_session), "organisation_id": str(self.org), "matter_id": None},
            {"id": str(foreign_session), "organisation_id": str(self.other_org), "matter_id": None},
        ]
        matter = self.repo(self.owner).create_matter(
            client_name="A", matter_name="M", workspace_id=self.workspace, session_id=own_session
        )
        self.assertEqual(matter.session_ids, [own_session])
        with self.assertRaises(HTTPException):
            self.repo(self.owner).create_matter(
                client_name="B", matter_name="N", workspace_id=self.workspace, session_id=foreign_session
            )


class ConnectorTenancyTests(unittest.TestCase):
    def test_deployment_connectors_only_for_configured_org(self):
        from app.routers.production_hearings import _require_connector_org

        org = uuid4()
        with mock.patch.dict(os.environ, {"HAKISCRIBE_INTEGRATIONS_ORGANISATION_ID": ""}):
            with self.assertRaises(HTTPException) as ctx:
                _require_connector_org(org)
            self.assertEqual(ctx.exception.status_code, 403)
        with mock.patch.dict(os.environ, {"HAKISCRIBE_INTEGRATIONS_ORGANISATION_ID": str(uuid4())}):
            with self.assertRaises(HTTPException):
                _require_connector_org(org)
        with mock.patch.dict(os.environ, {"HAKISCRIBE_INTEGRATIONS_ORGANISATION_ID": str(org).upper()}):
            _require_connector_org(org)


class ProductionRoutingTests(unittest.TestCase):
    def test_list_routes_are_not_captured_by_session_routes(self):
        """GET /production/hearings used to hit GET /production/{session_id} (422)."""
        # With auth stubbed, the right route reaches production_client() and answers
        # 503 (no database in tests); the session route would answer 422 (not a UUID).
        script = (
            "from types import SimpleNamespace\n"
            "from uuid import uuid4\n"
            "from fastapi.testclient import TestClient\n"
            "from app.main import app\n"
            "from app.services import tenant_context\n"
            "user = SimpleNamespace(id=str(uuid4()), email='a@b.ke', aal='aal2')\n"
            "app.dependency_overrides[tenant_context.require_organisation] = lambda: (user, uuid4())\n"
            "client = TestClient(app)\n"
            "for path in ('/production/hearings', '/production/matters', '/production/contacts', "
            "'/production/hearings/pending-confirm'):\n"
            "    r = client.get(path)\n"
            "    print(path, r.status_code)\n"
        )
        env = {
            **os.environ,
            "HAKISCRIBE_PRODUCTION_AUTH": "true",
            "HAKISCRIBE_JOB_WORKER": "false",
            "SUPABASE_URL": "",
            "SUPABASE_SERVICE_KEY": "",
        }
        out = subprocess.run(
            [sys.executable, "-c", script], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120
        )
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        statuses = dict(line.split(" ", 1) for line in out.stdout.strip().splitlines())
        self.assertEqual(
            statuses,
            {
                "/production/hearings": "503",
                "/production/matters": "503",
                "/production/contacts": "503",
                "/production/hearings/pending-confirm": "503",
            },
        )
