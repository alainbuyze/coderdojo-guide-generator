"""Tests for MakeCode image detector."""

from bs4 import BeautifulSoup

from src.makecode_detector import MakeCodeImageDetector


def test_find_makecode_links():
    """Test finding MakeCode links in sections."""
    detector = MakeCodeImageDetector()

    sections = [
        {
            "heading": "Introduction",
            "content": [
                BeautifulSoup(
                    "<p>Some text with a link: "
                    '<a href="https://makecode.microbit.org/_iscUF8CzzYMd">Project</a></p>',
                    "html.parser",
                ).p
            ],
        },
        {
            "heading": "Reference",
            "content": [
                BeautifulSoup(
                    '<p>Link: <a href="https://makecode.microbit.org/_abc123def456">Project 2</a></p>',
                    "html.parser",
                ).p
            ],
        },
    ]

    links = detector.find_makecode_links(sections)

    assert len(links) == 2
    assert "https://makecode.microbit.org/_iscUF8CzzYMd" in links
    assert "https://makecode.microbit.org/_abc123def456" in links


def test_find_makecode_links_no_duplicates():
    """Test that duplicate links are removed."""
    detector = MakeCodeImageDetector()

    sections = [
        {
            "heading": "Introduction",
            "content": [
                BeautifulSoup(
                    '<p><a href="https://makecode.microbit.org/_test123">Project</a></p>',
                    "html.parser",
                ).p,
                BeautifulSoup(
                    '<p><a href="https://makecode.microbit.org/_test123">Same Project</a></p>',
                    "html.parser",
                ).p,
            ],
        }
    ]

    links = detector.find_makecode_links(sections)

    assert len(links) == 1
    assert "https://makecode.microbit.org/_test123" in links


def test_is_code_image():
    """Test code image detection."""
    detector = MakeCodeImageDetector()

    # Image with "code" in alt text
    code_image = {"src": "image.png", "alt": "code blocks", "title": ""}
    assert detector._is_code_image(code_image, 0) is True

    # Image with "makecode" in filename
    makecode_image = {"src": "makecode_screenshot.png", "alt": "", "title": ""}
    assert detector._is_code_image(makecode_image, 1) is True

    # Regular image
    regular_image = {"src": "photo.jpg", "alt": "A photo", "title": ""}
    assert detector._is_code_image(regular_image, 2) is False


def test_match_images_to_links():
    """Test matching code images to MakeCode links."""
    detector = MakeCodeImageDetector()

    images = [
        {"src": "intro.png", "alt": "Introduction", "title": ""},
        {"src": "code1.png", "alt": "code blocks", "title": ""},
        {"src": "photo.jpg", "alt": "Photo", "title": ""},
        {"src": "code2.png", "alt": "program", "title": ""},
    ]

    links = [
        "https://makecode.microbit.org/_link1",
        "https://makecode.microbit.org/_link2",
    ]

    matches = detector.match_images_to_links(images, links)

    assert len(matches) == 2
    assert matches[1] == "https://makecode.microbit.org/_link1"  # code1.png
    assert matches[3] == "https://makecode.microbit.org/_link2"  # code2.png


def test_match_images_to_links_no_links():
    """Test matching when no links are provided."""
    detector = MakeCodeImageDetector()

    images = [
        {"src": "code.png", "alt": "code blocks", "title": ""},
    ]

    matches = detector.match_images_to_links(images, [])

    assert len(matches) == 0


def test_match_images_to_links_no_code_images():
    """Test matching when no code images are found."""
    detector = MakeCodeImageDetector()

    images = [
        {"src": "photo1.jpg", "alt": "Photo", "title": ""},
        {"src": "photo2.jpg", "alt": "Another photo", "title": ""},
    ]

    links = ["https://makecode.microbit.org/_link1"]

    matches = detector.match_images_to_links(images, links)

    assert len(matches) == 0
