import datetime as dt
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, text

from app import ntfy, storage
from app.deps import AccountDep, DbDep, require_permission
from app.models import Account, Category, Notification, OrgUnit, Post, PostMedia
from app.schemas import MediaOut, PostIn, PostOut, PostPage, PostPatch

router = APIRouter(tags=["posts"])


def _owns(account: Account, post: Post) -> bool:
    return account.is_super_admin or post.org_unit_id == account.org_unit_id


async def _get_owned(post_id: str, account: Account, db: DbDep) -> Post:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if not _owns(account, post):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your post")
    return post


async def _fan_out_notifications(post_id: str, author_unit_id, title: str) -> None:
    """v1 trigger: a published post notifies every other org unit. DB rows are
    authoritative; ntfy is best-effort push."""
    from app.db import SessionLocal

    async with SessionLocal() as db:
        # background task has no request identity; run it with the super-admin
        # bypass so the notifications WITH CHECK passes for every recipient.
        await db.execute(text("SELECT set_config('app.is_super_admin', 'on', true)"))
        unit_ids = list(
            await db.scalars(select(OrgUnit.id).where(OrgUnit.id != author_unit_id))
        )
        db.add_all(
            Notification(
                recipient_org_unit_id=uid,
                type="post.published",
                title=title,
                body="",
                source_type="post",
                source_id=post_id,
            )
            for uid in unit_ids
        )
        await db.commit()
    for uid in unit_ids:
        await ntfy.publish(uid, "New notice", title)


@router.get("/posts", response_model=PostPage)
async def list_posts(
    _: AccountDep,
    db: DbDep,
    q: str | None = None,
    category: str | None = None,
    date_from: dt.datetime | None = None,
    date_to: dt.datetime | None = None,
    posted_by: str | None = None,
    status_: str | None = None,
    page: int = 1,
    size: int = 20,
):
    # RLS already limits rows to published + own drafts + (super = all).
    stmt = select(Post)
    if q:
        stmt = stmt.where(Post.search_tsv.op("@@")(func.websearch_to_tsquery("simple", q)))
    if category:
        stmt = stmt.where(Post.category_id == category)
    if posted_by:
        stmt = stmt.where(Post.org_unit_id == posted_by)
    if date_from:
        stmt = stmt.where(Post.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Post.created_at <= date_to)
    if status_ in ("draft", "published"):
        stmt = stmt.where(Post.status == status_)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    size = max(1, min(size, 100))
    page = max(1, page)
    rows = await db.scalars(
        stmt.order_by(Post.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    return PostPage(items=list(rows), total=total or 0, page=page, size=size)


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: PostIn,
    bg: BackgroundTasks,
    account: Account = Depends(require_permission("post.create")),
    db: DbDep = None,
):
    if account.org_unit_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super Admin posts via an org unit only")
    if await db.get(Category, body.category_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown category")

    post = Post(
        org_unit_id=account.org_unit_id,
        category_id=body.category_id,
        title=body.title,
        body=body.body,
        status=body.status,
    )
    if body.created_at is not None:
        post.created_at = body.created_at
    if body.status == "published":
        post.published_at = dt.datetime.now(dt.UTC)
    db.add(post)
    await db.flush()
    if post.status == "published":
        bg.add_task(_fan_out_notifications, str(post.id), account.org_unit_id, post.title)
    return post


@router.get("/posts/{post_id}", response_model=PostOut)
async def get_post(post_id: str, _: AccountDep, db: DbDep):
    post = await db.get(Post, post_id)
    if post is None:  # RLS hides drafts you can't see -> 404
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return post


@router.patch("/posts/{post_id}", response_model=PostOut)
async def edit_post(
    post_id: str,
    body: PostPatch,
    account: Account = Depends(require_permission("post.edit")),
    db: DbDep = None,
):
    post = await _get_owned(post_id, account, db)
    if body.category_id is not None:
        if await db.get(Category, body.category_id) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown category")
        post.category_id = body.category_id
    if body.title is not None:
        post.title = body.title
    if body.body is not None:
        post.body = body.body
    if body.created_at is not None:
        post.created_at = body.created_at
    await db.flush()
    return post


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    account: Account = Depends(require_permission("post.delete")),
    db: DbDep = None,
):
    post = await _get_owned(post_id, account, db)
    for m in post.media:
        storage.delete(m.s3_key)
    await db.delete(post)


@router.post("/posts/{post_id}/publish", response_model=PostOut)
async def publish_post(
    post_id: str,
    bg: BackgroundTasks,
    account: Account = Depends(require_permission("post.publish")),
    db: DbDep = None,
):
    post = await _get_owned(post_id, account, db)
    was_draft = post.status == "draft"
    post.status = "published"
    if post.published_at is None:
        post.published_at = dt.datetime.now(dt.UTC)
    await db.flush()
    if was_draft:
        bg.add_task(_fan_out_notifications, str(post.id), post.org_unit_id, post.title)
    return post


@router.post("/posts/{post_id}/media", response_model=list[MediaOut])
async def upload_media(
    post_id: str,
    files: list[UploadFile],
    account: Account = Depends(require_permission("post.edit")),
    db: DbDep = None,
):
    post = await _get_owned(post_id, account, db)
    start = len(post.media)
    out: list[PostMedia] = []
    for idx, f in enumerate(files):
        key = storage.put(f.file, f.content_type)
        size = f.size or 0
        m = PostMedia(
            post_id=post.id,
            s3_key=key,
            original_filename=f.filename or "file",
            content_type=f.content_type,
            size_bytes=size,
            sort_order=start + idx,
        )
        db.add(m)
        out.append(m)
    await db.flush()
    return out


@router.delete("/posts/{post_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    post_id: str,
    media_id: str,
    account: Account = Depends(require_permission("post.edit")),
    db: DbDep = None,
):
    post = await _get_owned(post_id, account, db)
    m = await db.get(PostMedia, media_id)
    if m is None or m.post_id != post.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    storage.delete(m.s3_key)
    await db.delete(m)


# Types safe to render in the browser. Anything else is forced to download as an
# opaque blob so a mislabeled text/html or script-bearing SVG can't execute in
# this origin (the SPA and this API share one origin). Uploads are still accepted
# unrestricted (spec 5) — this only governs how bytes are served back.
_INLINE_OK = ("image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf")


@router.get("/media/{media_id}")
async def get_media(media_id: str, _: AccountDep, db: DbDep):
    """Auth-gated proxy. No public S3 URLs are ever issued (spec 11.2)."""
    m = await db.get(PostMedia, media_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # visibility rides on the parent post's RLS
    if await db.get(Post, m.post_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    chunks, content_type, length = storage.open_stream(m.s3_key)

    ct = (content_type or "").split(";")[0].strip().lower()
    inline = ct in _INLINE_OK
    served_type = ct if inline else "application/octet-stream"
    filename = quote(m.original_filename or "file", safe="")

    headers = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        # neutralizes any HTML/SVG that slips through, even if rendered inline
        "Content-Security-Policy": "default-src 'none'; sandbox; base-uri 'none'",
        "Content-Disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{filename}",
    }
    if length is not None:
        headers["Content-Length"] = str(length)
    return StreamingResponse(chunks, media_type=served_type, headers=headers)
