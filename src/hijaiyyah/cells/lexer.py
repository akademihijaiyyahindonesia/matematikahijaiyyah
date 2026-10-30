"""Phase 3.1 — Unicode-Aware Lexer for Native Hijaiyyah Cells (.hcell).

Enforces Option 2:
- Recognizes the 28 canonical Hijaiyyah letters (including two-codepoint 'هـ'),
  Hijaiyyah cell identifiers, Arabic-Indic and ASCII numerals, and approved
  Matematika Hijaiyyah mathematical & system symbols (Θ̂/Θ, U, ρ, Θ₄, Δ, ‖·‖²,
  d₂², ⟨·,·⟩, N, K, Q, A, H*, Φ, §, ⏣, ⛁, ⊢, ↦, :=, =, +, -, *, ==, !=, <=, >=,
  <, >, ?, :, {, }, ↻, ƒ, ⇐, [, ], (, ), ,, ;).
- Rejects Latin programming keywords/identifiers (let, fn, println, if, while, etc.),
  Arabic Presentation Forms, and lookalike glyphs without silent substitution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from hijaiyyah.cells.dataset_engine import (
    H28_SINGLE_CHARS,
    HAA_FIRST,
    HAA_SECOND,
    HAA_SEQUENCE,
    validate_and_normalize_hijaiyyah_text,
)
from hijaiyyah.core.exceptions import HijaiyyahError

ARABIC_INDIC_DIGITS: dict[str, str] = {
    "٠": "0",
    "١": "1",
    "٢": "2",
    "٣": "3",
    "٤": "4",
    "٥": "5",
    "٦": "6",
    "٧": "7",
    "٨": "8",
    "٩": "9",
}

APPROVED_MATH_LATIN_OPERATORS: frozenset[str] = frozenset({"U", "N", "K", "Q", "A"})


class HCellLexerError(HijaiyyahError):
    """Raised when the .hcell lexer encounters an invalid character or forbidden Latin token."""

    def __init__(self, message: str, line: int, col: int) -> None:
        self.line = line
        self.col = col
        super().__init__(f"L{line}:{col}: {message}")


class HCellTokenType(Enum):
    """Token types for the native .hcell language (HCELL-v0.1-exp)."""

    HIJAIYYAH_LETTER = auto()  # Single canonical letter: ب, س, م, هـ
    WORD_LITERAL = auto()      # ⟪ب س م⟫ or «ب س م»
    CELL_ID = auto()           # ⟦...⟧, @..., or multi-letter Hijaiyyah cell identifier
    INTEGER = auto()           # 42 or ٤٢

    # Approved Mathematical & System Operators (Bab I–III)
    OP_THETA = auto()          # Θ̂ or Θ
    OP_U = auto()              # U
    OP_RHO = auto()            # ρ
    OP_THETA4 = auto()         # Θ₄
    OP_DELTA = auto()          # Δ
    OP_DIST2 = auto()          # d₂²
    OP_N = auto()              # N
    OP_K = auto()              # K
    OP_Q = auto()              # Q
    OP_A = auto()              # A
    OP_HSTAR = auto()          # H*
    OP_PHI = auto()            # Φ
    OP_HAR_LOOKUP = auto()     # § (dynamic/static Master Table / HAR entry lookup)
    OP_SYSCALL = auto()        # ⏣ (official HOS syscall invocation)
    OP_HFS_READ_HYBIT = auto() # ⛁ (official HFS_READ hybit via SYSCALL 7)

    # Statement & Relational Symbols
    GUARD_TURNSTILE = auto()   # ⊢ (guard assertion)
    EMIT_ARROW = auto()        # ↦ (output emission)
    ASSIGN = auto()            # := or =
    QUESTION = auto()          # ? (conditional branch)
    COLON = auto()             # : (else branch)
    LOOP_CYCLE = auto()        # ↻ (bounded loop)
    FN_HOOK = auto()           # ƒ (subroutine cell definition)
    RETURN_ARROW = auto()      # ⇐ (subroutine return)

    # Comparison Operators
    EQ = auto()                # ==
    NE = auto()                # != or ≠
    LE = auto()                # <= or ≤
    GE = auto()                # >= or ≥
    LT = auto()                # <
    GT = auto()                # >

    # Arithmetic & Norm / Inner-product Delimiters
    PLUS = auto()              # +
    MINUS = auto()             # -
    STAR = auto()              # *
    NORM_BAR = auto()          # ‖
    SUP_TWO = auto()           # ²
    LANGLE = auto()            # ⟨
    RANGLE = auto()            # ⟩

    # Punctuation
    LPAREN = auto()            # (
    RPAREN = auto()            # )
    LBRACE = auto()            # {
    RBRACE = auto()            # }
    LBRACKET = auto()          # [
    RBRACKET = auto()          # ]
    COMMA = auto()             # , or ،
    SEMICOLON = auto()         # ; or ؛
    NEWLINE = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class HCellToken:
    """Immutable token with 1-based line and column provenance."""

    type: HCellTokenType
    value: str
    line: int
    col: int


class HCellLexer:
    """Unicode-aware lexer for native `.hcell` programs."""

    def __init__(self, source: str) -> None:
        self._src = validate_and_normalize_hijaiyyah_text(source)
        self._pos = 0
        self._line = 1
        self._col = 1
        self._tokens: list[HCellToken] = []

    def tokenize(self) -> list[HCellToken]:
        self._tokens = []
        self._pos = 0
        self._line = 1
        self._col = 1

        while self._pos < len(self._src):
            ch = self._src[self._pos]

            if ch in " \t\r":
                self._advance()
                continue

            if ch == "\n":
                self._emit(HCellTokenType.NEWLINE, "\n")
                self._pos += 1
                self._line += 1
                self._col = 1
                continue

            # Comments: # ... or // ...
            if ch == "#" or (ch == "/" and self._peek(1) == "/"):
                while self._pos < len(self._src) and self._src[self._pos] != "\n":
                    self._advance()
                continue

            rem = self._src[self._pos:]
            if rem.startswith(":="):
                self._emit(HCellTokenType.ASSIGN, ":=")
                self._advance(2)
                continue
            if rem.startswith("=="):
                self._emit(HCellTokenType.EQ, "==")
                self._advance(2)
                continue
            if rem.startswith("!="):
                self._emit(HCellTokenType.NE, "!=")
                self._advance(2)
                continue
            if rem.startswith("<="):
                self._emit(HCellTokenType.LE, "<=")
                self._advance(2)
                continue
            if rem.startswith(">="):
                self._emit(HCellTokenType.GE, ">=")
                self._advance(2)
                continue
            if rem.startswith("Θ̂") or rem.startswith("Θ\u0302"):
                self._emit(HCellTokenType.OP_THETA, "Θ̂")
                self._advance(2)
                continue
            if rem.startswith("Θ₄"):
                self._emit(HCellTokenType.OP_THETA4, "Θ₄")
                self._advance(2)
                continue
            if rem.startswith("d₂²"):
                self._emit(HCellTokenType.OP_DIST2, "d₂²")
                self._advance(3)
                continue
            if rem.startswith("H*"):
                self._emit(HCellTokenType.OP_HSTAR, "H*")
                self._advance(2)
                continue

            if ch in ("⟪", "«"):
                close = "⟫" if ch == "⟪" else "»"
                self._read_word_literal(close)
                continue

            if ch == "⟦":
                self._read_bracketed_cell_id()
                continue

            if ch == "@":
                self._read_at_cell_id()
                continue

            single_map = {
                "Θ": HCellTokenType.OP_THETA,
                "ρ": HCellTokenType.OP_RHO,
                "Δ": HCellTokenType.OP_DELTA,
                "Φ": HCellTokenType.OP_PHI,
                "§": HCellTokenType.OP_HAR_LOOKUP,
                "⏣": HCellTokenType.OP_SYSCALL,
                "⛁": HCellTokenType.OP_HFS_READ_HYBIT,
                "⊢": HCellTokenType.GUARD_TURNSTILE,
                "↦": HCellTokenType.EMIT_ARROW,
                "↻": HCellTokenType.LOOP_CYCLE,
                "ƒ": HCellTokenType.FN_HOOK,
                "⇐": HCellTokenType.RETURN_ARROW,
                "?": HCellTokenType.QUESTION,
                ":": HCellTokenType.COLON,
                "=": HCellTokenType.ASSIGN,
                "≠": HCellTokenType.NE,
                "≤": HCellTokenType.LE,
                "≥": HCellTokenType.GE,
                "<": HCellTokenType.LT,
                ">": HCellTokenType.GT,
                "+": HCellTokenType.PLUS,
                "-": HCellTokenType.MINUS,
                "*": HCellTokenType.STAR,
                "‖": HCellTokenType.NORM_BAR,
                "²": HCellTokenType.SUP_TWO,
                "⟨": HCellTokenType.LANGLE,
                "⟩": HCellTokenType.RANGLE,
                "(": HCellTokenType.LPAREN,
                ")": HCellTokenType.RPAREN,
                "{": HCellTokenType.LBRACE,
                "}": HCellTokenType.RBRACE,
                "[": HCellTokenType.LBRACKET,
                "]": HCellTokenType.RBRACKET,
                ",": HCellTokenType.COMMA,
                "،": HCellTokenType.COMMA,
                ";": HCellTokenType.SEMICOLON,
                "؛": HCellTokenType.SEMICOLON,
            }
            if ch in single_map:
                self._emit(single_map[ch], ch)
                self._advance()
                continue

            if ch.isdigit() or ch in ARABIC_INDIC_DIGITS:
                self._read_integer()
                continue

            if self._is_hijaiyyah_char_at(self._pos):
                self._read_hijaiyyah_token()
                continue

            if ch.isalpha() and ch.isascii():
                self._read_ascii_math_or_reject()
                continue

            raise HCellLexerError(
                f"Unrecognized symbol {ch!r} (U+{ord(ch):04X}) in .hcell source",
                self._line,
                self._col,
            )

        self._emit(HCellTokenType.EOF, "")
        return self._tokens

    def _advance(self, count: int = 1) -> None:
        self._pos += count
        self._col += count

    def _peek(self, offset: int = 0) -> str | None:
        idx = self._pos + offset
        return self._src[idx] if idx < len(self._src) else None

    def _emit(self, ttype: HCellTokenType, value: str) -> None:
        self._tokens.append(HCellToken(ttype, value, self._line, self._col))

    def _is_hijaiyyah_char_at(self, idx: int) -> bool:
        if idx >= len(self._src):
            return False
        ch = self._src[idx]
        return ch in H28_SINGLE_CHARS or ch == HAA_FIRST

    def _consume_one_hijaiyyah_letter(self) -> str:
        ch = self._src[self._pos]
        if ch == HAA_FIRST:
            if self._peek(1) == HAA_SECOND:
                self._advance(2)
            else:
                self._advance(1)
            return HAA_SEQUENCE
        self._advance(1)
        return ch

    def _read_word_literal(self, close_delim: str) -> None:
        start_line, start_col = self._line, self._col
        self._advance(1)
        letters: list[str] = []
        while self._pos < len(self._src) and self._src[self._pos] != close_delim:
            ch = self._src[self._pos]
            if ch in " \t":
                self._advance(1)
                continue
            if self._is_hijaiyyah_char_at(self._pos):
                letters.append(self._consume_one_hijaiyyah_letter())
                continue
            raise HCellLexerError(
                f"Invalid character {ch!r} inside Hijaiyyah word literal",
                self._line,
                self._col,
            )
        if self._pos >= len(self._src):
            raise HCellLexerError(
                f"Unterminated word literal (expected {close_delim!r})",
                start_line,
                start_col,
            )
        self._advance(1)
        if not letters:
            raise HCellLexerError(
                "Empty Hijaiyyah word literal is not allowed",
                start_line,
                start_col,
            )
        self._tokens.append(
            HCellToken(HCellTokenType.WORD_LITERAL, " ".join(letters), start_line, start_col)
        )

    def _read_bracketed_cell_id(self) -> None:
        start_line, start_col = self._line, self._col
        self._advance(1)
        parts: list[str] = []
        while self._pos < len(self._src) and self._src[self._pos] != "⟧":
            ch = self._src[self._pos]
            if self._is_hijaiyyah_char_at(self._pos):
                parts.append(self._consume_one_hijaiyyah_letter())
            elif ch == "_" or ch.isdigit() or ch in ARABIC_INDIC_DIGITS:
                parts.append(ARABIC_INDIC_DIGITS.get(ch, ch))
                self._advance(1)
            else:
                raise HCellLexerError(
                    f"Invalid character {ch!r} inside cell identifier ⟦...⟧; "
                    "only Hijaiyyah letters, '_', and digits are permitted",
                    self._line,
                    self._col,
                )
        if self._pos >= len(self._src):
            raise HCellLexerError("Unterminated cell identifier ⟦...⟧", start_line, start_col)
        self._advance(1)
        name = "".join(parts)
        if not name:
            raise HCellLexerError("Empty cell identifier ⟦⟧", start_line, start_col)
        self._tokens.append(HCellToken(HCellTokenType.CELL_ID, name, start_line, start_col))

    def _read_at_cell_id(self) -> None:
        start_line, start_col = self._line, self._col
        self._advance(1)
        parts: list[str] = []
        while self._pos < len(self._src):
            ch = self._src[self._pos]
            if self._is_hijaiyyah_char_at(self._pos):
                parts.append(self._consume_one_hijaiyyah_letter())
            elif ch == "_" or ch.isdigit() or ch in ARABIC_INDIC_DIGITS:
                parts.append(ARABIC_INDIC_DIGITS.get(ch, ch))
                self._advance(1)
            else:
                break
        name = "".join(parts)
        if not name:
            raise HCellLexerError("Expected Hijaiyyah cell name after '@'", start_line, start_col)
        self._tokens.append(HCellToken(HCellTokenType.CELL_ID, name, start_line, start_col))

    def _read_hijaiyyah_token(self) -> None:
        start_line, start_col = self._line, self._col
        first = self._consume_one_hijaiyyah_letter()
        parts: list[str] = [first]
        while self._pos < len(self._src):
            ch = self._src[self._pos]
            if self._is_hijaiyyah_char_at(self._pos):
                parts.append(self._consume_one_hijaiyyah_letter())
            elif ch == "_" or ch.isdigit() or ch in ARABIC_INDIC_DIGITS:
                parts.append(ARABIC_INDIC_DIGITS.get(ch, ch))
                self._advance(1)
            else:
                break
        if len(parts) == 1:
            self._tokens.append(
                HCellToken(HCellTokenType.HIJAIYYAH_LETTER, first, start_line, start_col)
            )
        else:
            self._tokens.append(
                HCellToken(HCellTokenType.CELL_ID, "".join(parts), start_line, start_col)
            )

    def _read_integer(self) -> None:
        start_line, start_col = self._line, self._col
        digits: list[str] = []
        while self._pos < len(self._src):
            ch = self._src[self._pos]
            if ch.isdigit():
                digits.append(ch)
                self._advance(1)
            elif ch in ARABIC_INDIC_DIGITS:
                digits.append(ARABIC_INDIC_DIGITS[ch])
                self._advance(1)
            else:
                break
        self._tokens.append(
            HCellToken(HCellTokenType.INTEGER, "".join(digits), start_line, start_col)
        )

    def _read_ascii_math_or_reject(self) -> None:
        start_line, start_col = self._line, self._col
        start_pos = self._pos
        while self._pos < len(self._src) and (
            self._src[self._pos].isalnum() or self._src[self._pos] == "_"
        ):
            self._advance(1)
        word = self._src[start_pos : self._pos]
        op_map = {
            "U": HCellTokenType.OP_U,
            "N": HCellTokenType.OP_N,
            "K": HCellTokenType.OP_K,
            "Q": HCellTokenType.OP_Q,
            "A": HCellTokenType.OP_A,
        }
        if word in op_map and self._pos < len(self._src) and self._src[self._pos] == "(":
            self._tokens.append(HCellToken(op_map[word], word, start_line, start_col))
            return
        raise HCellLexerError(
            f"Latin keyword or identifier {word!r} is forbidden in native .hcell "
            "(Option 2 requires Hijaiyyah letters and mathematical symbols; use .hc for HC v1.0)",
            start_line,
            start_col,
        )


def tokenize_hcell(source: str) -> list[HCellToken]:
    """Tokenize a native `.hcell` source string."""
    return HCellLexer(source).tokenize()


__all__ = [
    "APPROVED_MATH_LATIN_OPERATORS",
    "ARABIC_INDIC_DIGITS",
    "HCellLexer",
    "HCellLexerError",
    "HCellToken",
    "HCellTokenType",
    "tokenize_hcell",
]
