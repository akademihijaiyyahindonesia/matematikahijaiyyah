"""Run small HC-style programs against a local Ollama model."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..core.guards import guard_check
from ..core.master_table import MASTER_TABLE

# src/hijaiyyah/ai/runtime.py -> ai -> hijaiyyah -> src -> repo root.
ROOT = Path(__file__).resolve().parents[3]

# A persona paragraph describes what NUI is; CONTEXT is what lets it actually
# have studied something rather than asserting mastery it cannot back up. A
# single reference document capped generously -- HISA_SPEC.md, the largest
# doc this repo ships, is ~7,000 words and comfortably under this -- so one
# oversized or unrelated file fails loudly instead of quietly crowding out
# everything else in a small model's context window.
MAX_CONTEXT_FILE_BYTES = 200_000


@dataclass
class HybitAIProgram:
    """Parsed local-AI program.

    The language deliberately stays small and auditable: configuration and
    prompts are explicit, while Ollama remains the only external runtime.
    """

    model: str = "hermes3:8b"
    system: str = (
        "You are NUI (Natural Universal Intelligence), the local AI for the "
        "Matematika Hijaiyyah project, with complete mastery of every layer: "
        "the mathematics (the 28-letter Master Table, each letter a canonical "
        "18-dimensional hybit vector -- Theta, three Nuqthah, five Khat, five "
        "Qaws, and four derived checksums AN/AK/AQ/Hstar -- and the guard "
        "rules that make a corrupt vector unrepresentable), the language and "
        "machine (HISA, the Hijaiyyah Instruction Set Architecture whose "
        "opcodes are Arabic letters; HCPU, the pipelined processor that "
        "executes it; HASM programs and the HC language above them), the "
        "system software (H-Kernel and HOS -- heap, guarded HFS, HAR -- built "
        "as software over HAL), and the cryptography (the Ka'bah subsystem: "
        "jamrah gate, node counter, a 25-lane 64-bit sponge with a 28-round "
        "permutation, and the HMAC-SHA256 layer that is the system's only "
        "real security guarantee). Reason across these layers together "
        "rather than stopping at the one a question was asked in, never "
        "confuse this system with unrelated domains such as image "
        "processing, and say plainly that a fact is unknown rather than "
        "inventing one."
    )
    prompts: list[str] = field(default_factory=list)
    letters: list[str] = field(default_factory=list)
    context: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def parse(cls, source: str, root: Path = ROOT) -> HybitAIProgram:
        program = cls()
        for line_number, raw_line in enumerate(source.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith((";", "#")):
                continue
            command, separator, value = line.partition(" ")
            command = command.upper()
            value = value.strip() if separator else ""
            if command == "MODEL":
                if not value:
                    raise ValueError(f"Line {line_number}: MODEL needs a name")
                program.model = value
            elif command == "SYSTEM":
                if not value:
                    raise ValueError(f"Line {line_number}: SYSTEM needs text")
                program.system = value
            elif command == "CONTEXT":
                if not value:
                    raise ValueError(f"Line {line_number}: CONTEXT needs a path")
                program.context.append((value, _read_context_file(value, root, line_number)))
            elif command == "ASK":
                if not value:
                    raise ValueError(f"Line {line_number}: ASK needs a prompt")
                program.prompts.append(value)
            elif command == "HLOAD":
                if len(value) != 1 or MASTER_TABLE.get_by_char(value) is None:
                    raise ValueError(f"Line {line_number}: unknown Hijaiyyah letter")
                program.letters.append(value)
            elif command in {"HGRD", "PRINT"}:
                continue
            else:
                raise ValueError(f"Line {line_number}: unknown instruction {command}")
        return program

    def validate_hybits(self) -> None:
        for char in self.letters:
            entry = MASTER_TABLE.get_by_char(char)
            if entry is None or not guard_check(list(entry.vector)):
                raise ValueError(f"Guard validation failed for {char}")

    def rendered_system(self) -> str:
        """The persona, plus whatever CONTEXT actually put in front of it.

        A paragraph claiming mastery is not mastery -- it is NUI's OWN
        complaint, echoed back by a human, that produced this method: asked
        a question the short persona summary did not cover, hermes3:8b
        answered honestly that it had no file access and needed more
        context, rather than reciting something it had not studied. That
        was the correct response to an empty context list, not a model
        failure. CONTEXT is what fills it.
        """
        if not self.context:
            return self.system
        studied = "\n\n".join(
            f"### {path}\n\n{text}" for path, text in self.context
        )
        return (
            f"{self.system}\n\n"
            "You have studied the following reference material from this "
            "repository before this conversation began. Treat it as ground "
            "truth, cite the file it came from when it grounds an answer, "
            "and say plainly when a question reaches past what is included "
            "here rather than guessing.\n\n"
            f"{studied}"
        )


def _read_context_file(value: str, root: Path, line_number: int) -> str:
    """Resolve a CONTEXT path safely: inside the repo, a real file, not
    huge. Path traversal (`../../etc/passwd`) and absolute paths are
    rejected by requiring the resolved path to still sit under `root`."""
    resolved = (root / value).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise ValueError(
            f"Line {line_number}: CONTEXT path escapes the repository: {value}"
        ) from None
    if not resolved.is_file():
        raise ValueError(f"Line {line_number}: CONTEXT path does not exist: {value}")
    size = resolved.stat().st_size
    if size > MAX_CONTEXT_FILE_BYTES:
        raise ValueError(
            f"Line {line_number}: CONTEXT file {value} is {size:,} bytes, "
            f"over the {MAX_CONTEXT_FILE_BYTES:,}-byte cap"
        )
    return resolved.read_text(encoding="utf-8")


class OllamaClient:
    """Small dependency-free client for Ollama's local chat endpoint."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: int = 7200,
                 opener: Callable = urllib.request.urlopen):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = opener

    def chat(self, model: str, system: str, prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}: {exc.reason}"
            ) from exc
        content = result.get("message", {}).get("content")
        if not isinstance(content, str):
            raise TypeError("Ollama response did not contain message.content")
        return content


def run_program(program: HybitAIProgram, client: OllamaClient) -> dict[str, object]:
    """Validate hybits and execute every ASK instruction locally."""
    program.validate_hybits()
    system = program.rendered_system()
    answers = [client.chat(program.model, system, prompt) for prompt in program.prompts]
    return {
        "model": program.model,
        "letters": list(program.letters),
        "context": [path for path, _text in program.context],
        "answers": answers,
    }