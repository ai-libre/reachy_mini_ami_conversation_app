"""
Logging configuration for Reachy MCP Server.

Provides structured, configurable logging with audit trail support.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import get_config


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Colored, human-readable formatter for console output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Format: [TIMESTAMP] LEVEL: message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {color}{record.levelname:8}{reset}: {record.getMessage()}"

        # Add exception if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


class AuditLogger:
    """
    Audit logger for robot command tracking.

    Logs all robot commands to JSONL file for security/debugging.
    """

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_command(
        self,
        tool_name: str,
        arguments: dict,
        result: str,
        success: bool,
        user: str = "unknown",
        duration_ms: float = 0.0,
        error: str | None = None,
    ) -> None:
        """
        Log robot command execution.

        Args:
            tool_name: Name of tool executed
            arguments: Tool arguments
            result: Execution result
            success: Whether execution succeeded
            user: User who executed command
            duration_ms: Execution duration in milliseconds
            error: Error message if failed
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "success": success,
            "user": user,
            "duration_ms": duration_ms,
            "error": error,
        }

        # Append to JSONL file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


def setup_logging() -> tuple[logging.Logger, AuditLogger]:
    """
    Setup logging configuration.

    Creates both application logger and audit logger.

    Returns:
        tuple: (app_logger, audit_logger)
    """
    config = get_config()

    # Create root logger
    logger = logging.getLogger("reachy_mcp")
    logger.setLevel(config.log_level)
    logger.propagate = False

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.log_level)

    if config.structured_logging:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(HumanReadableFormatter())

    logger.addHandler(console_handler)

    # File handler
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setLevel(config.log_level)

    # Always use structured format for file
    file_handler.setFormatter(StructuredFormatter())
    logger.addHandler(file_handler)

    # Create audit logger
    audit_logger = AuditLogger(config.audit_log)

    logger.info(
        "Logging configured",
        extra={
            "extra_fields": {
                "log_level": config.log_level,
                "log_file": str(config.log_file),
                "audit_log": str(config.audit_log),
                "structured": config.structured_logging,
            }
        },
    )

    return logger, audit_logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get logger instance.

    Args:
        name: Logger name (uses module name if None)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"reachy_mcp.{name}")
    return logging.getLogger("reachy_mcp")


# Global audit logger instance
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        config = get_config()
        _audit_logger = AuditLogger(config.audit_log)
    return _audit_logger
