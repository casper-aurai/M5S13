#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chat_html_to_md.py
Convert a ChatGPT HTML conversation dump to Markdown with YAML frontmatter.
- Preserves message order
- Extracts code blocks with language detection and ~~~ fences (not backticks)
- Converts headings, paragraphs, lists, blockquotes
- Keeps inline code; escapes backticks inside inline code spans
- Collects canonical URL, title, and timestamps into frontmatter

Dependencies: beautifulsoup4, lxml
    pip install beautifulsoup4 lxml
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import sys
import logging
from collections import defaultdict
from typing import Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Track transformations for summary
transform_stats = defaultdict(int)

def log_transform(element_type: str, details: str = "") -> None:
    """Log transformation with stats tracking."""
    transform_stats[element_type] += 1
    if details:
        logger.info(f"{element_type}: {details}")
    else:
        logger.info(element_type)

def print_transform_summary() -> None:
    """Print summary of all transformations made."""
    if transform_stats:
        logger.info("Transformation Summary:")
        for transform, count in sorted(transform_stats.items()):
            logger.info(f"  {transform}: {count}")
    else:
        logger.info("No transformations tracked")

LANG_PATTERNS = (
    re.compile(r"(?:language|lang|code\-lang|syntax)\-([A-Za-z0-9\+\#\-\_]+)"),
    re.compile(r"highlight\-source\-([A-Za-z0-9\+\#\-\_]+)"),
)

MERMAID_PATTERNS = (
    re.compile(r"mermaid", re.IGNORECASE),
    re.compile(r"diagram", re.IGNORECASE),
    re.compile(r"flowchart|gantt|sequenceDiagram|classDiagram|stateDiagram|journey|pie|requirement|gitgraph|timeline", re.IGNORECASE),
    re.compile(r"flowchart\s+(?:TD|TB|BT|RL|LR)", re.IGNORECASE),
    # Additional patterns for edge cases
    re.compile(r"subgraph|direction|classDef", re.IGNORECASE),
    re.compile(r"-->|-\.-|\.->|---", re.IGNORECASE),  # Common mermaid arrows
)

# --- Utilities ----------------------------------------------------------------

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def write_file(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def iso(dtobj: dt.datetime) -> str:
    return dtobj.replace(microsecond=0).isoformat()

def clean_ws(text: str) -> str:
    # Normalize line endings and collapse excessive blank lines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def unescape_html(text: str) -> str:
    return html.unescape(text)

def guess_code_language(tag: Tag) -> Optional[str]:
    # Try classes first
    classes = tag.get("class", []) or []
    class_str = " ".join(classes)

    # Check for mermaid patterns in class names
    for pattern in MERMAID_PATTERNS:
        if pattern.search(class_str):
            log_transform("MERMAID_DETECTED", f"class: {class_str}")
            return "mermaid"

    for rx in LANG_PATTERNS:
        m = rx.search(class_str)
        if m:
            return m.group(1).lower()

    # Check for mermaid in the actual content
    code_el = tag.find("code")
    if code_el:
        content = code_el.get_text()
        for pattern in MERMAID_PATTERNS:
            if pattern.search(content):
                log_transform("MERMAID_DETECTED", f"content: {content[:50]}...")
                return "mermaid"

    # Try attributes commonly used for language hints
    for attr in ("data-language", "data-lang", "lang"):
        if tag.has_attr(attr) and str(tag[attr]).strip():
            lang = str(tag[attr]).strip().lower()
            # Check if it's a mermaid variant
            for pattern in MERMAID_PATTERNS:
                if pattern.search(lang):
                    log_transform("MERMAID_DETECTED", f"attribute: {lang}")
                    return "mermaid"
            return lang

    # Probe <code> child classes
    if code_el:
        classes = code_el.get("class", []) or []
        for rx in LANG_PATTERNS:
            m = rx.search(" ".join(classes))
            if m:
                return m.group(1).lower()
        for attr in ("data-language", "data-lang", "lang"):
            if code_el.has_attr(attr) and str(code_el[attr]).strip():
                return str(code_el[attr]).strip().lower()
    return None

def fence_code(code: str, lang: Optional[str]) -> str:
    # Special handling for mermaid diagrams - use backticks for better compatibility
    if lang == "mermaid":
        # Use backticks for mermaid diagrams as they're more widely supported
        return f"```mermaid\n{code.rstrip()}\n```"

    # For other languages, ensure no trailing spaces and consistent newlines inside code.
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    # Avoid triple-tilde conflicts: if code contains ~~~, lengthen the fence.
    fence = "~~~"
    if "~~~" in code:
        fence = "~~~~"
    lang_suffix = (lang or "").strip()
    header = f"{fence}{lang_suffix and ' ' + lang_suffix}"
    return f"{header}\n{code.rstrip()}\n{fence}"

def escape_backticks_inline(text: str) -> str:
    # Inside inline code markers we escape backticks. We’ll apply when converting <code> inline.
    return text.replace("`", r"\`")

def text_of(tag: Tag) -> str:
    # Get visible text with single newlines between block children.
    # Avoid including script/style text; BeautifulSoup excludes them by default.
    return tag.get_text(separator="\n", strip=True)

def extract_mermaid_content(tag: Tag) -> Optional[str]:
    """Extract raw mermaid content from HTML tags, preserving exact syntax."""
    # Look for mermaid in class names or content
    classes = tag.get("class", []) or []
    class_str = " ".join(classes).lower()

    for pattern in MERMAID_PATTERNS:
        if pattern.search(class_str):
            # Extract raw text content
            content = tag.get_text("\n")
            return cleanup_mermaid_content(content.strip())

    # Check if content contains mermaid patterns
    content = tag.get_text("\n")
    for pattern in MERMAID_PATTERNS:
        if pattern.search(content):
            return cleanup_mermaid_content(content.strip())

    return None

def cleanup_mermaid_content(content: str) -> str:
    """Clean up mermaid content to fix common parsing issues."""
    lines = content.split('\n')
    cleaned_lines = []

    for line in lines:
        original_line = line
        line = line.strip()

        # Fix common issues that cause parsing errors
        # Remove problematic characters at the end of lines
        line = re.sub(r'[^\x20-\x7E\n]+$', '', line)  # Remove non-ASCII chars at end

        # Fix malformed arrows and connections
        line = re.sub(r'-\.-+', '--', line)  # Fix dotted arrows
        line = re.sub(r'-\.+>', '->', line)  # Fix dotted arrows
        line = re.sub(r'--+>', '->', line)   # Fix multiple dashes
        line = re.sub(r'<-+', '<-', line)    # Fix multiple dashes

        # Fix bracket issues
        line = re.sub(r'\[\s*\]', '[]', line)  # Remove spaces in empty brackets

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)

# --- Block conversion ----------------------------------------------------------

def convert_inline(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if isinstance(node, Tag):
        name = node.name.lower()
        if name in {"strong", "b"}:
            return f"**{''.join(convert_inline(c) for c in node.children)}**"
        if name in {"em", "i"}:
            return f"*{''.join(convert_inline(c) for c in node.children)}*"
        if name == "code":
            content = ''.join(convert_inline(c) for c in node.children)
            return f"`{escape_backticks_inline(content)}`"
        if name == "a":
            href = node.get("href") or ""
            label = ''.join(convert_inline(c) for c in node.children) or href
            return f"[{label}]({href})" if href else label
        if name in {"span", "u", "mark"}:
            return ''.join(convert_inline(c) for c in node.children)
        if name in {"br"}:
            return "  \n"
        # Default: recurse into children
        return ''.join(convert_inline(c) for c in node.children)
    return ""

def convert_list(ul_or_ol: Tag, ordered: bool) -> str:
    out: List[str] = []
    idx = 1
    for li in ul_or_ol.find_all("li", recursive=False):
        # Convert LI content (block and inline)
        para_chunks: List[str] = []
        # If LI has block children, handle; else treat as inline
        block_children = [c for c in li.children if isinstance(c, Tag) and c.name.lower() in ("p", "ul", "ol")]
        if not block_children:
            # Simple inline LI
            line = convert_inline(li)
            prefix = f"{idx}." if ordered else "-"
            out.append(f"{prefix} {line.strip()}")
        else:
            # First paragraph
            first = li.find("p", recursive=False)
            head = convert_inline(first) if first else convert_inline(li)
            prefix = f"{idx}." if ordered else "-"
            out.append(f"{prefix} {head.strip()}")
            # Nested lists
            for nested in li.find_all(["ul", "ol"], recursive=False):
                nested_str = convert_list(nested, ordered=(nested.name.lower() == "ol"))
                # Indent nested by two spaces
                nested_str = "\n".join(("  " + ln) if ln.strip() else ln for ln in nested_str.splitlines())
                out.append(nested_str)
        idx += 1
    return "\n".join(out)

def convert_block(node: Tag) -> Optional[str]:
    name = node.name.lower()
    if name in {"script", "style"}:
        return None

    # Log major element conversions
    if name in {"h1","h2","h3","h4","h5","h6","p","blockquote","pre","code","ul","ol","table"}:
        log_transform(f"HTML_{name.upper()}")

    if name in {"h1","h2","h3","h4","h5","h6"}:
        level = int(name[1])
        hashes = "#" * level
        return f"{hashes} {text_of(node)}"
    if name in {"p"}:
        return convert_inline(node).strip()
    if name in {"blockquote"}:
        inner = "\n".join(filter(None, ((convert_block(c) or "") for c in node.children if isinstance(c, Tag))))
        if not inner:
            inner = convert_inline(node)
        quoted = "\n".join([f"> {ln}" if ln.strip() else ">" for ln in inner.splitlines()])
        return quoted
    if name == "pre":
        # Block code
        lang = guess_code_language(node)

        # Special handling for mermaid diagrams
        mermaid_content = extract_mermaid_content(node)
        if mermaid_content and (lang == "mermaid" or not lang):
            log_transform("MERMAID_BLOCK", f"length: {len(mermaid_content)}")
            return fence_code(mermaid_content, "mermaid")

        code_el = node.find("code")
        raw = code_el.get_text("\n") if code_el else node.get_text("\n")
        log_transform("CODE_BLOCK", f"lang: {lang or 'unknown'}")
        return fence_code(raw, lang)
    if name == "code":
        # Only treat as block if it has multiple lines and parent is not <pre>
        if node.parent and node.parent.name.lower() == "pre":
            return None
        raw = node.get_text("\n")
        if "\n" in raw:
            log_transform("CODE_BLOCK", f"lang: {guess_code_language(node) or 'unknown'}")
            return fence_code(raw, guess_code_language(node))
        # otherwise inline; will be handled by convert_inline within <p>
        return None
    if name in {"ul", "ol"}:
        return convert_list(node, ordered=(name == "ol"))
    if name in {"hr"}:
        return "---"
    if name in {"table"}:
        # Basic table to markdown (pipe table). Keep simple, no alignment calc.
        rows = node.find_all("tr")
        if not rows:
            return None
        def row_text(tr: Tag) -> List[str]:
            cells = tr.find_all(["th","td"])
            return [convert_inline(td).strip().replace("\n", " ") for td in cells]
        md_rows = [row_text(r) for r in rows]
        if md_rows:
            header = md_rows[0]
            sep = ["---"] * len(header)
            lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
            for r in md_rows[1:]:
                lines.append("| " + " | ".join(r) + " |")
            return "\n".join(lines)
    # Generic container: descend and collect children blocks
    if name in {"div","section","article"}:
        parts = []
        for child in node.children:
            if isinstance(child, Tag):
                blk = convert_block(child)
                if blk:
                    parts.append(blk)
        if parts:
            return "\n\n".join([p for p in parts if p.strip()])
        return None
    # Fallback: plain text
    txt = node.get_text("\n", strip=True)
    return txt if txt else None

# --- Conversation extraction ---------------------------------------------------

def find_message_roots(soup: BeautifulSoup) -> List[Tag]:
    """
    Attempt to find message containers in a ChatGPT export.
    Preference order:
    1) Nodes with data-message-author-role + data-message-id
    2) Article/section nodes with role="article" or [data-testid*='conversation']
    3) Fallback to main content container
    """
    nodes = soup.select("[data-message-author-role][data-message-id]")
    if nodes:
        return nodes
    nodes = soup.select("article[role='article'], section[role='article'], [data-testid*='conversation']")
    if nodes:
        return nodes
    main = soup.find(id="main") or soup.find("main")
    return [main] if main else [soup.body or soup]

def label_of(msg: Tag) -> str:
    # Try to label by author role if present
    role = msg.get("data-message-author-role") or ""
    if role:
        return role.strip()
    # Sometimes the class names include 'user' or 'assistant'
    classes = " ".join(msg.get("class", [])).lower()
    if "assistant" in classes:
        return "assistant"
    if "user" in classes:
        return "user"
    return "message"

def extract_messages(root: Tag) -> List[Tuple[str, str]]:
    """
    Convert each message root into Markdown chunk.
    Returns list of (label, markdown_block).
    """
    out: List[Tuple[str, str]] = []
    # If root looks like a single message container, convert directly
    # Otherwise, dive into likely message children
    candidates = []
    if root.has_attr("data-message-id"):
        candidates = [root]
    else:
        candidates = root.select("[data-message-author-role][data-message-id]") or root.find_all(["article","section","div"], recursive=True)

    if not candidates:
        candidates = [root]

    seen_ids = set()
    for c in candidates:
        # Deduplicate via data-message-id if present
        mid = c.get("data-message-id")
        if mid:
            if mid in seen_ids:
                continue
            seen_ids.add(mid)

        lbl = label_of(c)
        md = convert_block(c) or ""
        md = clean_ws(md)
        if md:
            log_transform("MESSAGE_EXTRACTED", f"label: {lbl}")
            out.append((lbl, md))
    return out

# --- Frontmatter ---------------------------------------------------------------

def build_frontmatter(title: str, src_path: str, soup: BeautifulSoup) -> str:
    # Attempt to get canonical URL
    canonical = soup.find("link", rel="canonical")
    src_url = canonical.get("href") if canonical and canonical.has_attr("href") else ""

    og_title = soup.find("meta", property="og:title")
    meta_title = og_title.get("content").strip() if og_title and og_title.has_attr("content") else ""

    page_title = (title or meta_title or (soup.title.string.strip() if soup.title and soup.title.string else "")) or os.path.basename(src_path)

    now = dt.datetime.now()
    try:
        mtime = dt.datetime.fromtimestamp(os.path.getmtime(src_path))
    except Exception:
        mtime = now

    fm = {
        "title": page_title,
        "source_file": os.path.basename(src_path),
        "source_url": src_url,
        "exported_at": iso(now),
        "file_mtime": iso(mtime),
        "generator": "chat-html2md/0.1",
        "tags": ["chatgpt", "conversation", "import"],
    }

    # Render YAML manually (no PyYAML dependency)
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            items = ", ".join([str(x) for x in v])
            lines.append(f"{k}: [{items}]")
        else:
            # Escape quotes minimally
            sv = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{sv}"')
    lines.append("---")
    return "\n".join(lines)

# --- Main ---------------------------------------------------------------------

def validate_markdown(md: str) -> List[str]:
    """Basic validation for markdown content."""
    issues = []

    # Check for unmatched code block fences
    backtick_blocks = md.count("```")
    if backtick_blocks % 2 != 0:
        issues.append("Unmatched backtick code block fences")

    tilde_blocks = md.count("~~~")
    if tilde_blocks % 2 != 0:
        issues.append("Unmatched tilde code block fences")

    # Check for common markdown issues
    lines = md.split('\n')
    for i, line in enumerate(lines, 1):
        # Check for headings without space after #
        if re.match(r'^#{1,6}[^ #]', line):
            issues.append(f"Line {i}: Heading without space after #")

        # Check for links without proper brackets
        if '[[' in line and ']]' not in line:
            issues.append(f"Line {i}: Potential malformed wikilink")

    return issues

def find_mermaid_blocks(md: str) -> List[str]:
    """Extract mermaid diagram blocks from markdown."""
    blocks = []
    lines = md.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("```mermaid"):
            # Found start of mermaid block
            block_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith("```"):
                    # End of block
                    blocks.append('\n'.join(block_lines))
                    break
                block_lines.append(lines[i])
                i += 1
            else:
                # Unclosed block
                blocks.append('\n'.join(block_lines))
        else:
            i += 1

    return blocks

def html_to_markdown(html_text: str, src_path: str, custom_title: Optional[str]) -> str:
    logger.info("Starting HTML to Markdown conversion")
    soup = BeautifulSoup(html_text, "lxml")

    frontmatter = build_frontmatter(custom_title or "", src_path, soup)
    log_transform("FRONTMATTER_GENERATED")

    roots = find_message_roots(soup)
    logger.info(f"Found {len(roots)} message root(s)")

    # Collect messages from each root, preserving document order
    collected: List[Tuple[str,str]] = []
    for i, r in enumerate(roots):
        logger.info(f"Processing message root {i+1}/{len(roots)}")
        messages = extract_messages(r)
        collected.extend(messages)
        if messages:
            logger.info(f"Extracted {len(messages)} message(s) from root {i+1}")

    logger.info(f"Total collected {len(collected)} message(s)")

    # Post-process: prune empty/dup blocks and add labels as headings
    normalized: List[str] = []
    for lbl, md in collected:
        if not md:
            continue
        # Heuristic: if md looks like the entire page dump (overly large), skip; else keep
        normalized.append(f"### {lbl.capitalize()}\n\n{md}")

    body = "\n\n".join(dict.fromkeys(normalized))  # de-dup exact repeats while preserving order
    body = clean_ws(body)

    if not body:
        # Fallback: convert body wholesale
        logger.warning("No message content found, using fallback conversion")
        body = convert_block(soup.body or soup) or ""

    doc = frontmatter + ("\n\n" + body if body else "\n")
    final_doc = clean_ws(doc) + "\n"

    logger.info(f"Conversion complete: {len(final_doc)} characters generated")
    return final_doc

def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Convert ChatGPT HTML export to Markdown with frontmatter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s conversation.html
  %(prog)s conversation.html -o output.md
  %(prog)s conversation.html --debug --validate
        """
    )
    p.add_argument("html", help="Path to ChatGPT HTML export (e.g., foundation.html)")
    p.add_argument("-o", "--output", help="Output .md path (default: same name with .md)")
    p.add_argument("--title", help="Override frontmatter title", default=None)
    p.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    p.add_argument("-v", "--validate", action="store_true", help="Validate generated markdown")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without writing files")
    p.add_argument("--show-mermaid", action="store_true", help="Show detected mermaid diagrams")
    p.add_argument("--encoding", default="utf-8", help="Input file encoding (default: utf-8)")

    args = p.parse_args(argv)

    src_path = args.html
    if not os.path.exists(src_path):
        print(f"ERROR: File not found: {src_path}", file=sys.stderr)
        return 2

    try:
        with open(src_path, "r", encoding=args.encoding, errors="ignore") as f:
            html_text = f.read()
    except Exception as e:
        print(f"ERROR: Failed to read file {src_path}: {e}", file=sys.stderr)
        return 1

    if args.debug:
        print(f"DEBUG: Read {len(html_text)} characters from {src_path}")

    try:
        md = html_to_markdown(html_text, src_path, args.title)
    except Exception as e:
        print(f"ERROR: Failed to convert HTML to markdown: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

    if args.debug:
        print(f"DEBUG: Generated {len(md)} characters of markdown")

    if args.validate:
        issues = validate_markdown(md)
        if issues:
            print(f"WARNING: Found {len(issues)} validation issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("INFO: Markdown validation passed")

    if args.show_mermaid:
        mermaid_blocks = find_mermaid_blocks(md)
        if mermaid_blocks:
            print(f"INFO: Found {len(mermaid_blocks)} mermaid diagram(s):")
            for i, block in enumerate(mermaid_blocks, 1):
                print(f"\n--- Mermaid Diagram {i} ---")
                print(block)
        else:
            print("INFO: No mermaid diagrams found")

    # Print transformation summary
    print_transform_summary()

    if args.dry_run:
        print("DRY RUN - Would write the following markdown:")
        print("=" * 50)
        print(md[:500] + "..." if len(md) > 500 else md)
        return 0

    out_path = args.output or re.sub(r"\.html?$", ".md", src_path, flags=re.I) or (os.path.basename(src_path) + ".md")

    try:
        write_file(out_path, md)
        print(f"SUCCESS: Wrote {len(md)} characters to: {out_path}")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to write file {out_path}: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
