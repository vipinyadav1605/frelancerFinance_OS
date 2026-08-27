import re

from rest_framework import serializers

# Standard GSTIN layout: 2-digit state code, 10-char PAN, 1-digit entity
# code, 'Z' by convention, 1 checksum char. This checks the LAYOUT, not the
# actual mod-36 checksum - good enough to catch typos/garbage without
# reimplementing GSTN's checksum algorithm.
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")


def validate_gstin_format(value: str) -> str:
    if value and not GSTIN_PATTERN.match(value):
        raise serializers.ValidationError("Not a validly-formatted GSTIN (e.g. 27AAAAA0000A1Z5).")
    return value


def validate_pan_format(value: str) -> str:
    if value and not PAN_PATTERN.match(value):
        raise serializers.ValidationError("Not a validly-formatted PAN (e.g. ABCDE1234F).")
    return value
