import os
from contextlib import contextmanager
from datetime import date
import subprocess
from typing import Self

from werkzeug.exceptions import Forbidden, NotFound
from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy import select
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, MappedAsDataclass,
    mapped_column
)

from .app import app

app.config['SQLALCHEMY_ENGINES'] = {'default': os.environ['DB_URI']}
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

class Model(DeclarativeBase, MappedAsDataclass):
    pass

class Proposal(Model):
    __tablename__ = 'proposals'

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    summary: Mapped[str] = mapped_column(unique=False)
    base_ref: Mapped[str] = mapped_column(unique=False)
    adopted: Mapped[date | None] = mapped_column(default=None, unique=False)

    @classmethod
    def add(cls, summary: str) -> Self:
        content = subprocess.check_output(
            ['git', 'rev-parse', 'master'],
            stderr=subprocess.STDOUT, encoding='utf8'
        )
        self = cls(summary=summary, base_ref=content.strip())
        with xaction() as s:
            s.add(self)
        return self

    @classmethod
    def get_or_404(cls, id: int) -> Self:
        self = db.session.get(cls, id)
        if self is None:
            raise NotFound()
        return self

    def delete(self) -> None:
        with xaction() as s:
            s.delete(self)

    @classmethod
    def _base_query(cls):
        return select(cls).order_by(cls.adopted.desc().nulls_first())
    @classmethod
    def _exec(cls, query) -> list[Self]:
        return list(db.session.execute(query).scalars())

    @classmethod
    def page(cls, offset: int = 0, limit: int = 20) -> list[Self]:
        return cls._exec(cls._base_query().offset(offset).limit(limit))

    @classmethod
    def since(cls, before: date, limit: int = 20) -> list[Self]:
        return cls._exec(cls._base_query().where(cls.adopted > before).limit(limit))

class AllowedUser(Model):
    __tablename__ = 'allowed_users'

    email: Mapped[str] = mapped_column(primary_key=True)

    @classmethod
    def add(cls, email: str) -> Self:
        self = cls(email=email)
        with xaction() as s:
            s.add(self)
        return self

    @classmethod
    def has_or_403(cls, email: str) -> None:
        if db.session.get(cls, email) is None:
            raise Forbidden('Not on allowed users list')

with app.app_context():
    Model.metadata.create_all(db.engine)
