from enum import Enum
import os
from contextlib import contextmanager
from datetime import date
import subprocess
from typing import NamedTuple, Self

from werkzeug.exceptions import Forbidden, NotFound
from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy import ForeignKey, PickleType, select
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, MappedAsDataclass,
    mapped_column
)

from mds_to_html import Section

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

    def user_update(self, summary: str | None = None) -> None:
        with xaction():
            if summary:
                self.summary = summary

    def update(
        self, summary: str | None = None,
        base_ref: str | None = None,
        # NOTE: although `adopted` is nullable, it should never be
        # updated from non-null to null. Thus this default is fine.
        adopted: date | None = None,
    ) -> None:
        with xaction():
            if summary:
                self.summary = summary
            if base_ref:
                self.base_ref = base_ref
            if adopted:
                self.adopted = adopted

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

class Ref(NamedTuple):
    chapter: int
    section: int
    subsection: int
    subsubsection: int
    subsubsubsection: int

    def __composite_values__(self):
        return (
            self.chapter, self.section, self.subsection,
            self.subsubsection, self.subsubsubsection
        )

    def __str__(self) -> str:
        return '-'.join(str(i) for i in self if i >= 0)

    @classmethod
    def from_frag(cls, frag: str) -> Self:
        parts = list(map(int, frag.split('-')))
        parts[len(parts)-5:] = [-1] * (5 - len(parts))
        return cls(*parts)

class AmendmentOp(Enum):
    INSERT = 'insert'
    DELETE = 'delete'
    REPLACE = 'replace'

class Amendment(Model):
    __tablename__ = 'amendments'

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    proposal: Mapped[int] = mapped_column(ForeignKey(Proposal.id))
    path: Mapped[str] = mapped_column(unique=False)
    # the section reference for the ORIGINAL section.
    # INSERT ops insert *after* this section
    # REPLACE/DELETE ops replace/delete this section
    ref: Mapped[str] = mapped_column(unique=False)
    # technically redundant, but useful
    lineno: Mapped[int] = mapped_column(unique=False)
    op: Mapped[AmendmentOp] = mapped_column(unique=False)
    # None for DELETE ops
    content: Mapped[list[Section] | None] = mapped_column(PickleType, unique=False)

    @classmethod
    def add(
        cls, proposal: Proposal, path: str, ref: Ref, lineno: int,
        op: AmendmentOp, section: list[Section] | None
    ) -> Self:
        self = cls(proposal.id, path, str(ref), lineno, op, section)
        with xaction() as s:
            s.add(self)
        return self

    @classmethod
    def get_all(cls, proposal: Proposal) -> list[Self]:
        return list(db.session.execute(
            select(cls).where(cls.proposal == proposal.id)
        ).scalars())
    @classmethod
    def get_for_file(cls, proposal: Proposal, path: str) -> list[Self]:
        return list(db.session.execute(
            select(cls).where(cls.proposal == proposal.id, cls.path == path)
            .order_by(cls.lineno.desc())
        ).scalars())

    def delete(self) -> None:
        with xaction() as s:
            s.delete(self)

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
