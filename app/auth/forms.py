from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

MIN_PASSWORD_LENGTH = 12  # same rule as the first-run admin password
MAX_PASSWORD_LENGTH = 128


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _new_password_field(label="Password"):
    return PasswordField(
        label,
        validators=[
            DataRequired(message="Password is required."),
            Length(
                min=MIN_PASSWORD_LENGTH,
                max=MAX_PASSWORD_LENGTH,
                message=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            ),
        ],
    )


class LoginForm(FlaskForm):
    username = StringField("Username", filters=[_strip], validators=[DataRequired(), Length(max=50)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=MAX_PASSWORD_LENGTH)])


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        filters=[_strip],
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=50, message="Username must be 3-50 characters."),
            Regexp(r"^[A-Za-z0-9_]+$", message="Use only letters, numbers and underscores."),
        ],
    )
    password = _new_password_field()
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(message="Please confirm your password."), EqualTo("password", message="Passwords must match.")],
    )

    def validate_password(self, field):
        if self.username.data and field.data.lower() == self.username.data.lower():
            raise ValidationError("Password must not be the same as the username.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password", validators=[DataRequired(message="Enter your current password."), Length(max=MAX_PASSWORD_LENGTH)]
    )
    new_password = _new_password_field("New password")
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(message="Please confirm your new password."), EqualTo("new_password", message="Passwords must match.")],
    )

    def validate_new_password(self, field):
        if field.data == self.current_password.data:
            raise ValidationError("New password must be different from the current one.")