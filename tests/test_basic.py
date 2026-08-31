"""Runnable self-checks for logic that has no DB dependency.
    uv run python tests/test_basic.py
"""

import asyncio
import uuid

from fastapi import HTTPException

from app.ntfy import topic_for
from app.permissions import CATALOG, PROFILE_DEFAULTS
from app.routers.messages import _acting_unit
from app.routers.org_units import _col


def test_profile_seed_matches_spec_15():
    assert PROFILE_DEFAULTS["dept_default"] == {k: True for k in CATALOG}
    branch = PROFILE_DEFAULTS["branch_default"]
    assert branch["category.manage"] is False
    assert all(v for k, v in branch.items() if k != "category.manage")


def test_csv_column_aliases():
    assert _col({"name": " A "}, "name", "branch") == "A"
    assert _col({"branch_name": "B"}, "name", "branch") == "B"
    assert _col({"dept_code": "D1"}, "code", "dept") == "D1"
    assert _col({}, "password", "branch") == ""


def test_topic_uses_uuid_not_code():
    assert topic_for("11111111-1111-1111-1111-111111111111").endswith(
        "-11111111-1111-1111-1111-111111111111"
    )


class _Acct:
    def __init__(self, org_unit_id=None, is_super_admin=False):
        self.org_unit_id = org_unit_id
        self.is_super_admin = is_super_admin


class _Unit:
    def __init__(self, unit_type):
        self.id = uuid.uuid4()
        self.unit_type = unit_type


class _Db:
    """Stub: db.get(OrgUnit, pk) -> the unit handed in (or None)."""

    def __init__(self, unit=None):
        self._unit = unit

    async def get(self, _model, _pk):
        return self._unit


def _acts(account, db, as_unit):
    return asyncio.run(_acting_unit(account, db, as_unit))


def _status(account, db, as_unit):
    try:
        _acts(account, db, as_unit)
    except HTTPException as e:
        return e.status_code
    return None


def test_acting_unit_branch_dept_account_uses_own_unit():
    ou = uuid.uuid4()
    # `as` is ignored — a unit account cannot act as anyone else
    assert _acts(_Acct(org_unit_id=ou), _Db(_Unit("dept")), str(uuid.uuid4())) == ou


def test_acting_unit_non_super_without_unit_is_forbidden():
    assert _status(_Acct(), _Db(), None) == 403


def test_acting_unit_super_admin_must_name_a_unit():
    assert _status(_Acct(is_super_admin=True), _Db(), None) == 422


def test_acting_unit_super_admin_rejects_non_dept():
    assert _status(_Acct(is_super_admin=True), _Db(_Unit("branch")), str(uuid.uuid4())) == 422
    assert _status(_Acct(is_super_admin=True), _Db(None), str(uuid.uuid4())) == 422


def test_acting_unit_super_admin_accepts_dept():
    dept = _Unit("dept")
    assert _acts(_Acct(is_super_admin=True), _Db(dept), str(uuid.uuid4())) == dept.id


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("all passed")
