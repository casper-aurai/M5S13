#!/usr/bin/env python3
"""
Filesystem MCP Server

Provides secure file operations within workspace boundaries.
Implements stdio and WebSocket transport layers.
"""

import asyncio
import json
import logging
import os
import sys
import mimetypes
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Union

from base_mcp_server import MCPServer, MCPError, Tool


class FilesystemMCPServer(MCPServer):
    """Filesystem MCP Server implementation."""

    def __init__(self, workspace_root: Optional[str] = None, readonly: bool = False):
        super().__init__("filesystem", "1.0.0")

        # Resolve workspace root
        if workspace_root:
            self.workspace_root = Path(workspace_root).resolve()
        else:
            self.workspace_root = Path.cwd().resolve()

        self.readonly = readonly
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit

        # Ensure workspace root exists
        if not self.workspace_root.exists():
            raise MCPError("INVALID_CONFIG", f"Workspace root does not exist: {self.workspace_root}")

        logging.info(f"Filesystem server initialized with workspace root: {self.workspace_root}")
        logging.info(f"Read-only mode: {self.readonly}")

    def validate_path(self, path: str) -> Path:
        """Validate and resolve file path within workspace."""
        if not path:
            raise MCPError("INVALID_PARAMS", "Path cannot be empty")

        # Resolve the path
        try:
            resolved_path = Path(path).resolve()
        except Exception as e:
            raise MCPError("INVALID_PATH", f"Invalid path: {str(e)}")

        # Check if path is within workspace
        try:
            resolved_path.relative_to(self.workspace_root)
        except ValueError:
            raise MCPError(
                "PATH_OUTSIDE_WORKSPACE",
                f"Path is outside workspace: {path}",
                {"requested_path": path, "workspace_root": str(self.workspace_root)}
            )

        return resolved_path

    def check_read_permission(self, path: Path):
        """Check if read operation is allowed."""
        # Basic read permission check
        if not os.access(path, os.R_OK):
            raise MCPError("PERMISSION_DENIED", f"No read permission for: {path}")

    def check_write_permission(self, path: Path):
        """Check if write operation is allowed."""
        if self.readonly:
            raise MCPError("READONLY_MODE", "Server is in read-only mode")

        if not os.access(path.parent, os.W_OK):
            raise MCPError("PERMISSION_DENIED", f"No write permission for: {path}")

    async def setup_tools(self):
        """Setup filesystem tools."""
        # File reading tools
        self.register_tool(Tool(
            "fs_read",
            "Read the contents of a file",
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read (relative to workspace root)"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (1-indexed, default: 1)",
                        "minimum": 1
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number (inclusive, default: read entire file)",
                        "minimum": 1
                    }
                },
                "required": ["path"]
            },
            self.fs_read
        ))

        # File writing tools
        self.register_tool(Tool(
            "fs_write",
            "Write content to a file",
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write (relative to workspace root)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Write mode: 'overwrite' or 'append' (default: overwrite)",
                        "enum": ["overwrite", "append"],
                        "default": "overwrite"
                    }
                },
                "required": ["path", "content"]
            },
            self.fs_write
        ))

        # Directory listing tools
        self.register_tool(Tool(
            "fs_list",
            "List contents of a directory",
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (relative to workspace root, default: root)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List contents recursively (default: false)",
                        "default": False
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Include hidden files/directories (default: false)",
                        "default": False
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth for recursive listing (default: unlimited)",
                        "minimum": 1
                    }
                }
            },
            self.fs_list
        ))

        # File/directory info tools
        self.register_tool(Tool(
            "fs_stat",
            "Get information about a file or directory",
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to check (relative to workspace root)"
                    }
                },
                "required": ["path"]
            },
            self.fs_stat
        ))

        # Search tools
        self.register_tool(Tool(
            "fs_search",
            "Search for files and directories using glob patterns",
            {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to search for (e.g., '*.py', '**/*.md')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (relative to workspace root, default: root)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 100)",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 100
                    }
                },
                "required": ["pattern"]
            },
            self.fs_search
        ))

        # File deletion tools
        self.register_tool(Tool(
            "fs_delete",
            "Delete a file or directory",
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to delete (relative to workspace root)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Delete directory and contents recursively (default: false)",
                        "default": False
                    }
                },
                "required": ["path"]
            },
            self.fs_delete
        ))

    async def fs_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents with optional line range."""
        path = params["path"]
        encoding = params.get("encoding", "utf-8")
        start_line = params.get("start_line")
        end_line = params.get("end_line")

        resolved_path = self.validate_path(path)
        self.check_read_permission(resolved_path)

        if not resolved_path.is_file():
            raise MCPError("NOT_A_FILE", f"Path is not a file: {path}")

        # Check file size
        file_size = resolved_path.stat().st_size
        if file_size > self.max_file_size:
            raise MCPError(
                "FILE_TOO_LARGE",
                f"File is too large ({file_size} bytes > {self.max_file_size} bytes)",
                {"file_size": file_size, "max_size": self.max_file_size}
            )

        try:
            with open(resolved_path, 'r', encoding=encoding) as f:
                if start_line is not None or end_line is not None:
                    # Read specific line range
                    lines = f.readlines()
                    start_idx = (start_line or 1) - 1
                    end_idx = end_line if end_line is not None else len(lines)

                    if start_idx < 0 or start_idx >= len(lines):
                        raise MCPError("INVALID_LINE_RANGE", f"Start line out of range: {start_line}")

                    if end_idx < start_idx:
                        raise MCPError("INVALID_LINE_RANGE", f"End line must be >= start line")

                    content = "".join(lines[start_idx:end_idx])
                    return {
                        "content": content,
                        "lines_read": end_idx - start_idx,
                        "total_lines": len(lines)
                    }
                else:
                    # Read entire file
                    content = f.read()
                    return {
                        "content": content,
                        "size": file_size
                    }

        except UnicodeDecodeError as e:
            raise MCPError("ENCODING_ERROR", f"Failed to decode file with encoding {encoding}: {str(e)}")
        except Exception as e:
            raise MCPError("READ_ERROR", f"Failed to read file: {str(e)}")

    async def fs_write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file."""
        path = params["path"]
        content = params["content"]
        encoding = params.get("encoding", "utf-8")
        mode = params.get("mode", "overwrite")

        resolved_path = self.validate_path(path)
        self.check_write_permission(resolved_path)

        # Ensure parent directory exists
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if mode == "append":
                open_mode = "a"
            else:
                open_mode = "w"

            with open(resolved_path, open_mode, encoding=encoding) as f:
                f.write(content)

            return {
                "written": True,
                "path": path,
                "size": len(content)
            }

        except Exception as e:
            raise MCPError("WRITE_ERROR", f"Failed to write file: {str(e)}")

    async def fs_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents."""
        path = params.get("path", ".")
        recursive = params.get("recursive", False)
        show_hidden = params.get("show_hidden", False)
        max_depth = params.get("max_depth")

        resolved_path = self.validate_path(path)
        self.check_read_permission(resolved_path)

        if not resolved_path.is_dir():
            raise MCPError("NOT_A_DIRECTORY", f"Path is not a directory: {path}")

        def list_directory(dir_path: Path, depth: int = 0) -> List[Dict[str, Any]]:
            """Recursively list directory contents."""
            if max_depth is not None and depth >= max_depth:
                return []

            items = []
            try:
                for item in sorted(dir_path.iterdir()):
                    # Skip hidden files unless requested
                    if not show_hidden and item.name.startswith('.'):
                        continue

                    item_info = {
                        "name": item.name,
                        "path": str(item.relative_to(self.workspace_root)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                        "modified": item.stat().st_mtime
                    }

                    items.append(item_info)

                    # Recurse into directories if requested
                    if recursive and item.is_dir():
                        items.extend(list_directory(item, depth + 1))

            except PermissionError:
                logging.warning(f"Permission denied accessing: {dir_path}")
            except Exception as e:
                logging.error(f"Error listing directory {dir_path}: {e}")

            return items

        items = list_directory(resolved_path)
        return {
            "items": items,
            "count": len(items),
            "path": path
        }

    async def fs_stat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get file/directory information."""
        path = params["path"]

        resolved_path = self.validate_path(path)
        self.check_read_permission(resolved_path)

        if not resolved_path.exists():
            raise MCPError("PATH_NOT_FOUND", f"Path does not exist: {path}")

        stat_info = resolved_path.stat()

        # Get MIME type for files
        mime_type = None
        if resolved_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(resolved_path))

        return {
            "path": path,
            "exists": True,
            "type": "directory" if resolved_path.is_dir() else "file",
            "size": stat_info.st_size,
            "modified": stat_info.st_mtime,
            "created": stat_info.st_ctime,
            "mime_type": mime_type,
            "readable": os.access(resolved_path, os.R_OK),
            "writable": os.access(resolved_path, os.W_OK),
            "executable": os.access(resolved_path, os.X_OK)
        }

    async def fs_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for files using glob patterns."""
        pattern = params["pattern"]
        search_path = params.get("path", ".")
        max_results = params.get("max_results", 100)

        resolved_path = self.validate_path(search_path)
        self.check_read_permission(resolved_path)

        if not resolved_path.is_dir():
            raise MCPError("NOT_A_DIRECTORY", f"Search path is not a directory: {search_path}")

        matches = []
        try:
            # Use glob pattern matching
            import glob

            search_pattern = str(resolved_path / pattern)
            glob_results = glob.glob(search_pattern, recursive=True)

            # Convert to relative paths and limit results
            for result in glob_results[:max_results]:
                result_path = Path(result)
                try:
                    # Check if result is within workspace
                    result_path.relative_to(self.workspace_root)
                    relative_path = str(result_path.relative_to(self.workspace_root))

                    matches.append({
                        "path": relative_path,
                        "absolute_path": str(result_path),
                        "type": "directory" if result_path.is_dir() else "file",
                        "size": result_path.stat().st_size if result_path.is_file() else None
                    })
                except ValueError:
                    # Skip paths outside workspace
                    continue

        except Exception as e:
            raise MCPError("SEARCH_ERROR", f"Search failed: {str(e)}")

        return {
            "matches": matches,
            "count": len(matches),
            "pattern": pattern,
            "search_path": search_path,
            "max_results": max_results
        }

    async def fs_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete file or directory."""
        path = params["path"]
        recursive = params.get("recursive", False)

        resolved_path = self.validate_path(path)
        self.check_write_permission(resolved_path)

        if not resolved_path.exists():
            raise MCPError("PATH_NOT_FOUND", f"Path does not exist: {path}")

        try:
            if resolved_path.is_file():
                resolved_path.unlink()
                return {
                    "deleted": True,
                    "path": path,
                    "type": "file"
                }
            elif resolved_path.is_dir():
                if recursive:
                    import shutil
                    shutil.rmtree(resolved_path)
                    return {
                        "deleted": True,
                        "path": path,
                        "type": "directory",
                        "recursive": True
                    }
                else:
                    # Try to remove empty directory
                    resolved_path.rmdir()
                    return {
                        "deleted": True,
                        "path": path,
                        "type": "directory",
                        "recursive": False
                    }
        except OSError as e:
            if "Directory not empty" in str(e):
                raise MCPError(
                    "DIRECTORY_NOT_EMPTY",
                    f"Directory is not empty (use recursive=true to delete): {path}"
                )
            else:
                raise MCPError("DELETE_ERROR", f"Failed to delete: {str(e)}")
        except Exception as e:
            raise MCPError("DELETE_ERROR", f"Failed to delete: {str(e)}")


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Filesystem MCP Server")
    parser.add_argument(
        "--workspace-root",
        help="Workspace root directory (default: current directory)"
    )
    parser.add_argument(
        "--readonly",
        action="store_true",
        help="Run in read-only mode"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="stdio",
        help="Transport mechanism (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for WebSocket transport"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level"
    )

    args = parser.parse_args()

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Create server instance
        server = FilesystemMCPServer(
            workspace_root=args.workspace_root,
            readonly=args.readonly
        )

        # Configure transport
        if args.transport == "websocket":
            if not args.port:
                parser.error("--port is required for WebSocket transport")
            server.transport_type = "websocket"
            server.websocket_port = args.port
        else:
            server.transport_type = "stdio"

        # Start server
        await server.start()

    except KeyboardInterrupt:
        logging.info("Server interrupted by user")
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
