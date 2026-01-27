"""Tests for MakeCode image detector."""

from src.makecode_detector import find_makecode_image_pairs


def test_find_pairs_basic():
    """Test finding image/MakeCode pairs from HTML structure."""
    html = """
    <div>
        <p><img src="https://example.com/code1.png"></p>
        <p>Link: <a href="https://makecode.microbit.org/_abc123">https://makecode.microbit.org/_abc123</a></p>
    </div>
    """

    pairs = find_makecode_image_pairs(html)

    assert len(pairs) == 1
    assert pairs["https://example.com/code1.png"] == "https://makecode.microbit.org/_abc123"


def test_find_pairs_multiple():
    """Test finding multiple image/MakeCode pairs."""
    html = """
    <div>
        <p><img src="https://example.com/code1.png"></p>
        <p>Link: <a href="https://makecode.microbit.org/_abc123">Project 1</a></p>

        <p>Some other text</p>

        <p><img src="https://example.com/code2.png"></p>
        <p>Link: <a href="https://makecode.microbit.org/_xyz789">Project 2</a></p>
    </div>
    """

    pairs = find_makecode_image_pairs(html)

    assert len(pairs) == 2
    assert pairs["https://example.com/code1.png"] == "https://makecode.microbit.org/_abc123"
    assert pairs["https://example.com/code2.png"] == "https://makecode.microbit.org/_xyz789"


def test_find_pairs_no_image_before_link():
    """Test that links without preceding image paragraphs are skipped."""
    html = """
    <div>
        <p>Just text, no image</p>
        <p>Link: <a href="https://makecode.microbit.org/_abc123">Project</a></p>
    </div>
    """

    pairs = find_makecode_image_pairs(html)

    assert len(pairs) == 0


def test_find_pairs_non_makecode_link():
    """Test that non-MakeCode links are ignored."""
    html = """
    <div>
        <p><img src="https://example.com/code.png"></p>
        <p>Link: <a href="https://example.com/other">Other Link</a></p>
    </div>
    """

    pairs = find_makecode_image_pairs(html)

    assert len(pairs) == 0


def test_find_pairs_real_html_structure():
    """Test with HTML structure matching actual Elecfreaks pages."""
    html = """
    <p><img loading="lazy" src="https://wiki-media-ef.oss-cn-hongkong.aliyuncs.com/i18n/en/docusaurus-plugin-content-docs/current/microbit/building-blocks/nezha-inventors-kit/images/75_15.png" class="img_ev3q"></p>
    <p>Link: <a href="https://makecode.microbit.org/_dmJ3isbKLLYV" target="_blank" rel="noopener noreferrer">https://makecode.microbit.org/_dmJ3isbKLLYV</a></p>
    """

    pairs = find_makecode_image_pairs(html)

    assert len(pairs) == 1
    img_src = "https://wiki-media-ef.oss-cn-hongkong.aliyuncs.com/i18n/en/docusaurus-plugin-content-docs/current/microbit/building-blocks/nezha-inventors-kit/images/75_15.png"
    assert pairs[img_src] == "https://makecode.microbit.org/_dmJ3isbKLLYV"


def test_find_pairs_empty_html():
    """Test with empty HTML."""
    pairs = find_makecode_image_pairs("")

    assert len(pairs) == 0


def test_find_pairs_image_not_immediately_before():
    """Test finding image when there are paragraphs between image and link."""
    html = """
    <div>
        <p><img src="https://example.com/code.png"></p>
        <p>Some explanation text</p>
        <p>Link: <a href="https://makecode.microbit.org/_abc123">Project</a></p>
    </div>
    """

    pairs = find_makecode_image_pairs(html)

    assert len(pairs) == 1
    assert pairs["https://example.com/code.png"] == "https://makecode.microbit.org/_abc123"


def test_find_pairs_image_too_far():
    """Test that images more than 3 paragraphs away are not matched."""
    html = """
    <div>
        <p><img src="https://example.com/code.png"></p>
        <p>Text 1</p>
        <p>Text 2</p>
        <p>Text 3</p>
        <p>Link: <a href="https://makecode.microbit.org/_abc123">Project</a></p>
    </div>
    """

    pairs = find_makecode_image_pairs(html)

    assert len(pairs) == 0
