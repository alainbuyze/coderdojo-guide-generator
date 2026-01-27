"""Tests for markdown generator."""

import pytest

from src.generator import generate_guide, heading_to_class, html_to_markdown
from src.sources.base import ExtractedContent


def test_html_to_markdown_basic():
    """Test basic HTML to Markdown conversion."""
    html = "<p>Hello <strong>world</strong></p>"
    md = html_to_markdown(html)

    assert "Hello" in md
    assert "**world**" in md


def test_html_to_markdown_images():
    """Test image conversion outputs HTML img tags with section class."""
    html = '<img src="https://example.com/img.png" alt="Test image" />'
    md = html_to_markdown(html, section_class="section-test")

    assert '<img src="https://example.com/img.png"' in md
    assert 'alt="Test image"' in md
    assert 'class="section-test"' in md


def test_generate_guide_basic():
    """Test basic guide generation."""
    content = ExtractedContent(
        title="Test Guide",
        sections=[
            {
                "heading": "Introduction",
                "level": 2,
                "content": [],
            }
        ],
        images=[],
        metadata={},
    )

    guide = generate_guide(content)

    assert "# Test Guide" in guide
    assert "## Introduction" in guide


def test_generate_guide_with_metadata():
    """Test guide generation with description."""
    content = ExtractedContent(
        title="Test Guide",
        sections=[],
        images=[],
        metadata={"description": "A test description"},
    )

    guide = generate_guide(content)

    assert "# Test Guide" in guide
    assert "> A test description" in guide


def test_heading_to_class():
    """Test heading to CSS class conversion."""
    assert heading_to_class("Benodigde materialen") == "section-benodigde-materialen"
    assert heading_to_class("Programmering") == "section-programmering"
    assert heading_to_class("Montage stappen") == "section-montage-stappen"
    assert heading_to_class("") == "section-content"
    assert heading_to_class("Test (special) / chars!") == "section-test-special-chars"


def test_html_to_markdown_images_default_class():
    """Test image conversion uses default class when none provided."""
    html = '<img src="https://example.com/img.png" alt="" />'
    md = html_to_markdown(html)

    assert '<img src="https://example.com/img.png"' in md
    assert 'class="section-content"' in md
