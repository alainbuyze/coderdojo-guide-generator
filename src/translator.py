"""Dutch translation module using deep-translator."""

import inspect
import logging
import re
import time
from copy import deepcopy

from deep_translator import GoogleTranslator

from src.core.config import get_settings
from src.core.errors import TranslationError
from src.sources.base import ExtractedContent

settings = get_settings()
logger = logging.getLogger(__name__)

# Delay between translation calls to avoid rate limiting
TRANSLATION_DELAY_SECONDS = 0.5

# Maximum text length for single translation (Google limit)
MAX_TRANSLATION_LENGTH = 4500


def translate_text(text: str, source: str = "en", target: str = "nl") -> str:
    """Translate text from source to target language.

    Args:
        text: Text to translate.
        source: Source language code.
        target: Target language code.

    Returns:
        Translated text.

    Raises:
        TranslationError: If translation fails.
    """
    if not text or not text.strip():
        return text

    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Translating: {text[:100]}{'...' if len(text) > 100 else ''}")

    try:
        translator = GoogleTranslator(source=source, target=target)
        translated = translator.translate(text)
        return translated or text
    except Exception as e:
        logger.warning(f"Translation failed for text: {text[:50]}... Error: {e}")
        raise TranslationError(f"Failed to translate: {e}") from e


def _extract_code_blocks(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Extract code blocks from text and replace with placeholders.

    Args:
        text: Text containing code blocks.

    Returns:
        Tuple of (text with placeholders, list of (placeholder, code) pairs).
    """
    code_blocks = []
    placeholder_template = "___CODE_BLOCK_{0}___"

    # Match fenced code blocks
    pattern = r"```[\s\S]*?```|`[^`]+`"

    def replace_code(match):
        code = match.group(0)
        placeholder = placeholder_template.format(len(code_blocks))
        code_blocks.append((placeholder, code))
        return placeholder

    text_without_code = re.sub(pattern, replace_code, text)
    return text_without_code, code_blocks


def _restore_code_blocks(text: str, code_blocks: list[tuple[str, str]]) -> str:
    """Restore code blocks from placeholders.

    Args:
        text: Text with placeholders.
        code_blocks: List of (placeholder, code) pairs.

    Returns:
        Text with code blocks restored.
    """
    for placeholder, code in code_blocks:
        text = text.replace(placeholder, code)
    return text


def translate_text_preserving_code(text: str, source: str = "en", target: str = "nl") -> str:
    """Translate text while preserving code blocks.

    Args:
        text: Text to translate (may contain code blocks).
        source: Source language code.
        target: Target language code.

    Returns:
        Translated text with code blocks preserved.
    """
    if not text or not text.strip():
        return text

    # Extract code blocks
    text_without_code, code_blocks = _extract_code_blocks(text)

    # If it's all code, return as-is
    if not text_without_code.strip() or text_without_code.strip().startswith("___CODE_BLOCK"):
        return text

    try:
        # Translate the text part
        translated = translate_text(text_without_code, source, target)

        # Restore code blocks
        result = _restore_code_blocks(translated, code_blocks)
        return result

    except TranslationError:
        # Return original on failure
        return text


def _chunk_text(text: str, max_length: int = MAX_TRANSLATION_LENGTH) -> list[str]:
    """Split text into chunks for translation.

    Args:
        text: Text to split.
        max_length: Maximum length per chunk.

    Returns:
        List of text chunks.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by sentences (roughly)
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += (" " if current_chunk else "") + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Handle very long sentences
            if len(sentence) > max_length:
                # Split by words
                words = sentence.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= max_length:
                        current_chunk += (" " if current_chunk else "") + word
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def translate_content(content: ExtractedContent) -> ExtractedContent:
    """Translate extracted content to Dutch.

    Translates: title, section headings, section content text.
    Preserves: code blocks, image references, URLs.

    Args:
        content: Extracted content to translate.

    Returns:
        New ExtractedContent with translated text and metadata["language"] = "nl".

    Raises:
        TranslationError: If critical translation failure occurs.
    """
    logger.debug(
        f" * {inspect.currentframe().f_code.co_name} > Translating content: {content.title}"
    )

    # Check if translation is enabled
    if not settings.TRANSLATE_ENABLED:
        logger.debug("    -> Translation disabled in settings")
        return content

    source = settings.TRANSLATION_SOURCE
    target = settings.TRANSLATION_TARGET

    try:
        # Deep copy to avoid modifying original
        translated = deepcopy(content)

        # Translate title
        logger.debug(f"    -> Translating title: {content.title}")
        translated.title = translate_text(content.title, source, target)
        time.sleep(TRANSLATION_DELAY_SECONDS)

        # Translate description if present
        if translated.metadata.get("description"):
            logger.debug("    -> Translating description")
            translated.metadata["description"] = translate_text(
                translated.metadata["description"], source, target
            )
            time.sleep(TRANSLATION_DELAY_SECONDS)

        # Translate sections
        for idx, section in enumerate(translated.sections):
            # Translate heading
            heading = section.get("heading", "")
            if heading:
                section["heading"] = translate_text(heading, source, target)
                time.sleep(TRANSLATION_DELAY_SECONDS)

            # Translate content elements (HTML tags)
            section_content = section.get("content", [])
            for elem_idx, element in enumerate(section_content):
                if hasattr(element, "string") and element.string:
                    # Translate text nodes
                    original_text = element.string
                    if original_text.strip():
                        chunks = _chunk_text(original_text)
                        translated_chunks = []
                        for chunk in chunks:
                            translated_chunk = translate_text_preserving_code(chunk, source, target)
                            translated_chunks.append(translated_chunk)
                            time.sleep(TRANSLATION_DELAY_SECONDS)
                        element.string.replace_with(" ".join(translated_chunks))
                elif hasattr(element, "get_text"):
                    # For complex elements, translate all text
                    for text_node in element.find_all(string=True):
                        if text_node.strip() and text_node.parent.name not in [
                            "code",
                            "pre",
                            "script",
                            "style",
                        ]:
                            original = str(text_node)
                            if len(original.strip()) > 2:  # Skip very short strings
                                chunks = _chunk_text(original)
                                translated_parts = []
                                for chunk in chunks:
                                    trans = translate_text_preserving_code(chunk, source, target)
                                    translated_parts.append(trans)
                                    time.sleep(TRANSLATION_DELAY_SECONDS)
                                text_node.replace_with(" ".join(translated_parts))

            logger.debug(f"    -> Translated section {idx + 1}/{len(translated.sections)}")

        # Mark as translated
        translated.metadata["language"] = target
        translated.metadata["original_language"] = source

        logger.debug(f"    -> Translation complete: {translated.title}")
        return translated

    except Exception as e:
        error_context = {
            "title": content.title,
            "sections": len(content.sections),
            "error_type": type(e).__name__,
        }
        logger.error(f"Translation failed: {e} | Context: {error_context}")
        raise TranslationError(f"Failed to translate content: {e}") from e
