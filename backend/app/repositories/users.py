from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(db: Session, email: str, *, for_update: bool = False) -> User | None:
    query = select(User).where(User.email == email.lower().strip())
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)
