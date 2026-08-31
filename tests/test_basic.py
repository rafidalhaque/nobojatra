"""Runnable self-checks for logic that has no DB dependency.
    uv run python tests/test_basic.py
"""

from app.ntfy import topic_for
from app.permissions import CATALOG, PROFILE_DEFAULTS
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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("all passed")
