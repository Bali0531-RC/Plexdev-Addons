import re
from typing import Tuple, Optional


def parse_version(version: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse a semver version string into a tuple of (major, minor, patch).
    Returns None if the version string is invalid.
    """
    # Match semver pattern: X.Y.Z with optional pre-release and build metadata
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-[\w.]+)?(?:\+[\w.]+)?$', version.strip())
    if not match:
        return None
    
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two semver version strings.
    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    
    if v1 is None or v2 is None:
        # Fallback to string comparison if parsing fails
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        return 0
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    return 0


def is_valid_version(version: str) -> bool:
    """Check if a version string is a valid semver."""
    return parse_version(version) is not None


def is_newer_version(current: str, latest: str) -> bool:
    """Check if current version is newer than latest (development version)."""
    return compare_versions(current, latest) > 0


def is_outdated_version(current: str, latest: str) -> bool:
    """Check if current version is older than latest."""
    return compare_versions(current, latest) < 0
