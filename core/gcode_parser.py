"""G-code parser for the CNC CAM and simulation workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


SUPPORTED_COMMANDS = {
    "G0",
    "G1",
    "G2",
    "G3",
    "G17",
    "G18",
    "G21",
    "G40",
    "G54",
    "G90",
    "G91",
    "G94",
    "G28",
    "G30",
    "G43",
    "M3",
    "M5",
    "M6",
    "M30",
}
MOTION_COMMANDS = {"G0", "G1", "G2", "G3"}
ARC_COMMANDS = {"G2", "G3"}
SUPPORTED_PARAMETERS = {"X", "Y", "Z", "F", "S", "I", "J", "K", "R", "T", "H", "D"}
COMMAND_PATTERN = re.compile(r"([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
PAREN_COMMENT_PATTERN = re.compile(r"\([^)]*\)")


@dataclass(frozen=True)
class GCodeCommand:
    """One parsed G-code line with normalized command and parameters."""

    line_number: int
    raw_line: str
    command: str
    x: float | None = None
    y: float | None = None
    z: float | None = None
    f: float | None = None
    s: float | None = None
    i: float | None = None
    j: float | None = None
    k: float | None = None
    r: float | None = None
    t: float | None = None
    h: float | None = None
    d: float | None = None
    distance_mode: str = "absolute"
    move_type: str = "unknown"
    is_motion: bool = False
    arc_direction: str | None = None
    warning: str | None = None


@dataclass(frozen=True)
class GCodeParseResult:
    """Summary and command list produced by the G-code parser."""

    commands: list[GCodeCommand] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    motion_count: int = 0
    total_line_count: int = 0
    valid_line_count: int = 0


class GCodeParser:
    """Parse basic Fanuc-style G-code into structured command objects."""

    def __init__(self) -> None:
        """Create a parser with modal motion state."""
        self._modal_motion_command: str | None = None
        self._distance_mode = "absolute"

    def parse(self, content: str) -> GCodeParseResult:
        """Parse G-code text and keep going when individual lines are invalid."""
        self._modal_motion_command = None
        self._distance_mode = "absolute"
        commands: list[GCodeCommand] = []
        warnings: list[str] = []
        lines = content.splitlines()

        for line_number, raw_line in enumerate(lines, start=1):
            cleaned_line = self._strip_comments(raw_line).strip().upper()
            if not cleaned_line or cleaned_line == "%":
                continue
            if cleaned_line.startswith("O") and cleaned_line[1:].isdigit():
                continue

            command = self._parse_line(line_number, raw_line, cleaned_line)
            commands.append(command)
            if command.warning:
                warnings.append(command.warning)

        return GCodeParseResult(
            commands=commands,
            warnings=warnings,
            motion_count=sum(1 for command in commands if command.is_motion),
            total_line_count=len(lines),
            valid_line_count=len(commands),
        )

    def _parse_line(self, line_number: int, raw_line: str, cleaned_line: str) -> GCodeCommand:
        """Parse one non-empty G-code line into a command object."""
        warning_parts: list[str] = []
        command_words, parameters = self._extract_words(line_number, cleaned_line, warning_parts)
        command = self._select_command(command_words, parameters)

        if command == "G90":
            self._distance_mode = "absolute"
        elif command == "G91":
            self._distance_mode = "incremental"
        if command in MOTION_COMMANDS:
            self._modal_motion_command = command

        if command not in SUPPORTED_COMMANDS:
            warning_parts.append(f"第 {line_number} 行：不支持或无法识别的指令")
        if command in ARC_COMMANDS:
            self._validate_arc_command(line_number, parameters, warning_parts)

        warning = "；".join(warning_parts) if warning_parts else None
        return GCodeCommand(
            line_number=line_number,
            raw_line=raw_line.rstrip(),
            command=command,
            x=parameters.get("X"),
            y=parameters.get("Y"),
            z=parameters.get("Z"),
            f=parameters.get("F"),
            s=parameters.get("S"),
            i=parameters.get("I"),
            j=parameters.get("J"),
            k=parameters.get("K"),
            r=parameters.get("R"),
            t=parameters.get("T"),
            h=parameters.get("H"),
            d=parameters.get("D"),
            distance_mode=self._distance_mode,
            move_type=self._move_type(command),
            is_motion=command in MOTION_COMMANDS,
            arc_direction="cw" if command == "G2" else "ccw" if command == "G3" else None,
            warning=warning,
        )

    def _extract_words(
        self,
        line_number: int,
        cleaned_line: str,
        warning_parts: list[str],
    ) -> tuple[list[str], dict[str, float]]:
        """Extract command words and supported numeric parameters from a line."""
        command_words: list[str] = []
        parameters: dict[str, float] = {}
        recognized_spans: list[tuple[int, int]] = []

        for match in COMMAND_PATTERN.finditer(cleaned_line):
            letter = match.group(1)
            numeric_text = match.group(2)
            recognized_spans.append(match.span())

            if letter in {"N", "O"}:
                continue

            if letter in {"G", "M"}:
                command_words.append(self._normalize_command(letter, numeric_text))
                continue

            if letter not in SUPPORTED_PARAMETERS:
                warning_parts.append(f"第 {line_number} 行：不支持的参数 {letter}{numeric_text}")
                continue

            try:
                parameters[letter] = float(numeric_text)
            except ValueError:
                warning_parts.append(f"第 {line_number} 行：参数 {letter}{numeric_text} 数值无效")

        invalid_tokens = self._unrecognized_tokens(cleaned_line, recognized_spans)
        if invalid_tokens:
            warning_parts.append(f"第 {line_number} 行：无法识别的内容：{' '.join(invalid_tokens)}")

        return command_words, parameters

    def _select_command(self, command_words: list[str], parameters: dict[str, float]) -> str:
        """Select the explicit command or apply modal G0/G1 when appropriate."""
        if command_words:
            return command_words[0]
        if parameters and self._modal_motion_command:
            return self._modal_motion_command
        return "UNKNOWN"

    def _normalize_command(self, letter: str, numeric_text: str) -> str:
        """Normalize G00/M03 style commands to G0/M3."""
        try:
            number = int(float(numeric_text))
        except ValueError:
            return f"{letter}{numeric_text}"
        return f"{letter}{number}"

    def _move_type(self, command: str) -> str:
        """Map normalized command names to UI-friendly movement categories."""
        if command == "G0":
            return "rapid"
        if command == "G1":
            return "linear"
        if command in {"G2", "G3"}:
            return "arc"
        if command in {"M3", "M5", "M6"}:
            return "spindle"
        if command == "M30":
            return "program"
        if command in {"G17", "G18", "G21", "G28", "G30", "G40", "G43", "G54", "G90", "G91", "G94"}:
            return "setting"
        return "unknown"

    def _validate_arc_command(
        self,
        line_number: int,
        parameters: dict[str, float],
        warning_parts: list[str],
    ) -> None:
        """Add non-fatal warnings for incomplete G2/G3 commands."""
        has_radius = "R" in parameters
        has_center_offset = any(axis in parameters for axis in ("I", "J", "K"))
        has_endpoint = any(axis in parameters for axis in ("X", "Y", "Z"))

        if has_radius:
            return
        if not has_center_offset:
            warning_parts.append(
                f"\u7b2c {line_number} \u884c\uff1a\u5706\u5f27\u7f3a\u5c11 I/J/K \u5706\u5fc3\u504f\u79fb\u6216 R \u534a\u5f84\u53c2\u6570"
            )
        if not has_endpoint and not has_center_offset:
            warning_parts.append(f"\u7b2c {line_number} \u884c\uff1a\u5706\u5f27\u7f3a\u5c11\u7ec8\u70b9\u5750\u6807")

    def _strip_comments(self, raw_line: str) -> str:
        """Remove semicolon comments and parenthesized comments from a raw line."""
        without_semicolon = raw_line.split(";", 1)[0]
        return PAREN_COMMENT_PATTERN.sub(" ", without_semicolon)

    def _unrecognized_tokens(
        self,
        cleaned_line: str,
        recognized_spans: list[tuple[int, int]],
    ) -> list[str]:
        """Return text fragments not consumed by the normal G-code word parser."""
        chars = list(cleaned_line)
        for start, end in recognized_spans:
            for index in range(start, end):
                chars[index] = " "
        return [token for token in "".join(chars).split() if token]
