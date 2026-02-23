"""Tests for semver utilities."""
from app.utils.semver import parse_version, compare_versions, is_valid_version


class TestParseVersion:
    def test_basic(self):
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_zero(self):
        assert parse_version("0.0.0") == (0, 0, 0)

    def test_large(self):
        assert parse_version("100.200.300") == (100, 200, 300)

    def test_prerelease(self):
        assert parse_version("1.2.3-beta.1") == (1, 2, 3)

    def test_build_metadata(self):
        assert parse_version("1.2.3+build.42") == (1, 2, 3)

    def test_prerelease_and_build(self):
        assert parse_version("1.2.3-alpha+build") == (1, 2, 3)

    def test_invalid_no_patch(self):
        assert parse_version("1.2") is None

    def test_invalid_text(self):
        assert parse_version("latest") is None

    def test_invalid_empty(self):
        assert parse_version("") is None

    def test_whitespace_stripped(self):
        assert parse_version("  1.0.0  ") == (1, 0, 0)


class TestCompareVersions:
    def test_equal(self):
        assert compare_versions("1.0.0", "1.0.0") == 0

    def test_major_greater(self):
        assert compare_versions("2.0.0", "1.0.0") == 1

    def test_major_less(self):
        assert compare_versions("1.0.0", "2.0.0") == -1

    def test_minor_greater(self):
        assert compare_versions("1.1.0", "1.0.0") == 1

    def test_patch_greater(self):
        assert compare_versions("1.0.1", "1.0.0") == 1

    def test_ten_vs_nine(self):
        """Ensure numeric comparison, not string: 10 > 9."""
        assert compare_versions("10.0.0", "9.0.0") == 1

    def test_invalid_returns_zero(self):
        assert compare_versions("invalid", "1.0.0") == 0


class TestIsValidVersion:
    def test_valid(self):
        assert is_valid_version("1.0.0") is True

    def test_valid_prerelease(self):
        assert is_valid_version("1.0.0-beta") is True

    def test_invalid(self):
        assert is_valid_version("not-a-version") is False

    def test_partial(self):
        assert is_valid_version("1.0") is False
