"""Tests for QR code processor module."""

import tempfile
from pathlib import Path

import pytest

from src.qrcode_processor import QRCodeGenerator, process_markdown_links


class TestQRCodeGenerator:
    """Tests for QRCodeGenerator class."""

    def test_init_creates_directory(self):
        """Test that initialization creates the qrcodes directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = QRCodeGenerator(output_dir)

            assert generator.qrcode_dir.exists()
            assert generator.qrcode_dir.is_dir()
            assert generator.qrcode_dir == output_dir / "qrcodes"

    def test_generate_qr_code_creates_file(self):
        """Test that generate_qr_code creates a PNG file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = QRCodeGenerator(output_dir)

            url = "https://example.com/test"
            qr_path = generator.generate_qr_code(url)

            # Check relative path is returned
            assert str(qr_path).startswith("qrcodes/")
            assert str(qr_path).endswith(".png")

            # Check file exists
            full_path = output_dir / qr_path
            assert full_path.exists()
            assert full_path.is_file()

    def test_generate_qr_code_caching(self):
        """Test that duplicate URLs reuse cached QR codes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = QRCodeGenerator(output_dir)

            url = "https://example.com/test"

            # Generate first time
            qr_path1 = generator.generate_qr_code(url)

            # Generate again - should return same path
            qr_path2 = generator.generate_qr_code(url)

            assert qr_path1 == qr_path2
            assert url in generator._cache

    def test_generate_qr_code_different_urls(self):
        """Test that different URLs generate different QR codes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = QRCodeGenerator(output_dir)

            url1 = "https://example.com/page1"
            url2 = "https://example.com/page2"

            qr_path1 = generator.generate_qr_code(url1)
            qr_path2 = generator.generate_qr_code(url2)

            assert qr_path1 != qr_path2

    def test_generate_qr_code_long_url(self):
        """Test QR code generation with very long URLs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = QRCodeGenerator(output_dir)

            # Create a very long URL
            url = "https://example.com/" + "a" * 500

            qr_path = generator.generate_qr_code(url)
            full_path = output_dir / qr_path

            assert full_path.exists()


class TestProcessMarkdownLinks:
    """Tests for process_markdown_links function."""

    def test_no_links(self):
        """Test markdown without any links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            markdown = "# Hello World\n\nThis is plain text without links."

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            assert result_md == markdown
            assert len(qr_info) == 0

    def test_single_link(self):
        """Test markdown with a single link."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            markdown = "Check out [this link](https://example.com/test) for more info."

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            # Should contain original link plus QR code
            assert "[this link](https://example.com/test)" in result_md
            assert "![QR](qrcodes/" in result_md
            assert ".png)" in result_md

            # Should have one QR code info
            assert len(qr_info) == 1
            assert qr_info[0].url == "https://example.com/test"

    def test_multiple_links(self):
        """Test markdown with multiple links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            markdown = (
                "Visit [site 1](https://example.com/1) and "
                "[site 2](https://example.com/2) for details."
            )

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            # Should contain both original links plus QR codes
            assert "[site 1](https://example.com/1)" in result_md
            assert "[site 2](https://example.com/2)" in result_md
            assert result_md.count("![QR](qrcodes/") == 2

            # Should have two QR code infos
            assert len(qr_info) == 2

    def test_duplicate_urls(self):
        """Test that duplicate URLs reuse the same QR code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            url = "https://example.com/test"
            markdown = f"See [link 1]({url}) and [link 2]({url}) for more."

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            # Should have two QR code references
            assert len(qr_info) == 2

            # Both should point to the same QR code file
            assert qr_info[0].qr_path == qr_info[1].qr_path

    def test_empty_markdown(self):
        """Test with empty markdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            markdown = ""

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            assert result_md == ""
            assert len(qr_info) == 0

    def test_add_qrcodes_disabled(self):
        """Test that QR codes are not added when add_qrcodes=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            markdown = "Check out [this link](https://example.com/test) for more info."

            result_md, qr_info = process_markdown_links(
                markdown, output_dir, add_qrcodes=False
            )

            # Should return original markdown unchanged
            assert result_md == markdown
            assert len(qr_info) == 0

            # No qrcodes directory should be created
            qrcode_dir = output_dir / "qrcodes"
            assert not qrcode_dir.exists()

    def test_special_characters_in_url(self):
        """Test URLs with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            url = "https://example.com/path?param=value&other=123#section"
            markdown = f"Visit [the page]({url}) for details."

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            assert len(qr_info) == 1
            assert qr_info[0].url == url

    def test_complex_markdown_structure(self):
        """Test with complex markdown including headers, lists, and multiple links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            markdown = """# My Guide

## Introduction

Visit [our website](https://example.com) to learn more.

## Resources

- [Documentation](https://example.com/docs)
- [GitHub](https://github.com/example)
- [Support](https://example.com/support)

## Conclusion

Check [this link](https://example.com/docs) again for updates.
"""

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            # Should preserve structure
            assert "# My Guide" in result_md
            assert "## Introduction" in result_md

            # Should have QR codes (4 links, but one is duplicate)
            assert len(qr_info) == 4

            # Original links should still be present
            assert "[our website](https://example.com)" in result_md
            assert "[Documentation](https://example.com/docs)" in result_md


class TestIntegration:
    """Integration tests for the QR code processor."""

    def test_full_workflow(self):
        """Test complete workflow from markdown to QR codes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            markdown = """# Product Guide

Visit [our store](https://shop.example.com/product) to purchase.

For support, see [the manual](https://example.com/manual.pdf).
"""

            result_md, qr_info = process_markdown_links(markdown, output_dir)

            # Verify QR codes were generated
            assert len(qr_info) == 2

            # Verify files exist
            for info in qr_info:
                qr_file = output_dir / info.qr_path
                assert qr_file.exists()
                assert qr_file.suffix == ".png"

            # Verify markdown contains QR references
            for info in qr_info:
                assert info.qr_path in result_md
