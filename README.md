# M5S13

ChatGPT HTML export to Markdown converter with YAML frontmatter.

## Setup

This project uses [UV](https://github.com/astral-sh/uv) for Python dependency management.

### Prerequisites

- Python 3.8 or higher
- UV package manager (already installed)

### Installation

Dependencies are already installed. If you need to reinstall or update:

```bash
uv sync
```

### Usage

Run the ChatGPT HTML to Markdown converter:

```bash
uv run python scripts/oneoff/parse-long-chat.py path/to/chatgpt-export.html
```

### Development

To add new dependencies:

```bash
uv add package-name
```

To run with development tools:

```bash
uv run python script.py
```