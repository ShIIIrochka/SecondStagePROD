# -*- coding: utf-8 -*-


async def password_validator(password: str):
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one digit.")
    if not any(char.islower() for char in password):
        raise ValueError(
            "Password must contain at least one lowercase letter."
        )
    if not any(char.isupper() for char in password):
        raise ValueError(
            "Password must contain at least one uppercase letter."
        )
    if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for char in password):
        raise ValueError(
            "Password must contain at least one special character."
        )
