"""Tests for QR code processor."""

import re
from pathlib import Path

import pytest

from src.qrcode_processor import QRCodeGenerator, process_markdown_links


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory for tests."""
    return tmp_path / "output"


@pytest.fixture
def qr_generator(temp_output_dir):
    """Create a QRCodeGenerator instance for testing."""
    return QRCodeGenerator(temp_output_dir)


class TestQRCodeGenerator:
    """Tests for QRCodeGenerator class."""

    def test_init_creates_qrcode_directory(self, temp_output_dir):
        """Test that initializing creates the qrcodes subdirectory."""
        generator = QRCodeGenerator(temp_output_dir)
        assert generator.qrcode_dir.exists()
        assert generator.qrcode_dir.is_dir()
        assert generator.qrcode_dir == temp_output_dir / "qrcodes"

    def test_generate_qr_code_creates_image(self, qr_generator):
        """Test that generate_qr_code creates a PNG file."""
        url = "https://example.com"
        filename = "test_qr.png"

        qr_path = qr_generator.generate_qr_code(url, filename)

        assert qr_path.exists()
        assert qr_path.is_file()
        assert qr_path.suffix == ".png"
        assert qr_path.name == filename

    def test_generate_qr_code_caches_results(self, qr_generator):
        """Test that generating the same URL twice uses cache."""
        url = "https://example.com/test"
        filename1 = "test_qr_1.png"
        filename2 = "test_qr_2.png"

        # First call
        qr_path1 = qr_generator.generate_qr_code(url, filename1)
        assert qr_path1.exists()

        # Second call with different filename should return cached path
        qr_path2 = qr_generator.generate_qr_code(url, filename2)
        assert qr_path2 == qr_path1  # Same path returned
        assert not (qr_generator.qrcode_dir / filename2).exists()  # Second file not created

    def test_get_qr_filename_format(self, qr_generator):
        """Test that get_qr_filename returns correct format."""
        url = "https://example.com"
        filename = qr_generator.get_qr_filename(url, 1)

        # Should match pattern: qr_NNN_HASH.png
        assert re.match(r"qr_\d{3}_[a-f0-9]{8}\.png", filename)

    def test_get_qr_filename_deterministic(self, qr_generator):
        """Test that same URL produces same filename."""
        url = "https://example.com/test"
        filename1 = qr_generator.get_qr_filename(url, 5)
        filename2 = qr_generator.get_qr_filename(url, 5)

        assert filename1 == filename2

    def test_get_qr_filename_different_for_different_urls(self, qr_generator):
        """Test that different URLs produce different filenames."""
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2"

        filename1 = qr_generator.get_qr_filename(url1, 1)
        filename2 = qr_generator.get_qr_filename(url2, 1)

        assert filename1 != filename2

    def test_generate_qr_code_with_long_url(self, qr_generator):
        """Test QR code generation with a very long URL."""
        long_url = "https://example.com/" + "a" * 500
        filename = "long_url_qr.png"

        qr_path = qr_generator.generate_qr_code(long_url, filename)

        assert qr_path.exists()
        assert qr_path.stat().st_size > 0  # File has content

    def test_generate_qr_code_with_special_characters(self, qr_generator):
        """Test QR code generation with special characters in URL."""
        url = "https://example.com/page?param=value&other=123#section"
        filename = "special_chars_qr.png"

        qr_path = qr_generator.generate_qr_code(url, filename)

        assert qr_path.exists()


class TestProcessMarkdownLinks:
    """Tests for process_markdown_links function."""

    def test_no_links_in_markdown(self, temp_output_dir):
        """Test processing markdown with no links."""
        markdown = "# Title\n\nThis is plain text with no links."

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        assert modified_md == markdown
        assert len(qr_infos) == 0

    def test_single_link_processing(self, temp_output_dir):
        """Test processing markdown with a single link."""
        markdown = "Visit [Example](https://example.com) for more info."

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        assert len(qr_infos) == 1
        assert qr_infos[0].url == "https://example.com"
        assert qr_infos[0].path.exists()
        assert "![QR](qrcodes/" in modified_md
        assert modified_md.count("![QR]") == 1

    def test_multiple_links_processing(self, temp_output_dir):
        """Test processing markdown with multiple links."""
        markdown = (
            "Visit [Example](https://example.com) and [Google](https://google.com) "
            "for more info."
        )

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        assert len(qr_infos) == 2
        assert qr_infos[0].url == "https://example.com"
        assert qr_infos[1].url == "https://google.com"
        assert modified_md.count("![QR]") == 2

    def test_duplicate_url_handling(self, temp_output_dir):
        """Test that duplicate URLs reuse the same QR code."""
        markdown = (
            "Visit [Example](https://example.com) and also "
            "[this link](https://example.com) again."
        )

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        assert len(qr_infos) == 2
        assert qr_infos[0].url == qr_infos[1].url
        # Both should reference the same file (due to caching)
        assert qr_infos[0].path == qr_infos[1].path

    def test_qr_code_placement(self, temp_output_dir):
        """Test that QR codes are placed inline after links."""
        markdown = "Visit [Example](https://example.com) for info."

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        # QR code should appear immediately after the link
        assert "] ![QR]" in modified_md or "m) ![QR]" in modified_md

    def test_add_qrcodes_false(self, temp_output_dir):
        """Test that add_qrcodes=False skips QR generation."""
        markdown = "Visit [Example](https://example.com) for more info."

        modified_md, qr_infos = process_markdown_links(
            markdown, temp_output_dir, add_qrcodes=False
        )

        assert modified_md == markdown
        assert len(qr_infos) == 0
        assert not (temp_output_dir / "qrcodes").exists()

    def test_complex_markdown_with_multiple_elements(self, temp_output_dir):
        """Test processing complex markdown with various elements."""
        markdown = """# Tutorial

## Introduction

This is an [introduction](https://example.com/intro) to the guide.

![Image](images/pic.jpg)

## Steps

1. Visit the [product page](https://example.com/product)
2. Read the [documentation](https://example.com/docs)
3. Done!

[GitHub](https://github.com)
"""

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        assert len(qr_infos) == 4
        assert modified_md.count("![QR]") == 4
        # Original markdown structure should be preserved
        assert "# Tutorial" in modified_md
        assert "## Introduction" in modified_md
        assert "## Steps" in modified_md

    def test_links_with_titles(self, temp_output_dir):
        """Test processing links that have title attributes (edge case)."""
        markdown = 'Visit [Example](https://example.com "Example Site") for info.'

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        assert len(qr_infos) == 1
        # Should handle the title attribute gracefully
        assert qr_infos[0].url == 'https://example.com "Example Site"'

    def test_relative_paths_in_qr_markdown(self, temp_output_dir):
        """Test that QR code references use relative paths."""
        markdown = "Visit [Example](https://example.com) for info."

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        # Should use relative path, not absolute
        assert "qrcodes/" in modified_md
        assert str(temp_output_dir) not in modified_md

    def test_qrcode_directory_creation(self, temp_output_dir):
        """Test that qrcodes directory is created if it doesn't exist."""
        assert not (temp_output_dir / "qrcodes").exists()

        markdown = "Visit [Example](https://example.com) for info."
        process_markdown_links(markdown, temp_output_dir)

        assert (temp_output_dir / "qrcodes").exists()
        assert (temp_output_dir / "qrcodes").is_dir()

    def test_empty_markdown(self, temp_output_dir):
        """Test processing empty markdown."""
        markdown = ""

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        assert modified_md == ""
        assert len(qr_infos) == 0

    def test_markdown_with_code_blocks(self, temp_output_dir):
        """Test that links in code blocks are still detected (current behavior)."""
        markdown = """
# Code Example

```
[Not a real link](https://example.com)
```

But this [is a link](https://real-example.com).
"""

        modified_md, qr_infos = process_markdown_links(markdown, temp_output_dir)

        # Current implementation will detect both (markdown regex doesn't distinguish)
        # This documents current behavior - could be refined later to skip code blocks
        assert len(qr_infos) == 2
