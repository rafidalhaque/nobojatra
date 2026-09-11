from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import AccountDep, DbDep
from app.models import Account, Comment, Post
from app.schemas import CommentIn, CommentOut

router = APIRouter(tags=["comments"])


def _owns(account: Account, comment: Comment) -> bool:
    return account.is_super_admin or comment.org_unit_id == account.org_unit_id


async def _get_visible_post(post_id: str, db: DbDep) -> Post:
    post = await db.get(Post, post_id)
    if post is None:  # RLS hides drafts you can't see -> 404, same as GET /posts/{id}
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return post


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
async def list_comments(post_id: str, _: AccountDep, db: DbDep):
    await _get_visible_post(post_id, db)
    rows = await db.scalars(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at)
    )
    return list(rows)


@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(post_id: str, body: CommentIn, account: AccountDep, db: DbDep):
    if account.org_unit_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Comments are per org unit")
    await _get_visible_post(post_id, db)
    comment = Comment(post_id=post_id, org_unit_id=account.org_unit_id, body=body.body)
    db.add(comment)
    await db.flush()
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: str, account: AccountDep, db: DbDep):
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if not _owns(account, comment):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your comment")
    await db.delete(comment)
