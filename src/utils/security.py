"""Security utilities for sanitizing sensitive data."""

import re
from typing import Any, Dict, List, Set


# Default patterns for sensitive data
DEFAULT_SENSITIVE_PATTERNS = [
    "password",
    "passwd",
    "pwd",
    "token",
    "secret",
    "key",
    "api_key",
    "apikey",
    "api-key",
    "credential",
    "auth",
    "private",
    "cert",
    "certificate",
]

# Additional patterns for environment variables
SENSITIVE_ENV_PATTERNS = [
    r".*_PASSWORD$",
    r".*_TOKEN$",
    r".*_SECRET$",
    r".*_KEY$",
    r".*_API_KEY$",
    r".*_APIKEY$",
    r".*_AUTH$",
    r"MYSQL_.*",
    r"POSTGRES_.*",
    r"DB_.*",
    r"DATABASE_.*",
]


def is_sensitive_key(key: str, custom_patterns: List[str] = None) -> bool:
    """Check if a key name indicates sensitive data.

    Args:
        key: Key name to check
        custom_patterns: Additional patterns to check

    Returns:
        bool: True if key appears to contain sensitive data
    """
    if not key:
        return False

    key_lower = key.lower()

    # Check default patterns
    for pattern in DEFAULT_SENSITIVE_PATTERNS:
        if pattern in key_lower:
            return True

    # Check environment variable patterns
    for pattern in SENSITIVE_ENV_PATTERNS:
        if re.match(pattern, key, re.IGNORECASE):
            return True

    # Check custom patterns
    if custom_patterns:
        for pattern in custom_patterns:
            if pattern.lower() in key_lower:
                return True
            # Try as regex
            try:
                if re.match(pattern, key, re.IGNORECASE):
                    return True
            except re.error:
                pass

    return False


def sanitize_value(value: Any, mask: str = "***REDACTED***") -> str:
    """Sanitize a sensitive value.

    Args:
        value: Value to sanitize
        mask: Replacement string

    Returns:
        str: Sanitized value
    """
    if value is None:
        return mask

    value_str = str(value)

    # Show length hint for debugging
    length = len(value_str)
    if length > 0:
        return f"{mask} (length: {length})"
    return mask


def sanitize_dict(
    data: Dict[str, Any],
    custom_patterns: List[str] = None,
    mask: str = "***REDACTED***"
) -> Dict[str, Any]:
    """Sanitize sensitive data from a dictionary.

    Args:
        data: Dictionary to sanitize
        custom_patterns: Custom patterns for sensitive keys
        mask: Replacement string

    Returns:
        Dict: Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}

    for key, value in data.items():
        if is_sensitive_key(key, custom_patterns):
            # Replace sensitive value
            sanitized[key] = sanitize_value(value, mask)
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = sanitize_dict(value, custom_patterns, mask)
        elif isinstance(value, list):
            # Sanitize lists
            sanitized[key] = [
                sanitize_dict(item, custom_patterns, mask)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def sanitize_secrets(
    data: Any,
    custom_patterns: List[str] = None,
    mask: str = "***REDACTED***"
) -> Any:
    """Sanitize sensitive data from any data structure.

    Args:
        data: Data to sanitize
        custom_patterns: Custom patterns for sensitive keys
        mask: Replacement string

    Returns:
        Sanitized data
    """
    if isinstance(data, dict):
        return sanitize_dict(data, custom_patterns, mask)
    elif isinstance(data, list):
        return [sanitize_secrets(item, custom_patterns, mask) for item in data]
    else:
        return data


def extract_referenced_secrets(text: str) -> Set[str]:
    """Extract references to secrets in password managers.

    Args:
        text: Text to analyze

    Returns:
        Set of secret reference patterns found
    """
    references = set()

    # Common password manager reference patterns
    patterns = [
        r"(bitwarden|1password|keepass|lastpass)://[^\s]+",
        r"vault://[^\s]+",
        r"\$\{[A-Z_]+\}",  # Environment variables
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        references.update(matches)

    return references


def sanitize_docker_compose(compose_content: str) -> str:
    """Sanitize docker-compose file content.

    Args:
        compose_content: Docker compose file content

    Returns:
        Sanitized content with secrets redacted
    """
    lines = compose_content.split('\n')
    sanitized_lines = []

    for line in lines:
        # Check for environment variable assignments
        if '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip().lstrip('- ')
                value = parts[1].strip()

                if is_sensitive_key(key):
                    # Redact the value but keep the key
                    sanitized_lines.append(f"{parts[0]}=***REDACTED***")
                    continue

        sanitized_lines.append(line)

    return '\n'.join(sanitized_lines)


def create_credential_reference(
    service_name: str,
    credential_type: str = "password",
    location: str = "password manager"
) -> str:
    """Create a reference to credentials in documentation.

    Args:
        service_name: Name of service
        credential_type: Type of credential
        location: Where credential is stored

    Returns:
        Documentation-friendly credential reference
    """
    return f"See {location} for {service_name} {credential_type}"


def should_exclude_from_docs(
    service_name: str,
    exclude_list: List[str]
) -> bool:
    """Check if a service should be excluded from documentation.

    Args:
        service_name: Name of service
        exclude_list: List of services to exclude

    Returns:
        bool: True if service should be excluded
    """
    for pattern in exclude_list:
        # Exact match
        if service_name.lower() == pattern.lower():
            return True

        # Pattern match
        try:
            if re.match(pattern, service_name, re.IGNORECASE):
                return True
        except re.error:
            pass

    return False
