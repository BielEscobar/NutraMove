"""Create local demo logins without changing existing accounts."""

from secrets import token_urlsafe

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models import User
from app.schemas.auth import MasterCreate
from app.schemas.professional import ProfessionalCreate
from app.services.auth import create_master
from app.services.professionals import create as create_professional


def main() -> None:
    if get_settings().environment != "development":
        raise SystemExit("Demo accounts are only allowed in development.")

    accounts = [
        ("MASTER", "master.demo@example.com", "Master Demo"),
        ("PROFESSIONAL", "professional.demo@example.com", "Professional Demo"),
    ]
    with Session(get_engine()) as db:
        for role, email, name in accounts:
            existing = db.scalar(select(User).where(User.email == email))
            if existing is not None:
                print(f"Already exists: {email}. Password and account unchanged.")
                continue
            password = SecretStr(token_urlsafe(18))
            if role == "MASTER":
                create_master(db, MasterCreate(name=name, email=email, password=password))
            else:
                create_professional(
                    db,
                    ProfessionalCreate(
                        name=name, email=email, password=password, specialty="Demonstracao"
                    ),
                )
            # Display once to the operator; passwords are never written to files.
            print(f"CREATED {role} {email} {password.get_secret_value()}")


if __name__ == "__main__":
    main()
