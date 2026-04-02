import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "legal.db")


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                title       TEXT,
                mode        TEXT CHECK(mode IN ('citizen', 'candidate')),
                pinned      INTEGER DEFAULT 0,
                folder      TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT CHECK(role IN ('user', 'conservative', 'liberal', 'consensus')),
                content         TEXT,
                risk_level      TEXT CHECK(risk_level IN ('safe', 'caution', 'danger')),
                cited_articles  TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedbacks (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
                user_question   TEXT,
                bot_response    TEXT,
                risk_level      TEXT,
                rating          TEXT CHECK(rating IN ('up', 'down')),
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Migrate: add pinned/folder columns if missing
        cursor = await db.execute("PRAGMA table_info(conversations)")
        cols = {row[1] for row in await cursor.fetchall()}
        if "pinned" not in cols:
            await db.execute("ALTER TABLE conversations ADD COLUMN pinned INTEGER DEFAULT 0")
        if "folder" not in cols:
            await db.execute("ALTER TABLE conversations ADD COLUMN folder TEXT")

        await db.commit()
    finally:
        await db.close()
