"""Tests for Elecfreaks adapter."""

from bs4 import BeautifulSoup

from src.sources.elecfreaks import ElecfreaksAdapter


def test_can_handle_elecfreaks_wiki():
    """Test that adapter handles Elecfreaks Wiki URLs."""
    adapter = ElecfreaksAdapter()

    assert adapter.can_handle("https://wiki.elecfreaks.com/en/some/page")
    assert adapter.can_handle("https://wiki.elecfreaks.com/en/microbit/building-blocks")
    assert adapter.can_handle("http://wiki.elecfreaks.com/page")


def test_cannot_handle_other_urls():
    """Test that adapter rejects non-Elecfreaks URLs."""
    adapter = ElecfreaksAdapter()

    assert not adapter.can_handle("https://example.com")
    assert not adapter.can_handle("https://github.com/elecfreaks")
    assert not adapter.can_handle("https://google.com")


def test_extract_title_from_h1():
    """Test title extraction from h1 element."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <article>
        <h1>Test Tutorial Title</h1>
        <p>Some content</p>
    </article>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    content = adapter.extract(soup, "https://wiki.elecfreaks.com/test")

    assert content.title == "Test Tutorial Title"


def test_extract_images():
    """Test image extraction from content."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <article>
        <h1>Test</h1>
        <img src="https://example.com/image1.png" alt="Image 1" />
        <img src="/relative/image2.jpg" alt="Image 2" />
    </article>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    content = adapter.extract(soup, "https://wiki.elecfreaks.com/test")

    assert len(content.images) == 2
    assert content.images[0]["src"] == "https://example.com/image1.png"
    assert content.images[0]["alt"] == "Image 1"


def test_extract_removes_navigation():
    """Test that navigation elements are removed."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <nav class="navbar">Navigation</nav>
    <article>
        <h1>Title</h1>
        <p>Content</p>
    </article>
    <footer>Footer</footer>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    content = adapter.extract(soup, "https://wiki.elecfreaks.com/test")

    # Should have found content
    assert content.title == "Title"
    assert content.metadata["source"] == "elecfreaks"


def test_extract_metadata():
    """Test metadata extraction."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <head>
        <meta name="description" content="A test tutorial about electronics" />
    </head>
    <body>
    <article>
        <h1>Test</h1>
    </article>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    content = adapter.extract(soup, "https://wiki.elecfreaks.com/test")

    assert content.metadata["description"] == "A test tutorial about electronics"
    assert content.metadata["url"] == "https://wiki.elecfreaks.com/test"


def test_extract_tutorial_links_basic():
    """Test extracting tutorial links from index page."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <ul>
        <li><a href="/en/microbit/nezha-kit/case_01">Case 01: Robot</a></li>
        <li><a href="/en/microbit/nezha-kit/case_02">Case 02: Car</a></li>
        <li><a href="/en/microbit/nezha-kit/case_03">Case 03: Crane</a></li>
    </ul>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    tutorials = adapter.extract_tutorial_links(soup, "https://wiki.elecfreaks.com/en/microbit/nezha-kit/")

    assert len(tutorials) == 3
    assert tutorials[0].title == "Case 01: Robot"
    assert "case_01" in tutorials[0].url
    assert tutorials[1].title == "Case 02: Car"
    assert tutorials[2].title == "Case 03: Crane"


def test_extract_tutorial_links_absolute_urls():
    """Test that relative URLs are made absolute."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <a href="/en/microbit/case_01">Case 01</a>
    <a href="https://wiki.elecfreaks.com/en/microbit/case_02">Case 02</a>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    tutorials = adapter.extract_tutorial_links(soup, "https://wiki.elecfreaks.com/en/microbit/")

    assert len(tutorials) == 2
    assert tutorials[0].url.startswith("https://")
    assert tutorials[1].url.startswith("https://")


def test_extract_tutorial_links_deduplication():
    """Test that duplicate URLs are removed."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <a href="/en/case_01">Case 01</a>
    <a href="/en/case_01">Case 01 Again</a>
    <a href="/en/case_02">Case 02</a>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    tutorials = adapter.extract_tutorial_links(soup, "https://wiki.elecfreaks.com/en/")

    assert len(tutorials) == 2


def test_extract_tutorial_links_no_case_links():
    """Test that non-case links are ignored."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <a href="/en/about">About</a>
    <a href="/en/contact">Contact</a>
    <a href="/en/case_01">Case 01</a>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    tutorials = adapter.extract_tutorial_links(soup, "https://wiki.elecfreaks.com/en/")

    assert len(tutorials) == 1
    assert tutorials[0].title == "Case 01"


def test_extract_tutorial_links_skips_current_page():
    """Test that the current page URL is not included."""
    adapter = ElecfreaksAdapter()

    html = """
    <html>
    <body>
    <a href="/en/microbit/case_index/">Case Index</a>
    <a href="/en/microbit/case_01">Case 01</a>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    # The current page contains "case" in its path
    tutorials = adapter.extract_tutorial_links(soup, "https://wiki.elecfreaks.com/en/microbit/case_index/")

    assert len(tutorials) == 1
    assert "case_01" in tutorials[0].url
