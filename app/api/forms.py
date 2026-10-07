from wtforms import FloatField, Form, IntegerField, StringField, ValidationError
from wtforms.validators import AnyOf, DataRequired, Length, NumberRange, Optional, Regexp

from ..services.integrity import ALGORITHMS

HOST_PATTERN = r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$"


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _strip_lower(value):
    return value.strip().lower() if isinstance(value, str) else value


class PortScanForm(Form):
    host = StringField(
        "Host",
        filters=[_strip],
        validators=[
            DataRequired(message="Host is required."),
            Length(max=253),
            Regexp(HOST_PATTERN, message="Enter a hostname or IPv4 address."),
        ],
    )
    start_port = IntegerField("Start port", default=1, validators=[NumberRange(1, 65535, "Port must be 1-65535.")])
    end_port = IntegerField("End port", default=1024, validators=[NumberRange(1, 65535, "Port must be 1-65535.")])
    timeout = FloatField("Timeout", default=1.0, validators=[NumberRange(0.1, 10.0, "Timeout must be 0.1-10 seconds.")])

    def validate_end_port(self, field):
        start = self.start_port.data
        if start is not None and field.data is not None and field.data < start:
            raise ValidationError("End port must be greater than or equal to the start port.")


class IntegrityForm(Form):
    directory = StringField("Directory", filters=[_strip], validators=[Length(max=500)])
    algorithm = StringField("Algorithm", filters=[_strip_lower], validators=[Optional(), AnyOf(ALGORITHMS)])