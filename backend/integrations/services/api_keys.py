import hashlib

from integrations.models import ApiKey, _generate_api_key


def create_api_key(*, user, name: str) -> tuple[ApiKey, str]:
    """Returns (ApiKey instance, full_key). The full key is only ever available here."""
    full_key, display_prefix, key_hash = _generate_api_key()
    api_key = ApiKey.objects.create(
        user=user, name=name, key_hash=key_hash, display_prefix=display_prefix,
    )
    return api_key, full_key


def resolve_api_key(raw_key: str) -> ApiKey | None:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return ApiKey.objects.filter(key_hash=key_hash, revoked_at__isnull=True).select_related("user").first()
