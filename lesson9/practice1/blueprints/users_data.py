"""Single source of truth for user data shared between API v1 and v2."""

USERS = {
    1: {"first_name": "Văn", "last_name": "Nguyễn", "email": "a@vnu.vn"},
    2: {"first_name": "Trang", "last_name": "Trần", "email": "b@vnu.vn"},
}


def get_user(uid: int):
    """Return user dictionary by ID, or None if not found."""
    return USERS.get(uid)


def create_user(first_name: str, last_name: str, email: str) -> tuple[int, dict]:
    """Create a new user and return (uid, user_dict)."""
    uid = max(USERS.keys(), default=0) + 1
    user = {"first_name": first_name, "last_name": last_name, "email": email}
    USERS[uid] = user
    return uid, user
