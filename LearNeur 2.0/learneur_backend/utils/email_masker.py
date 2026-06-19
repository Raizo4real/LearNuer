def mask_email(email: str) -> str:
    """
    Masks an email address (e.g. john.doe123@gmail.com -> jo*********123@gmail.com)
    Leaves first 2 and last 3 chars of the username before the @.
    """
    try:
        username, domain = email.split('@')
        if len(username) <= 5:
            # Fallback for very short usernames
            masked_user = username[0] + '*' * (len(username) - 1)
        else:
            masked_user = username[:2] + '*' * (len(username) - 5) + username[-3:]
        return f"{masked_user}@{domain}"
    except ValueError:
        return email # Fallback if invalid email format