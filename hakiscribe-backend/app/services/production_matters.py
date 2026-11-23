"""Org-scoped matters and contacts for production auth (ADR-012 b).

The demo /matters and /contacts routers share one snapshot store, so they are
never mounted in production. This repository is their production
counterpart: every query is filtered by the organisation that
tenant_context.require_organisation verified, and matter visibility follows
the haki_matters RLS policy (matter members, plus the firm's owners/admins).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException

from app.models.schemas import Contact, ContactWithSessions, Matter

FIRM_WIDE_ROLES = ("owner", "admin")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid_list(values: Any) -> list[UUID]:
    return [UUID(str(v)) for v in (values or [])]


class ProductionMattersRepo:
    def __init__(self, client: Any, organisation_id: UUID, user_id: str):
        self.client = client
        self.organisation_id = organisation_id
        self.user_id = user_id

    # -- visibility -------------------------------------------------------

    def _firm_wide(self) -> bool:
        result = (
            self.client.table("haki_memberships").select("role")
            .eq("organisation_id", str(self.organisation_id)).eq("user_id", self.user_id)
            .eq("status", "active").in_("role", list(FIRM_WIDE_ROLES)).execute()
        )
        return bool(result.data)

    def _member_matter_ids(self) -> set[str]:
        result = self.client.table("haki_matter_memberships").select("matter_id").eq("user_id", self.user_id).execute()
        return {str(r["matter_id"]) for r in (result.data or [])}

    def _org_matter_rows(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("haki_matters").select("*")
            .eq("organisation_id", str(self.organisation_id)).order("created_at", desc=True).execute()
        )
        return list(result.data or [])

    def _visible_matter_rows(self) -> list[dict[str, Any]]:
        rows = self._org_matter_rows()
        if self._firm_wide():
            return rows
        mine = self._member_matter_ids()
        return [r for r in rows if str(r["id"]) in mine]

    def _matter_row(self, matter_id: UUID) -> dict[str, Any]:
        for row in self._visible_matter_rows():
            if str(row["id"]) == str(matter_id):
                return row
        raise HTTPException(status_code=404, detail="Matter not found")

    # -- matters ----------------------------------------------------------

    def _to_matter(self, row: dict[str, Any], sessions: list[dict[str, Any]], contacts: list[dict[str, Any]]) -> Matter:
        mid = str(row["id"])
        linked_at = row.get("hakichain_linked_at")
        return Matter(
            id=UUID(mid),
            client_name=row["client_name"],
            matter_name=row["matter_name"],
            session_ids=[UUID(str(s["id"])) for s in sessions if str(s.get("matter_id")) == mid],
            contact_ids=[UUID(str(c["id"])) for c in contacts if str(c.get("matter_id")) == mid],
            hakichain_client_id=row.get("hakichain_client_id"),
            hakichain_workspace_id=row.get("hakichain_workspace_id"),
            hakichain_linked_at=linked_at,
            created_at=row.get("created_at") or _now(),
        )

    def link_hakichain(
        self,
        matter_id: UUID,
        *,
        hakichain_client_id: str,
        hakichain_workspace_id: str,
    ) -> Matter:
        self._matter_row(matter_id)
        updated = (
            self.client.table("haki_matters")
            .update(
                {
                    "hakichain_client_id": hakichain_client_id,
                    "hakichain_workspace_id": hakichain_workspace_id,
                    "hakichain_linked_at": _now(),
                }
            )
            .eq("id", str(matter_id))
            .eq("organisation_id", str(self.organisation_id))
            .execute()
        )
        if not updated.data:
            raise HTTPException(status_code=500, detail="Could not link HakiChain matter")
        return self.get_matter(matter_id)

    def _org_sessions(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("haki_sessions").select("id, matter_id")
            .eq("organisation_id", str(self.organisation_id)).execute()
        )
        return list(result.data or [])

    def _org_contact_rows(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("haki_contacts").select("*")
            .eq("organisation_id", str(self.organisation_id)).order("created_at", desc=True).execute()
        )
        return list(result.data or [])

    def list_matters(self) -> list[Matter]:
        rows = self._visible_matter_rows()
        sessions, contacts = self._org_sessions(), self._org_contact_rows()
        return [self._to_matter(r, sessions, contacts) for r in rows]

    def get_matter(self, matter_id: UUID) -> Matter:
        row = self._matter_row(matter_id)
        return self._to_matter(row, self._org_sessions(), self._org_contact_rows())

    def create_matter(
        self, *, client_name: str, matter_name: str, workspace_id: UUID, session_id: Optional[UUID] = None
    ) -> Matter:
        client_name, matter_name = client_name.strip(), matter_name.strip()
        if not client_name or not matter_name:
            raise HTTPException(status_code=400, detail="client_name and matter_name are required")
        inserted = (
            self.client.table("haki_matters").insert(
                {
                    "organisation_id": str(self.organisation_id),
                    "workspace_id": str(workspace_id),
                    "client_name": client_name,
                    "matter_name": matter_name,
                    "created_by": self.user_id,
                }
            ).execute()
        )
        if not inserted.data:
            raise HTTPException(status_code=500, detail="Could not create matter")
        row = inserted.data[0]
        # The creator must be able to see the matter under the RLS policy too.
        self.client.table("haki_matter_memberships").insert(
            {"matter_id": str(row["id"]), "user_id": self.user_id, "role": "lawyer"}
        ).execute()
        if session_id:
            self._link_session(session_id, UUID(str(row["id"])))
        self.create_contact(
            name=client_name,
            updates={"role": "client", "source": "matters_endpoint"},
            matter_id=UUID(str(row["id"])),
            session_id=session_id,
            dedupe=True,
        )
        return self.get_matter(UUID(str(row["id"])))

    def _link_session(self, session_id: UUID, matter_id: UUID) -> None:
        result = (
            self.client.table("haki_sessions").update({"matter_id": str(matter_id)})
            .eq("id", str(session_id)).eq("organisation_id", str(self.organisation_id)).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")

    # -- contacts ---------------------------------------------------------

    def _to_contact(self, row: dict[str, Any]) -> ContactWithSessions:
        session_ids = _uuid_list(row.get("session_ids"))
        return ContactWithSessions(
            id=UUID(str(row["id"])),
            name=row["name"],
            updates=row.get("updates") or {},
            matter_id=UUID(str(row["matter_id"])) if row.get("matter_id") else None,
            session_id=session_ids[0] if session_ids else None,
            created_at=row.get("created_at") or _now(),
            session_ids=session_ids,
        )

    def _contact_row(self, contact_id: UUID) -> dict[str, Any]:
        result = (
            self.client.table("haki_contacts").select("*")
            .eq("id", str(contact_id)).eq("organisation_id", str(self.organisation_id)).limit(1).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Contact not found")
        return result.data[0]

    def _check_session(self, session_id: UUID) -> None:
        result = (
            self.client.table("haki_sessions").select("id")
            .eq("id", str(session_id)).eq("organisation_id", str(self.organisation_id)).limit(1).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")

    def list_contacts(self, *, matter_id: Optional[UUID] = None) -> list[ContactWithSessions]:
        rows = self._org_contact_rows()
        if matter_id is not None:
            rows = [r for r in rows if str(r.get("matter_id")) == str(matter_id)]
        return [self._to_contact(r) for r in rows]

    def get_contact(self, contact_id: UUID) -> ContactWithSessions:
        return self._to_contact(self._contact_row(contact_id))

    def create_contact(
        self,
        *,
        name: str,
        updates: Optional[dict[str, Any]] = None,
        matter_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        dedupe: bool = False,
    ) -> Contact:
        name = name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        if matter_id is not None:
            self._matter_row(matter_id)
        if session_id is not None:
            self._check_session(session_id)
        if dedupe:
            for row in self._org_contact_rows():
                if row["name"].strip().lower() == name.lower() and str(row.get("matter_id")) == str(matter_id):
                    return self._to_contact(row)
        inserted = (
            self.client.table("haki_contacts").insert(
                {
                    "organisation_id": str(self.organisation_id),
                    "matter_id": str(matter_id) if matter_id else None,
                    "name": name,
                    "updates": dict(updates or {}),
                    "session_ids": [str(session_id)] if session_id else [],
                    "created_by": self.user_id,
                }
            ).execute()
        )
        if not inserted.data:
            raise HTTPException(status_code=500, detail="Could not create contact")
        return self._to_contact(inserted.data[0])

    def update_contact(
        self,
        contact_id: UUID,
        *,
        name: Optional[str] = None,
        updates: Optional[dict[str, Any]] = None,
        matter_id: Optional[UUID] = None,
        clear_matter: bool = False,
        session_ids: Optional[list[UUID]] = None,
    ) -> ContactWithSessions:
        self._contact_row(contact_id)
        patch: dict[str, Any] = {"updated_at": _now()}
        if name is not None and name.strip():
            patch["name"] = name.strip()
        if updates is not None:
            patch["updates"] = {k: v for k, v in updates.items() if not (isinstance(v, str) and not v.strip())}
        if clear_matter:
            patch["matter_id"] = None
        elif matter_id is not None:
            self._matter_row(matter_id)
            patch["matter_id"] = str(matter_id)
        if session_ids is not None:
            for sid in session_ids:
                self._check_session(sid)
            patch["session_ids"] = [str(sid) for sid in dict.fromkeys(session_ids)]
        result = (
            self.client.table("haki_contacts").update(patch)
            .eq("id", str(contact_id)).eq("organisation_id", str(self.organisation_id)).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Contact not found")
        return self._to_contact(result.data[0])
