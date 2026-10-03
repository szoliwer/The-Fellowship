"""Step 0 — User Registration: accounts, passwords and user records.

Accounts live in a small SQLite database, data/fellowship.db at the repo root
(git-ignored). Passwords are never stored: only a salted scrypt hash.

After every sign-up the user records (without any password data) are also written
to data/users.json, the file later steps read (see D-004: steps pass data as files).

Other users must only ever see `public_view(user)`. Everything under `private` is
for the owner and the system only.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

STEP_DIR = Path(__file__).resolve().parent
REPO_ROOT = STEP_DIR.parent
SAMPLE_USERS_FILE = STEP_DIR / "samples" / "users.json"
DB_FILE = REPO_ROOT / "data" / "fellowship.db"
USERS_EXPORT_FILE = REPO_ROOT / "data" / "users.json"

CONNECTION_INTENT = "research collaboration"  # scientist-first MVP: one intent for everyone

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 200
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1

# Shown on the sign-up screen. Answers the three privacy questions from the shared brief.
CONSENT_TEXT = {
    "What stays private": (
        "The chats you import, your email and password, and any private details "
        "(name, affiliation). No other user ever sees them."
    ),
    "What the system may use": (
        "Chats you import are first screened, and anything personal or sensitive is held back. "
        "The remaining research conversations are analysed by an external AI model service "
        "to suggest ideas. Suggested ideas stay private until you approve them."
    ),
    "What other people can see": (
        "Only your pseudonym, and only the idea summaries you approve one by one later. "
        "Nothing is shared when you sign up. Connecting with someone does not reveal who you are."
    ),
}
CONSENT_CHECKBOX = "I agree that the chats I choose to import may be processed as described above."

PSEUDONYM_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegistrationError(Exception):
    """A problem the user can fix. `code` is stable; `message` is safe to show on screen."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- Database ----------

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id          TEXT PRIMARY KEY,
    pseudonym        TEXT NOT NULL UNIQUE,
    email            TEXT UNIQUE,              -- lower-case; NULL for demo accounts
    name             TEXT,
    affiliation      TEXT,
    connection_intent TEXT NOT NULL,
    is_demo_account  INTEGER NOT NULL,
    consent_process_imported_chats INTEGER NOT NULL,
    consent_timestamp TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS credentials (
    user_id         TEXT PRIMARY KEY REFERENCES users(user_id),
    password_hash   TEXT NOT NULL,             -- scrypt$n$r$p$salt$hash, never the password
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT
);
"""


def _connect(db_file):
    db_file = Path(db_file)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _seed_demo_users(conn)
    return conn


def _seed_demo_users(conn, sample_file=SAMPLE_USERS_FILE):
    with open(sample_file, encoding="utf-8") as f:
        demos = json.load(f)
    with conn:
        for u in demos:
            conn.execute(
                "INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?,?,?,?)",
                (u["user_id"], u["pseudonym"], None, None, None, u["connection_intent"], 1,
                 1, u["consent"]["timestamp"], u["consent"]["timestamp"]),
            )


def _record(row):
    """A database row as the agreed Step 0 user record (no password data, ever)."""
    return {
        "user_id": row["user_id"],
        "pseudonym": row["pseudonym"],
        "connection_intent": row["connection_intent"],
        "is_demo_account": bool(row["is_demo_account"]),
        "private": {"name": row["name"], "email": row["email"], "affiliation": row["affiliation"]},
        "consent": {
            "process_imported_chats": bool(row["consent_process_imported_chats"]),
            "timestamp": row["consent_timestamp"],
        },
    }


def load_users(db_file=DB_FILE):
    with closing(_connect(db_file)) as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY is_demo_account DESC, created_at").fetchall()
    return [_record(r) for r in rows]


def get_user(user_id, db_file=DB_FILE):
    with closing(_connect(db_file)) as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return _record(row) if row else None


def demo_users(db_file=DB_FILE):
    return [u for u in load_users(db_file) if u["is_demo_account"]]


def export_users(db_file=DB_FILE, out_file=USERS_EXPORT_FILE):
    """Write all user records (no password data) to data/users.json for later steps."""
    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_file.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(load_users(db_file), f, indent=2, ensure_ascii=False)
    tmp.replace(out_file)


def public_view(user):
    """The only fields another user may ever see."""
    return {"pseudonym": user["pseudonym"], "connection_intent": user["connection_intent"]}


# ---------- Passwords ----------

def _hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def _check_password(password, stored):
    _, n, r, p, salt_hex, hash_hex = stored.split("$")
    digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
                            n=int(n), r=int(r), p=int(p), dklen=32)
    return hmac.compare_digest(digest.hex(), hash_hex)


_DUMMY_HASH = _hash_password(secrets.token_hex(16))


# ---------- Validation ----------

def normalize_email(email):
    return (email or "").strip().lower()


def validate_pseudonym(pseudonym, name=None):
    pseudonym = (pseudonym or "").strip()
    if not PSEUDONYM_PATTERN.match(pseudonym):
        raise RegistrationError(
            "invalid_pseudonym",
            "Pseudonyms use 3–30 lowercase letters, numbers or underscores, e.g. researcher_042.",
        )
    # The pseudonym is what other people see, so it must not give away the real name.
    for part in re.split(r"[\s\-_.]+", (name or "").lower()):
        if len(part) >= 3 and part in pseudonym:
            raise RegistrationError(
                "pseudonym_reveals_name",
                "Your pseudonym contains part of your real name. Pick one that doesn't identify you.",
            )
    return pseudonym


def validate_password(password, email="", pseudonym=""):
    password = password or ""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise RegistrationError("weak_password", f"Use a password of at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise RegistrationError("weak_password", f"Use a password of at most {MAX_PASSWORD_LENGTH} characters.")
    if password.lower() in {email.lower(), pseudonym.lower()}:
        raise RegistrationError("weak_password", "Your password can't be your email or pseudonym.")
    return password


# ---------- Sign-up and log-in ----------

def create_account(pseudonym, email, password, consent_given, name=None, affiliation=None, db_file=DB_FILE):
    """Validate a sign-up, save it, and return the new user record."""
    if consent_given is not True:
        raise RegistrationError(
            "consent_required", "You need to agree to the processing terms to create an account."
        )
    email = normalize_email(email)
    if not EMAIL_PATTERN.match(email):
        raise RegistrationError("invalid_email", "Enter a valid email address. You'll use it to log in.")
    name = (name or "").strip() or None
    affiliation = (affiliation or "").strip() or None
    pseudonym = validate_pseudonym(pseudonym, name=name)
    validate_password(password, email=email, pseudonym=pseudonym)

    now = _iso(_now())
    with closing(_connect(db_file)) as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise RegistrationError("email_taken", "There's already an account with that email. Try logging in.")
        if conn.execute("SELECT 1 FROM users WHERE pseudonym = ?", (pseudonym,)).fetchone():
            raise RegistrationError("pseudonym_taken", "That pseudonym is already taken. Try another.")
        user_id = "user_" + secrets.token_hex(4)
        while conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            user_id = "user_" + secrets.token_hex(4)
        with conn:
            conn.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)",
                (user_id, pseudonym, email, name, affiliation, CONNECTION_INTENT, 0, 1, now, now),
            )
            conn.execute(
                "INSERT INTO credentials (user_id, password_hash) VALUES (?, ?)",
                (user_id, _hash_password(password)),
            )
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    export_users(db_file, Path(db_file).parent / USERS_EXPORT_FILE.name)
    return _record(row)


def log_in(email, password, db_file=DB_FILE, now=None):
    """Return the user record if email + password are right. Locks the account for
    LOCKOUT_MINUTES after MAX_FAILED_LOGINS wrong passwords in a row."""
    now = now or _now()
    bad = RegistrationError("bad_credentials", "That email and password don't match an account.")
    email = normalize_email(email)
    with closing(_connect(db_file)) as conn:
        row = conn.execute(
            "SELECT u.*, c.password_hash, c.failed_attempts, c.locked_until "
            "FROM users u JOIN credentials c USING (user_id) WHERE u.email = ?",
            (email,),
        ).fetchone()
        if row is None:
            _check_password(password or "", _DUMMY_HASH)  # same work either way, so timing doesn't reveal emails
            raise bad
        if row["locked_until"] and now < datetime.fromisoformat(row["locked_until"].replace("Z", "+00:00")):
            raise RegistrationError(
                "locked", f"Too many wrong passwords. Try again in {LOCKOUT_MINUTES} minutes."
            )
        if not _check_password(password or "", row["password_hash"]):
            failed = row["failed_attempts"] + 1
            locked_until = _iso(now + timedelta(minutes=LOCKOUT_MINUTES)) if failed >= MAX_FAILED_LOGINS else None
            with conn:
                conn.execute(
                    "UPDATE credentials SET failed_attempts = ?, locked_until = ? WHERE user_id = ?",
                    (0 if locked_until else failed, locked_until, row["user_id"]),
                )
            raise bad
        with conn:
            conn.execute(
                "UPDATE credentials SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
                (row["user_id"],),
            )
        return _record(row)
