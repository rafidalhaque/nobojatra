import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


# ---- auth / me ----
class LoginIn(BaseModel):
    username: str
    password: str


class MeOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    username: str
    is_super_admin: bool
    org_unit_id: uuid.UUID | None
    theme_pref: Literal["light", "dark"]
    lang_pref: Literal["en", "bn"]


class PreferencesIn(BaseModel):
    theme_pref: Literal["light", "dark"] | None = None
    lang_pref: Literal["en", "bn"] | None = None


# ---- areas ----
class AreaIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AreaOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    name: str
    created_at: dt.datetime


# ---- org units ----
class OrgUnitIn(BaseModel):
    unit_type: Literal["branch", "dept"]
    name: str = Field(min_length=1, max_length=300)
    code: str = Field(min_length=1, max_length=120)
    area_id: uuid.UUID
    password: str = Field(min_length=1)


class OrgUnitPatch(BaseModel):
    name: str | None = Field(default=None, max_length=300)
    code: str | None = Field(default=None, max_length=120)
    area_id: uuid.UUID | None = None


class OrgUnitOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    unit_type: Literal["branch", "dept"]
    name: str
    code: str
    area_id: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime


class ImportRowError(BaseModel):
    row: int
    errors: list[str]


class ImportResult(BaseModel):
    created: int


# ---- categories ----
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class CategoryOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    name: str
    created_at: dt.datetime


# ---- posts ----
class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    body: str = ""
    category_id: uuid.UUID
    status: Literal["draft", "published"] = "draft"
    created_at: dt.datetime | None = None  # user-fillable; None -> row timestamp


class PostPatch(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    body: str | None = None
    category_id: uuid.UUID | None = None
    created_at: dt.datetime | None = None


class MediaOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    original_filename: str
    content_type: str | None
    size_bytes: int
    sort_order: int


class PostOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    org_unit_id: uuid.UUID
    category_id: uuid.UUID
    title: str
    body: str
    status: Literal["draft", "published"]
    created_at: dt.datetime
    updated_at: dt.datetime
    published_at: dt.datetime | None
    media: list[MediaOut]


class PostPage(BaseModel):
    items: list[PostOut]
    total: int
    page: int
    size: int


# ---- messages ----
class MessageIn(BaseModel):
    recipient_org_unit_id: uuid.UUID
    body: str = Field(min_length=1)


class MessageOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    sender_org_unit_id: uuid.UUID
    recipient_org_unit_id: uuid.UUID
    body: str
    created_at: dt.datetime
    read_at: dt.datetime | None


class ConversationOut(BaseModel):
    org_unit_id: uuid.UUID
    last_body: str
    last_at: dt.datetime
    unread: int


# ---- notifications ----
class NotificationOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    type: str
    title: str
    body: str
    source_type: str | None
    source_id: uuid.UUID | None
    status: Literal["read", "unread"]
    created_at: dt.datetime
    read_at: dt.datetime | None


# ---- permission matrix (admin panel) ----
class PermissionOut(BaseModel):
    key: str
    description: str


class MatrixIn(BaseModel):
    # {permission_key: allowed}  — for a profile: full set. for a unit: null clears override.
    permissions: dict[str, bool]


class UnitMatrixIn(BaseModel):
    permissions: dict[str, bool | None]


class EffectiveMatrixOut(BaseModel):
    unit_type: Literal["branch", "dept"]
    effective: dict[str, bool]
    overrides: dict[str, bool]
