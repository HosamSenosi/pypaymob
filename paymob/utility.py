from paymob.exceptions import ValidationError

def validate_email(email: str) -> None:
    """
    Simple email validator.
    ! This is not a complete email validator. You should use a more robust one if critical
    Raises:
        ValidationError
    """
    err_msg = "Invalid email address"
    
    if not email or "@" not in email or len(email) > 320:
        raise ValidationError(err_msg, params={"email": email})
