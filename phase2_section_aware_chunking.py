#!/usr/bin/env python3
"""Create section-aware chunks for the bond document.

The source is a PDF extraction, so headings and page headers are not always
perfectly separated. This parser uses explicit numbered subsection boundaries
as the primary unit and only splits an oversized subsection at paragraph or
numbered-list boundaries. It never combines unrelated numbered sections.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PAGE_RE = re.compile(r"\[PAGE BOUNDARY:\s*Page\s+(\d+)\]", re.IGNORECASE)
MAIN_SECTION_RE = re.compile(
    r"^\s*(?:\d+\s+)?SECTION\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE
)
SUBSECTION_RE = re.compile(
    r"^\s*(\d{1,2}\.\d{1,2})(?:\s+(.+?))?\s*$"
)
ITEM_RE = re.compile(r"(?m)^\s*(?:\([a-z]\)|\([ivx]+\)|\d+\))\s+")


def clean_line(line: str) -> str:
    return re.sub(r"[ \t]+", " ", line).strip()


def nearest_page(lines: List[str], line_number: int) -> Optional[int]:
    for index in range(line_number, -1, -1):
        match = PAGE_RE.search(lines[index])
        if match:
            return int(match.group(1))
    return None


def split_at_boundaries(text: str, max_words: int) -> List[str]:
    """Split only at paragraph/list boundaries when a section is very large."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [part.strip() for part in re.split(r"(?m)(?=^\s*(?:\([a-z]\)|\([ivx]+\)|\d+\))\s+)", text) if part.strip()]

    expanded: List[str] = []
    for paragraph in paragraphs:
        if len(paragraph.split()) <= max_words:
            expanded.append(paragraph)
            continue
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
            if sentence.strip()
        ]
        if len(sentences) == 1:
            words = paragraph.split()
            expanded.extend(
                " ".join(words[index:index + max_words])
                for index in range(0, len(words), max_words)
            )
        else:
            expanded.extend(sentences)

    paragraphs = expanded
    parts: List[str] = []
    current: List[str] = []
    current_words = 0
    for paragraph in paragraphs:
        words = len(paragraph.split())
        if current and current_words + words > max_words:
            parts.append("\n\n".join(current))
            current = []
            current_words = 0
        current.append(paragraph)
        current_words += words
    if current:
        parts.append("\n\n".join(current))
    return parts or [text.strip()]


def parse_sections(text: str, max_words: int = 850) -> Tuple[List[Dict], Dict]:
    lines = text.splitlines()
    subsection_matches = [
        (line_number, match)
        for line_number, line in enumerate(lines)
        if (match := SUBSECTION_RE.match(line))
    ]
    if not subsection_matches:
        raise ValueError("No numbered subsections were found in the bond document")

    chunks: List[Dict] = []
    id_counts: Dict[str, int] = {}
    for index, (line_number, match) in enumerate(subsection_matches):
        end_line = (
            subsection_matches[index + 1][0]
            if index + 1 < len(subsection_matches)
            else len(lines)
        )
        section_number = match.group(1)
        if not 1 <= int(section_number.split(".", 1)[0]) <= 11:
            continue
        inline_title = clean_line(match.group(2) or "")
        body_lines = lines[line_number + 1:end_line]
        body = "\n".join(body_lines).strip()
        body = PAGE_RE.sub("", body).strip()
        # Numeric values in financial tables can look like subsection headers.
        # Require a meaningful body so those false boundaries are discarded.
        if len(body.split()) < 20:
            continue

        parent_number = section_number.split(".", 1)[0]
        parent_title = ""
        for previous_line in reversed(lines[:line_number]):
            parent_match = MAIN_SECTION_RE.match(previous_line)
            if parent_match:
                parent_title = clean_line(parent_match.group(2))
                break

        title = inline_title or parent_title or f"Section {section_number}"
        parts = split_at_boundaries(body, max_words) if len(body.split()) > max_words else [body]
        page = nearest_page(lines, line_number)
        for part_index, part in enumerate(parts, start=1):
            suffix = f".part{part_index}" if len(parts) > 1 else ""
            base_id = f"section_{section_number.replace('.', '_')}{suffix}"
            id_counts[base_id] = id_counts.get(base_id, 0) + 1
            occurrence_suffix = (
                f".occ{id_counts[base_id]}" if id_counts[base_id] > 1 else ""
            )
            chunks.append(
                {
                    "id": f"{base_id}{occurrence_suffix}",
                    "source_section": section_number + suffix + occurrence_suffix,
                    "source_title": title,
                    "parent_section": parent_number,
                    "page": page,
                    "chunk_type": "numbered_subsection"
                    if len(parts) == 1
                    else "numbered_subsection_part",
                    "text": part,
                    "word_count": len(part.split()),
                }
            )

    stats = {
        "total_chunks": len(chunks),
        "total_words": sum(chunk["word_count"] for chunk in chunks),
        "min_words": min((chunk["word_count"] for chunk in chunks), default=0),
        "max_words": max((chunk["word_count"] for chunk in chunks), default=0),
        "avg_words": (
            sum(chunk["word_count"] for chunk in chunks) / len(chunks)
            if chunks
            else 0
        ),
        "numbered_subsections": len(subsection_matches),
        "max_section_words": max_words,
        "strategy": "numbered subsection boundaries with paragraph/item splitting",
    }
    return chunks, stats


def main() -> None:
    root = Path.cwd()
    input_file = root / "phase1_output" / "bond_cleaned.txt"
    output_dir = root / "phase2_output"
    output_dir.mkdir(exist_ok=True)
    if not input_file.exists():
        raise FileNotFoundError(f"Bond document not found: {input_file}")

    text = input_file.read_text(encoding="utf-8")
    chunks, stats = parse_sections(text, max_words=450)
    (output_dir / "section_aware_chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "section_aware_chunking_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Generated %d section-aware chunks", len(chunks))
    logger.info("Chunk size: %d-%d words; average %.1f", stats["min_words"], stats["max_words"], stats["avg_words"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
