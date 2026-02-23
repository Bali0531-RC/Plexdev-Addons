"""Tests for utility functions."""
from app.utils import slugify, calculate_storage_size, format_bytes


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        assert slugify("My Addon! @v2") == "my-addon-v2"

    def test_underscores(self):
        assert slugify("my_addon_name") == "my-addon-name"

    def test_multiple_spaces(self):
        assert slugify("too   many   spaces") == "too-many-spaces"

    def test_leading_trailing(self):
        assert slugify("--trimmed--") == "trimmed"

    def test_unicode(self):
        assert slugify("café résumé") == "caf-rsum"

    def test_empty(self):
        assert slugify("") == ""

    def test_numbers_only(self):
        assert slugify("123") == "123"

    def test_already_slug(self):
        assert slugify("already-a-slug") == "already-a-slug"


class TestCalculateStorageSize:
    def test_ascii(self):
        assert calculate_storage_size("hello") == 5

    def test_empty(self):
        assert calculate_storage_size("") == 0

    def test_none(self):
        assert calculate_storage_size(None) == 0

    def test_unicode(self):
        # Multi-byte UTF-8 characters
        size = calculate_storage_size("日本語")
        assert size == 9  # 3 bytes per CJK character


class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(500) == "500.00 B"

    def test_kb(self):
        assert format_bytes(1024) == "1.00 KB"

    def test_mb(self):
        assert format_bytes(1024 * 1024) == "1.00 MB"

    def test_gb(self):
        assert format_bytes(1024 ** 3) == "1.00 GB"

    def test_tb(self):
        assert format_bytes(1024 ** 4) == "1.00 TB"
