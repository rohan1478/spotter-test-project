from rest_framework.exceptions import ValidationError

ALLOWED_LOCATION_FIELDS = {"street", "city", "state"}

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def validate_presence(data: dict, label: str = "location"):
    """Reject any fields not in the allowed set."""
    unknown = set(data.keys()) - ALLOWED_LOCATION_FIELDS
    if unknown:
        raise ValidationError(
            {label: f"Unknown field(s): {', '.join(sorted(unknown))}. Only street, city, state are accepted."},
            code="invalid_fields",
        )


def validate_state(state: str, label: str = "location"):
    """Validate state is a valid US state abbreviation."""
    normalized = state.strip().upper()
    if normalized not in US_STATES:
        raise ValidationError(
            {label: f"Invalid US state: '{state}'. Must be a valid US state abbreviation."},
            code="invalid_state",
        )
    return normalized
