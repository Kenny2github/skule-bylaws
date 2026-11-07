from contextlib import contextmanager
from datetime import date
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from .app import app

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Proposal(db.Model, MappedAsDataclass):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    summary: Mapped[str] = mapped_column(unique=False)
    adopted: Mapped[date | None] = mapped_column(default=None, unique=False)

    @property
    def git_ref(self) -> str:
        return f'proposal_{self.id}'

with app.app_context():
    db.create_all()

@contextmanager
def xaction():
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

def new_proposal(summary: str) -> Proposal:
    proposal = Proposal(summary=summary)
    with xaction() as s:
        s.add(proposal)
    return proposal
