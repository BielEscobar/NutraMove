from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.schemas.auth import MasterCreate
from app.services.auth import create_master


def main() -> None:
    name = input("Nome: ")
    email = input("E-mail: ")
    password = getpass("Senha (12 a 128 caracteres): ")
    if password != getpass("Confirme a senha: "):
        raise SystemExit("As senhas não coincidem.")
    try:
        data = MasterCreate(name=name, email=email, password=password)
    except ValidationError:
        raise SystemExit("Dados inválidos. Verifique nome, e-mail e tamanho da senha.") from None
    try:
        with Session(get_engine()) as db:
            create_master(db, data)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print("MASTER criado com sucesso.")


if __name__ == "__main__":
    main()
