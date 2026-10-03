"""Step 0 — User Registration.

Creates and loads user records. Demo users come from samples/users.json (committed,
synthetic). Real sign-ups are saved to data/users.json at the repo root, which is
git-ignored so personal details never reach GitHub.

Other users must only ever see `pseudonym`. Everything under `private` is for the
owner and the system only.
"""

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

STEP_DIR = Path(__file__).resolve().parent
REPO_ROOT = STEP_DIR.parent
SAMPLE_USERS_FILE = STEP_DIR / "samples" / "users.json"
DATA_USERS_FILE = REPO_ROOT / "data" / "users.json"

CONNECTION_INTENT = "research collaboration"  # scientist-first MVP: one intent for everyone

# Shown on the sign-up screen. Answers the three privacy questions from the shared brief.
CONSENT_TEXT = {
    "What stays private": (
        "The chats you import and your private details (name, email, affiliation). "
        "No other user ever sees them."
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


class RegistrationError(Exception):
    """A problem the user can fix. `code` is stable; `message` is safe to show on screen."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_users(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_users(data_file=DATA_USERS_FILE, sample_file=SAMPLE_USERS_FILE):
    """All users: the synthetic demo users first, then real sign-ups."""
    return _read_users(sample_file) + _read_users(data_file)


def get_user(user_id, data_file=DATA_USERS_FILE, sample_file=SAMPLE_USERS_FILE):
    for user in load_users(data_file, sample_file):
        if user["user_id"] == user_id:
            return user
    return None


def demo_users(sample_file=SAMPLE_USERS_FILE):
    return _read_users(sample_file)


def validate_pseudonym(pseudonym, name=None, existing_users=()):
    pseudonym = (pseudonym or "").strip()
    if not PSEUDONYM_PATTERN.match(pseudonym):
        raise RegistrationError(
            "invalid_pseudonym",
            "Pseudonyms use 3–30 lowercase letters, numbers or underscores, e.g. researcher_042.",
        )
    if any(u["pseudonym"] == pseudonym for u in existing_users):
        raise RegistrationError("pseudonym_taken", "That pseudonym is already taken. Try another.")
    # The pseudonym is what other people see, so it must not give away the real name.
    for part in re.split(r"[\s\-_.]+", (name or "").lower()):
        if len(part) >= 3 and part in pseudonym:
            raise RegistrationError(
                "pseudonym_reveals_name",
                "Your pseudonym contains part of your real name. Pick one that doesn't identify you.",
            )
    return pseudonym


def create_user(
    pseudonym,
    consent_given,
    name=None,
    email=None,
    affiliation=None,
    data_file=DATA_USERS_FILE,
    sample_file=SAMPLE_USERS_FILE,
):
    """Validate a sign-up, save it to data_file, and return the new user record."""
    if consent_given is not True:
        raise RegistrationError(
            "consent_required", "You need to agree to the processing terms to create an account."
        )

    name = (name or "").strip() or None
    email = (email or "").strip() or None
    affiliation = (affiliation or "").strip() or None
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise RegistrationError("invalid_email", "That email address doesn't look right.")

    existing = load_users(data_file, sample_file)
    pseudonym = validate_pseudonym(pseudonym, name=name, existing_users=existing)

    existing_ids = {u["user_id"] for u in existing}
    user_id = "user_" + secrets.token_hex(4)
    while user_id in existing_ids:
        user_id = "user_" + secrets.token_hex(4)

    user = {
        "user_id": user_id,
        "pseudonym": pseudonym,
        "connection_intent": CONNECTION_INTENT,
        "is_demo_account": False,
        "private": {"name": name, "email": email, "affiliation": affiliation},
        "consent": {"process_imported_chats": True, "timestamp": _now_utc()},
    }

    registered = _read_users(data_file)
    registered.append(user)
    data_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = data_file.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(registered, f, indent=2, ensure_ascii=False)
    tmp.replace(data_file)
    return user


def public_view(user):
    """The only fields another user may ever see."""
    return {"pseudonym": user["pseudonym"], "connection_intent": user["connection_intent"]}
