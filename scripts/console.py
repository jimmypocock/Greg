#!/usr/bin/env python3
"""
Greg Database Console

Rails-like helpers for interacting with the database.

Usage:
    uv run greg console
    uv run greg db

Commands:
    all(Model)              Get all records
    first(Model)            Get first record
    last(Model, n=1)        Get last N records
    find(Model, id)         Find by primary key
    where(Model, **kwargs)  Filter by attributes
    count(Model)            Count records
    save(obj)               Save or update record
    destroy(obj)            Delete record
    reload(obj)             Refresh from database
    commit()                Commit transaction
    rollback()              Rollback transaction

    pp(obj)                 Pretty print all attributes (like Rails)
    attrs(obj)              Get dict of all attributes

Examples:
    >>> all(User)
    [<User jimmy@example.com>, ...]

    >>> first(Song)
    <Song "My Song">

    >>> last(Song, 5)
    [<Song "Recent">, <Song "Another">, ...]

    >>> find(User, "550e8400-e29b-41d4-a716-446655440000")
    <User jimmy@example.com>

    >>> where(User, is_active=True)
    [<User jimmy@example.com>]

    >>> where(Invite, is_active=True, type=InviteType.REFERRAL)
    [<Invite code="abc123">]

    >>> count(Song)
    42

    >>> u = first(User)
    >>> u.plan = UserPlan.PRO
    >>> save(u)
    Saved User

    >>> destroy(first(Invite))
    Deleted Invite

    >>> s = first(Song)
    >>> s.sections  # Access relationships
    [<SongSection Verse 1>, <SongSection Chorus>]

    >>> pp(first(User))  # See all attributes (like Rails)
    #User
      id         : UUID('abc123...')
      email      : 'jimmy@example.com'
      role       : <UserRole.ADMIN: 'admin'>
      plan       : <UserPlan.PRO: 'pro'>
      ...

    >>> attrs(first(Song))  # Get as dict
    {'id': UUID('...'), 'title': 'My Song', ...}

Raw SQLAlchemy queries:
    >>> db.query(User).filter(User.email.like("%@gmail%")).all()
    >>> db.query(Song).order_by(Song.created_at.desc()).limit(10).all()
    >>> db.query(Song).join(SongSection).filter(SongSection.type == SectionType.CHORUS).all()

Available Models:
    Core:       User, Invite, APIKey, RefreshToken, AIRequest
    Documents:  Document, DocumentChunk
    Songs:      Song, SongSection, SectionVersion, Line, ChordPlacement
    Metadata:   SongNote, AudioFile, AgentReview, ChatMessage
    Sharing:    SongCollaborator, SongShareLink, YjsDocument

Enums:
    UserRole, UserPlan, InviteType, SongStatus, SectionType,
    NoteType, CollaboratorRole, AnalysisStatus, AgentType, AgentTaskType
"""

import code
import os
import readline
import rlcompleter

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database setup
database_url = os.environ.get("DATABASE_URL", "postgresql://greg:greg@localhost:5433/greg")
sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
if not sync_url.startswith("postgresql+psycopg2://"):
    sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

engine = create_engine(sync_url)
Session = sessionmaker(bind=engine)
db = Session()

# Import all models from database
from api.database.models import (
    # Core
    APIKey,
    AIRequest,
    Document,
    DocumentChunk,
    DocumentStatus,
    EmbeddingProvider,
    Invite,
    InviteType,
    LLMProvider,
    PLAN_CREDITS,
    RefreshToken,
    RequestType,
    User,
    UserPlan,
    UserRole,
    # Songs
    AgentReview,
    AudioFile,
    ChatMessage,
    ChordPlacement,
    Line,
    SectionVersion,
    Song,
    SongCollaborator,
    SongNote,
    SongSection,
    SongShareLink,
    YjsDocument,
)
from api.enums import (
    AgentTaskType,
    AgentType,
    AnalysisStatus,
    CollaboratorRole,
    NoteType,
    SectionType,
    SongStatus,
)


# =============================================================================
# Rails-like Helpers
# =============================================================================


def all(model):
    """Get all records."""
    return db.query(model).all()


def first(model):
    """Get first record."""
    return db.query(model).first()


def last(model, n=1):
    """Get last N records (by id)."""
    results = db.query(model).order_by(model.id.desc()).limit(n).all()
    return results[0] if n == 1 else results


def find(model, id):
    """Find by primary key."""
    return db.query(model).get(id)


def where(model, **kwargs):
    """Filter by attributes."""
    return db.query(model).filter_by(**kwargs).all()


def count(model):
    """Count records."""
    return db.query(model).count()


def save(obj):
    """Save or update a record."""
    db.add(obj)
    db.commit()
    db.refresh(obj)
    print(f"Saved {obj.__class__.__name__}")
    return obj


def destroy(obj):
    """Delete a record."""
    db.delete(obj)
    db.commit()
    print(f"Deleted {obj.__class__.__name__}")


def reload(obj):
    """Refresh object from database."""
    db.refresh(obj)
    return obj


def commit():
    """Commit current transaction."""
    db.commit()
    print("Committed.")


def rollback():
    """Rollback current transaction."""
    db.rollback()
    print("Rolled back.")


def sql(query):
    """Execute raw SQL."""
    return db.execute(text(query)).fetchall()


def attrs(obj):
    """Get dict of all column attributes (excludes relationships and internal state)."""
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(obj.__class__)
    return {c.key: getattr(obj, c.key) for c in mapper.columns}


def pp(obj):
    """Pretty print all attributes of a model (like Rails inspect)."""
    if obj is None:
        print("None")
        return

    if isinstance(obj, list):
        for item in obj:
            pp(item)
            print()
        return

    data = attrs(obj)
    class_name = obj.__class__.__name__

    # Calculate max key length for alignment
    max_key_len = max(len(k) for k in data.keys()) if data else 0

    print(f"#{class_name}")
    for key, value in data.items():
        # Format the value nicely
        if isinstance(value, str) and len(value) > 60:
            value = value[:60] + "..."
        print(f"  {key:<{max_key_len}} : {value!r}")


# =============================================================================
# Start Console
# =============================================================================

if __name__ == "__main__":
    print(__doc__)

    # Enable tab completion
    readline.set_completer(rlcompleter.Completer(locals()).complete)
    readline.parse_and_bind("tab: complete")

    # Start REPL
    code.interact(local=locals(), banner="", exitmsg="\nClosing session...")
    db.close()
