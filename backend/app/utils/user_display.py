from app.models.user import User


def display_name(user: User) -> str:
    return user.nickname if user.nickname else user.name


def profile_completed(user: User) -> bool:
    return bool(user.email and user.gender)
