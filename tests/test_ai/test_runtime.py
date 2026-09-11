import json
from pathlib import Path

import pytest

from hijaiyyah.ai.runtime import HybitAIProgram, OllamaClient, run_program

ROOT = Path(__file__).resolve().parents[2]


def test_parse_and_validate_hcai_program():
    program = HybitAIProgram.parse("MODEL hermes3:8b\nHLOAD ا\nHGRD\nASK hello")
    program.validate_hybits()
    assert program.model == "hermes3:8b"
    assert program.letters == ["ا"]
    assert program.prompts == ["hello"]


def test_parse_rejects_unknown_instruction():
    with pytest.raises(ValueError, match="unknown instruction"):
        HybitAIProgram.parse("MAGIC no")


def test_parse_rejects_unknown_letter():
    with pytest.raises(ValueError, match="unknown Hijaiyyah letter"):
        HybitAIProgram.parse("HLOAD x")


def test_ollama_client_posts_local_chat_request():
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"message": {"content": "ok"}}).encode()

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["body"] = json.loads(request.data)
        seen["timeout"] = timeout
        return Response()

    answer = OllamaClient(opener=opener).chat("hermes3:8b", "system", "hello")
    assert answer == "ok"
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["body"]["model"] == "hermes3:8b"
    assert seen["body"]["stream"] is False


def test_run_program_returns_local_answers():
    class FakeClient:
        def chat(self, model, system, prompt):
            return f"{model}: {prompt}"

    program = HybitAIProgram.parse("HLOAD ا\nASK hello")
    result = run_program(program, FakeClient())
    assert result["answers"] == ["hermes3:8b: hello"]


def test_default_persona_is_nui_and_names_every_layer():
    """The persona both local models run under, unless a program overrides
    it -- mastery has to name all four layers, not just the mathematics the
    original default was scoped to."""
    system = HybitAIProgram().system
    assert "NUI" in system and "Natural Universal Intelligence" in system
    for layer in ("Master Table", "HISA", "HCPU", "H-Kernel", "HOS", "Ka'bah",
                  "HMAC-SHA256"):
        assert layer in system, f"NUI's persona stopped naming {layer}"


@pytest.mark.parametrize("example,model,contexts", [
    ("local_ai.hcai", "hermes3:8b",
     ["Hybit/Bab_III_Hybit_Paradigma_Komputasi_Ketiga.md"]),
    ("qwen_local_ai.hcai", "qwen3-coder:30b",
     ["cosmictera-build/ON.md", "rtl/programs/hos.hasm"]),
])
def test_example_programs_carry_the_same_nui_persona(example, model, contexts):
    """Both example programs spell the persona out in their own SYSTEM line
    rather than relying on the code default (the program format's own
    auditability point) -- so it is the code default that must not drift
    from what they say, not the other way around. Each also loads real
    CONTEXT: a persona claiming mastery with an empty context list is the
    exact complaint that made CONTEXT exist -- hermes3:8b, asked about Hybit
    with nothing to study, answered honestly that it had no file access."""
    source = (ROOT / "examples" / example).read_text(encoding="utf-8")
    program = HybitAIProgram.parse(source)
    assert program.model == model
    assert program.system == HybitAIProgram().system
    assert program.prompts, f"{example} must still ask something"
    assert [path for path, _text in program.context] == contexts
    for _path, text in program.context:
        assert len(text) > 500, "a CONTEXT file loaded almost nothing"


def test_context_is_empty_by_default_and_leaves_system_untouched():
    program = HybitAIProgram.parse("HLOAD ا\nASK hello")
    assert program.context == []
    assert program.rendered_system() == program.system


def test_context_appends_ground_truth_the_model_can_cite(tmp_path):
    doc = tmp_path / "note.md"
    doc.write_text("Hybit v18 has fourteen independent components.", encoding="utf-8")
    program = HybitAIProgram.parse(
        f"CONTEXT {doc.name}\nHLOAD ا\nASK hello", root=tmp_path
    )
    assert program.context == [
        (doc.name, "Hybit v18 has fourteen independent components.")
    ]
    rendered = program.rendered_system()
    assert rendered.startswith(program.system)
    assert doc.name in rendered
    assert "fourteen independent components" in rendered
    assert "studied the following reference material" in rendered


def test_context_rejects_a_path_that_escapes_the_repository(tmp_path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("not part of this repo", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes the repository"):
        HybitAIProgram.parse(
            f"CONTEXT ../{outside.name}\nASK hello", root=tmp_path
        )


def test_context_rejects_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        HybitAIProgram.parse("CONTEXT nope.md\nASK hello", root=tmp_path)


def test_context_rejects_an_oversized_file(tmp_path, monkeypatch):
    import hijaiyyah.ai.runtime as runtime

    monkeypatch.setattr(runtime, "MAX_CONTEXT_FILE_BYTES", 10)
    big = tmp_path / "big.md"
    big.write_text("x" * 50, encoding="utf-8")
    with pytest.raises(ValueError, match="over the 10-byte cap"):
        HybitAIProgram.parse(f"CONTEXT {big.name}\nASK hello", root=tmp_path)


def test_context_needs_a_path():
    with pytest.raises(ValueError, match="CONTEXT needs a path"):
        HybitAIProgram.parse("CONTEXT\nASK hello")