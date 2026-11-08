import os
from contextlib import contextmanager
from datetime import date
from typing import Self

from werkzeug.exceptions import Forbidden
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from .app import app

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@contextmanager
def xaction():
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

class Proposal(db.Model, MappedAsDataclass):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    summary: Mapped[str] = mapped_column(unique=False)
    adopted: Mapped[date | None] = mapped_column(default=None, unique=False)

    @property
    def git_ref(self) -> str:
        return f'proposal_{self.id}'

    @classmethod
    def add(cls, summary: str) -> Self:
        self = cls(summary=summary)
        with xaction() as s:
            s.add(self)
        return self

    @classmethod
    def get(cls, id: int) -> Self:
        return db.get_or_404(cls, id)

    def delete(self) -> None:
        with xaction() as s:
            s.delete(self)

    @classmethod
    def _base_query(cls):
        return db.select(cls).order_by(cls.adopted.desc().nulls_first())
    @classmethod
    def _exec(cls, query) -> list[Self]:
        return list(db.session.execute(query).scalars())

    @classmethod
    def page(cls, offset: int = 0, limit: int = 20) -> list[Self]:
        return cls._exec(cls._base_query().offset(offset).limit(limit))

    @classmethod
    def since(cls, before: date, limit: int = 20) -> list[Self]:
        return cls._exec(cls._base_query().where(cls.adopted > before).limit(limit))

class AllowedUser(db.Model, MappedAsDataclass):
    email: Mapped[str] = mapped_column(primary_key=True)

    @classmethod
    def add(cls, email: str) -> Self:
        self = cls(email=email)
        with xaction() as s:
            s.add(self)
        return self

    @classmethod
    def has_or_403(cls, email: str) -> None:
        if db.get(cls, email) is None:
            raise Forbidden('Not on allowed users list')

with app.app_context():
    db.create_all()
