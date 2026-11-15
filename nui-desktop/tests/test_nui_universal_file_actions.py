"""Acceptance Test Suite for CosmicTera NUI Universal File & Folder Action Intelligence.

Explicitly separated into 4 test tiers as mandated by Section 9:
- TIER A: UNIT TESTS (Format parsers, builders, unsupported format detection, resource registry schema)
- TIER B: MOCK TESTS (VPS transfer gate with Mock/Deterministic SSH transport, non-path attachment references)
- TIER C: INTEGRATION TESTS (9-stage chat orchestration workflow, multi-attachment turns, multi-turn session resource memory, ambiguity clarification, API `/api/resources/op`)
- TIER D: LIVE FILESYSTEM TESTS (Real directories, nested traversal, cross-file search, document comparison, copy-on-edit attachment preservation, READ_ONLY vs READ_WRITE enforcement, boundary denial)

Covers all 18 mandatory acceptance scenarios:
1. Reading PDF attachment (`test_01_unit_read_pdf_attachment`)
2. Reading DOCX (`test_02_unit_read_docx`)
3. Processing XLSX (`test_03_unit_process_xlsx`)
4. Reading PPTX (`test_04_unit_read_pptx`)
5. Reading source code (`test_05_unit_read_source_code_and_unsupported_format`)
6. Processing uploaded ZIP as archive & safe staged folder (`test_06_live_fs_process_uploaded_zip_to_staging`)
7. Traversing nested directories (`test_07_live_fs_traverse_nested_directories`)
8. Searching content across files (`test_08_live_fs_search_content_across_files`)
9. Comparing documents (`test_09_live_fs_compare_documents`)
10. Creating verified output file (`test_10_live_fs_create_output_file_and_pdf_merge`)
11. Ensuring original attachment file is NEVER overwritten (`test_11_live_fs_preserve_original_attachment_on_edit`)
12. Denying access to folders outside permissions (`test_12_live_fs_deny_folder_outside_permissions`)
13. Respecting `READ_ONLY` folder mode (`test_13_live_fs_respect_read_only_folder`)
14. Using `READ_WRITE` folder mode as authorized (`test_14_live_fs_use_read_write_folder`)
15. Producing output accessible via chat with `Copy`, `Open`, `Reveal in Finder` (`test_15_integration_chat_output_accessible_with_ui_actions`)
16. Processing multiple attachments in a single job (`test_16_integration_process_multiple_attachments_in_one_job`)
17. Retaining resource context across follow-up turns (`test_17_integration_retain_resource_context_on_followup`)
18. Transferring to VPS ONLY after remote connection & host fingerprint are verified (`test_18_mock_vps_transfer_only_after_verified_connection`)
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
import zipfile

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.remote_dev_engine import RemoteVPSDevelopmentEngine, VPSConnectionProfile
from backend.server import NUILocalServiceApp
from backend.universal_file_intelligence import (
    ACTION_WORKFLOW_STAGES,
    RESOURCE_SOURCE_TYPES,
    AttachmentResolver,
    DocumentProcessingEngine,
    FileOperationEngine,
    FolderResourceManager,
    OutputManager,
    RemoteFileAdapter,
    UniversalDocumentIntelligence,
    UniversalFileActionEngine,
)

SWIFT_SOURCE = REPO_ROOT / "nui-desktop" / "macos" / "Sources" / "CosmicTeraNUIApp.swift"


class MockVPSVerificationTransport:
    """Mock SSH/SFTP transport for testing Section 6 & Test 18 VPS connection gate."""

    def __init__(self) -> None:
        self.known_fingerprint = "SHA256:CosmicTeraVerifiedVPSHostKey2026"
        self.uploaded_files: dict[str, str] = {}

    def verify_host_fingerprint(
        self, host: str, port: int, expected_fingerprint: str, timeout: float = 5.0
    ) -> dict[str, Any]:
        matched = expected_fingerprint.strip() == self.known_fingerprint
        return {
            "ok": matched,
            "verified": matched,
            "status": "HOST_KEY_VERIFIED" if matched else "HOST_KEY_VERIFICATION_FAILED",
            "expected_fingerprint": expected_fingerprint,
            "scanned_fingerprints": [f"256 {self.known_fingerprint} {host} (ED25519)"],
            "reason": "Host key matched." if matched else "Host fingerprint mismatch",
        }

    def run_ssh_command(
        self,
        profile: VPSConnectionProfile,
        command: str,
        *,
        timeout: float = 10.0,
        keychain_secret: str | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "exit_code": 0,
            "stdout": "Linux 6.8.0-45-generic x86_64\n/usr/bin/python3\n",
            "stderr": "",
            "timed_out": False,
        }

    def sftp_read_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        content = self.uploaded_files.get(remote_path, "")
        return {
            "ok": bool(content),
            "remote_path": remote_path,
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
            "timed_out": False,
        }

    def sftp_write_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        content: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        self.uploaded_files[remote_path] = content
        return {
            "ok": True,
            "remote_path": remote_path,
            "bytes_written": len(content.encode("utf-8")),
            "exit_code": 0,
            "stderr": "",
            "timed_out": False,
        }


@pytest.fixture()
def universal_env(tmp_path: Path) -> dict[str, Any]:
    app = NUILocalServiceApp(
        db_path=tmp_path / "universal_actions.db", use_os_keychain=False
    )
    mock_ssh = MockVPSVerificationTransport()
    remote_engine = RemoteVPSDevelopmentEngine(
        storage=app.storage,
        permissions=app.permissions,
        transport=mock_ssh,
    )
    ufe = UniversalFileActionEngine(
        storage=app.storage,
        permissions=app.permissions,
        remote_dev_engine=remote_engine,
        staging_root=tmp_path / "universal_staging",
    )
    app.remote_dev_engine = remote_engine
    app.universal_file_engine = ufe
    app.native_provider.remote_dev_engine = remote_engine
    app.native_provider.universal_file_engine = ufe
    app.ollama_provider.remote_dev_engine = remote_engine
    app.ollama_provider.universal_file_engine = ufe
    app.orchestrator.remote_dev_engine = remote_engine
    app.orchestrator.universal_file_engine = ufe
    return {
        "app": app,
        "ufe": ufe,
        "remote_engine": remote_engine,
        "mock_ssh": mock_ssh,
        "tmp_path": tmp_path,
    }


# ===========================================================================
# TIER A: UNIT TESTS (Scenarios 1, 2, 3, 4, 5)
# ===========================================================================


@pytest.mark.unit
def test_01_unit_read_pdf_attachment(universal_env: dict[str, Any], tmp_path: Path):
    """Scenario 1 (UNIT): Generate and read a multi-line PDF attachment and verify extracted text & metadata."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    pdf_path = tmp_path / "sample_hijaiyyah_report.pdf"
    UniversalDocumentIntelligence.write_simple_pdf(
        pdf_path,
        title="Laporan Matematika Hijaiyyah",
        lines=[
            "Dokumen ini membahas sistem bilangan Hybit 18D dan norma ||BSM||^2 = 112.",
            "Arsitektur HCPU mengeksekusi instruksi H-ISA secara deterministik.",
        ],
    )
    # Register via non-path attachment reference with raw_bytes to prove non-path attachment handling
    att_res = ufe.attach_and_register(
        name="sample_hijaiyyah_report.pdf",
        path_or_reference="attachment://chat-msg-01/sample_hijaiyyah_report.pdf",
        raw_bytes=pdf_path.read_bytes(),
        session_id="sess-pdf-01",
    )
    assert att_res["ok"] is True
    rec = att_res["resource"]
    assert rec["source_type"] == "CHAT_ATTACHMENT"
    assert rec["canonical_path_or_reference"] == "attachment://chat-msg-01/sample_hijaiyyah_report.pdf"
    assert rec["staged_local_path"] is not None

    extracted = ufe.doc_intelligence.inspect_and_extract(Path(rec["staged_local_path"]))
    assert extracted["ok"] is True
    assert extracted["format"] == "PDF"
    assert extracted["page_count"] >= 1
    assert "Laporan Matematika Hijaiyyah" in extracted["text"]
    assert "Hybit 18D" in extracted["text"]


@pytest.mark.unit
def test_02_unit_read_docx(universal_env: dict[str, Any], tmp_path: Path):
    """Scenario 2 (UNIT): Read a `.docx` document including paragraphs and tables."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    docx_path = tmp_path / "dokumen_yayasan.docx"
    UniversalDocumentIntelligence.write_simple_docx(
        docx_path,
        paragraphs=[
            "Proposal Kurikulum Matematika Hijaiyyah",
            "Bab 1: Vektor 18 Dimensi dan Penjagaan Six-Guard.",
        ],
        table_rows=[
            ["Huruf", "Opcode", "Peran"],
            ["Ba", "0xE1", "Titik Bawah"],
            ["Jim", "0xE4", "Sudut Inti"],
        ],
    )
    extracted = ufe.doc_intelligence.inspect_and_extract(docx_path)
    assert extracted["ok"] is True
    assert extracted["format"] == "DOCX"
    assert extracted["paragraph_count"] >= 2
    assert extracted["table_count"] == 1
    assert "Proposal Kurikulum Matematika Hijaiyyah" in extracted["text"]
    assert extracted["tables"][0][1][0] == "Ba"


@pytest.mark.unit
def test_03_unit_process_xlsx(universal_env: dict[str, Any], tmp_path: Path):
    """Scenario 3 (UNIT): Read and aggregate numeric metrics from an `.xlsx` workbook."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    xlsx_path = tmp_path / "data_komputasi.xlsx"
    UniversalDocumentIntelligence.write_simple_xlsx(
        xlsx_path,
        sheet_name="Benchmarks",
        rows=[
            ["Modul", "Siklus", "Energi_mJ"],
            ["HLOAD", 4, 1.5],
            ["HCADD", 6, 2.5],
            ["HNRM2", 8, 5.0],
        ],
    )
    extracted = ufe.doc_intelligence.inspect_and_extract(xlsx_path)
    assert extracted["ok"] is True
    assert extracted["format"] == "XLSX"
    assert "Benchmarks" in extracted["sheet_names"]
    assert extracted["total_rows"] == 4
    assert extracted["numeric_summary"]["Siklus"]["sum"] == 18.0
    assert extracted["numeric_summary"]["Energi_mJ"]["sum"] == 9.0


@pytest.mark.unit
def test_04_unit_read_pptx(universal_env: dict[str, Any], tmp_path: Path):
    """Scenario 4 (UNIT): Read slides, titles, and bullet points from a `.pptx` presentation."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    pptx_path = tmp_path / "presentasi_cosmictera.pptx"
    UniversalDocumentIntelligence.write_simple_pptx(
        pptx_path,
        slides=[
            ("Arsitektur CosmicTera", ["Lapisan L0 hingga L11", "Prosesor Silikon HCPU"]),
            ("Implementasi Tang Nano 20K", ["Clock 27 MHz", "Visualisasi HDMI Real-Time"]),
        ],
    )
    extracted = ufe.doc_intelligence.inspect_and_extract(pptx_path)
    assert extracted["ok"] is True
    assert extracted["format"] == "PPTX"
    assert extracted["slide_count"] == 2
    assert extracted["slides"][0]["title"] == "Arsitektur CosmicTera"
    assert "Visualisasi HDMI Real-Time" in extracted["text"]


@pytest.mark.unit
def test_05_unit_read_source_code_and_unsupported_format(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 5 (UNIT): Parse source code (`.py`, `.swift`, `.v`, `.hasm`) and verify clean reporting for unsupported formats."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    py_file = tmp_path / "hybit_calc.py"
    py_file.write_text(
        "class HybitEngine:\n    def compute_bsm(self) -> int:\n        return 112\n",
        encoding="utf-8",
    )
    ext_py = ufe.doc_intelligence.inspect_and_extract(py_file)
    assert ext_py["ok"] is True
    assert ext_py["format"] == "PYTHON"
    assert "compute_bsm" in ext_py["functions_or_ops"]
    assert "HybitEngine" in ext_py["classes_or_modules"]

    hasm_file = tmp_path / "prog.hasm"
    hasm_file.write_text("HLOAD H1, 2\nHCADD H4, H1, H1\nPRINT R1\nHALT\n", encoding="utf-8")
    ext_hasm = ufe.doc_intelligence.inspect_and_extract(hasm_file)
    assert ext_hasm["ok"] is True
    assert ext_hasm["format"] == "HASM"
    assert "HLOAD" in ext_hasm["functions_or_ops"]

    # Unsupported format check
    bad_file = tmp_path / "installer.dmg"
    bad_file.write_bytes(b"\x00\x01\x02\x03")
    ext_bad = ufe.doc_intelligence.inspect_and_extract(bad_file)
    assert ext_bad["ok"] is False
    assert ext_bad["status"] == "UNSUPPORTED_FORMAT"

    # Verify all 8 resource source types and 7 unified adapter classes exist
    assert len(RESOURCE_SOURCE_TYPES) == 8
    assert AttachmentResolver is not None
    assert FolderResourceManager is not None
    assert FileOperationEngine is not None
    assert DocumentProcessingEngine is not None
    assert OutputManager is not None
    assert RemoteFileAdapter is not None


# ===========================================================================
# TIER D: LIVE FILESYSTEM TESTS (Scenarios 6, 7, 8, 9, 10, 11, 12, 13, 14)
# ===========================================================================


@pytest.mark.live_fs
def test_06_live_fs_process_uploaded_zip_to_staging(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 6 (LIVE FILESYSTEM): Upload a `.zip` folder archive, verify safe extraction to staging, and register as `UPLOADED_FOLDER`."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    zip_path = tmp_path / "paket_riset.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("catatan/ringkasan.md", "# Ringkasan Matematika Hijaiyyah\nIsi terverifikasi.")
        zf.writestr("kode/main.py", "def run():\n    return 'OK'\n")

    att_res = ufe.attach_and_register(
        name="paket_riset.zip",
        path_or_reference=str(zip_path),
        source_type="CHAT_ATTACHMENT",
        session_id="sess-zip-06",
    )
    assert att_res["ok"] is True
    uf_id = att_res["extracted_folder_resource_id"]
    assert uf_id is not None

    uf_rec = ufe.registry.get_resource(uf_id)
    assert uf_rec is not None
    assert uf_rec.source_type == "UPLOADED_FOLDER"
    assert Path(uf_rec.canonical_path_or_reference).is_dir()

    trav = ufe.list_and_traverse_directory(uf_rec, recursive=True)
    assert trav["ok"] is True
    assert trav["file_count"] == 2


@pytest.mark.live_fs
def test_07_live_fs_traverse_nested_directories(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 7 (LIVE FILESYSTEM): Traverse nested subdirectories inside an authorized Connected Folder."""
    app: NUILocalServiceApp = universal_env["app"]
    ufe: UniversalFileActionEngine = universal_env["ufe"]

    nested_root = tmp_path / "proyek_bertingkat"
    (nested_root / "bab1" / "sub_a").mkdir(parents=True)
    (nested_root / "bab2" / "sub_b").mkdir(parents=True)
    (nested_root / "bab1" / "sub_a" / "teori.md").write_text("# Teori L0\n", encoding="utf-8")
    (nested_root / "bab2" / "sub_b" / "bukti.py").write_text("x = 112\n", encoding="utf-8")

    app.storage.add_authorized_folder(
        nested_root, label="proyek_bertingkat", access_mode="READ_WRITE"
    )
    ufe.registry.sync_system_resources()

    trav = ufe.list_and_traverse_directory(nested_root, recursive=True)
    assert trav["ok"] is True
    assert trav["file_count"] == 2
    assert trav["directory_count"] >= 4
    rel_paths = {f["relative_path"] for f in trav["files"]}
    assert "bab1/sub_a/teori.md" in rel_paths
    assert "bab2/sub_b/bukti.py" in rel_paths


@pytest.mark.live_fs
def test_08_live_fs_search_content_across_files(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 8 (LIVE FILESYSTEM): Search content across multiple file types (MD, DOCX, TXT) in a folder."""
    app: NUILocalServiceApp = universal_env["app"]
    ufe: UniversalFileActionEngine = universal_env["ufe"]

    search_dir = tmp_path / "koleksi_dokumen"
    search_dir.mkdir()
    (search_dir / "catatan_umum.txt").write_text("Catatan administrasi harian.", encoding="utf-8")
    (search_dir / "riset_hijaiyyah.md").write_text(
        "# Riset Matematika Hijaiyyah\nMembahas vektor Hybit 18D dan norma BSM.",
        encoding="utf-8",
    )
    UniversalDocumentIntelligence.write_simple_docx(
        search_dir / "kurikulum_hijaiyyah.docx",
        paragraphs=["Modul pembelajaran Matematika Hijaiyyah tingkat lanjut."],
    )
    app.storage.add_authorized_folder(
        search_dir, label="koleksi_dokumen", access_mode="READ_ONLY"
    )

    srch = ufe.search_across_files("Matematika Hijaiyyah", [search_dir])
    assert srch["ok"] is True
    assert srch["match_count"] == 2
    matched_names = {m["name"] for m in srch["matches"]}
    assert "riset_hijaiyyah.md" in matched_names
    assert "kurikulum_hijaiyyah.docx" in matched_names
    assert "catatan_umum.txt" not in matched_names


@pytest.mark.live_fs
def test_09_live_fs_compare_documents(universal_env: dict[str, Any], tmp_path: Path):
    """Scenario 9 (LIVE FILESYSTEM): Compare two document versions and extract unified diff & similarity."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    v1 = tmp_path / "spesifikasi_v1.md"
    v2 = tmp_path / "spesifikasi_v2.md"
    v1.write_text("# Spesifikasi HCPU\nClock: 27 MHz\nStages: 5\n", encoding="utf-8")
    v2.write_text("# Spesifikasi HCPU\nClock: 27 MHz\nStages: 5\nHDMI: 640x480 @ 60Hz\n", encoding="utf-8")

    cmp_res = ufe.doc_intelligence.compare_documents(v1, v2)
    assert cmp_res["ok"] is True
    assert cmp_res["identical"] is False
    assert cmp_res["added_line_count"] == 1
    assert "HDMI: 640x480 @ 60Hz" in cmp_res["added_lines"][0]


@pytest.mark.live_fs
def test_10_live_fs_create_output_file_and_pdf_merge(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 10 (LIVE FILESYSTEM): Merge multiple documents into a single PDF output file and verify physical file on disk."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    doc1 = tmp_path / "laporan_1.md"
    doc2 = tmp_path / "laporan_2.txt"
    doc1.write_text("# Laporan Bagian 1\nVerifikasi L0-L7 selesai.", encoding="utf-8")
    doc2.write_text("Laporan Bagian 2: Integrasi L8-L11 lulus uji.", encoding="utf-8")

    out_pdf = ufe.output_dir / "gabungan_laporan.pdf"
    res = ufe.merge_documents_to_pdf([doc1, doc2], output_pdf_path=out_pdf, session_id="sess-10")
    assert res["ok"] is True
    assert out_pdf.is_file()
    assert out_pdf.stat().st_size > 100
    assert out_pdf.read_bytes().startswith(b"%PDF-1.4")

    # Verify the generated PDF can be read back
    read_back = ufe.doc_intelligence.inspect_and_extract(out_pdf)
    assert read_back["ok"] is True
    assert "Laporan Bagian 1" in read_back["text"]
    assert "Laporan Bagian 2" in read_back["text"]


@pytest.mark.live_fs
def test_11_live_fs_preserve_original_attachment_on_edit(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 11 (LIVE FILESYSTEM): Editing a `CHAT_ATTACHMENT` creates a new copy and NEVER overwrites the original file."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    orig_file = tmp_path / "kode_asli_pengguna.py"
    orig_content = "def hitung():\n    return 10\n"
    orig_file.write_text(orig_content, encoding="utf-8")
    orig_sha = orig_file.read_bytes()

    att = ufe.attach_and_register(
        name="kode_asli_pengguna.py",
        path_or_reference=str(orig_file),
        source_type="CHAT_ATTACHMENT",
        session_id="sess-edit-11",
    )
    rid = att["resource"]["resource_id"]

    edit_res = ufe.edit_resource_file(
        rid,
        target_snippet="return 10",
        replacement_snippet="return 112",
        allow_overwrite_original_attachment=False,
        session_id="sess-edit-11",
    )
    assert edit_res["ok"] is True
    assert edit_res["status"] == "EDITED_AS_NEW_COPY"
    assert edit_res["original_preserved"] is True
    # Original file on disk is untouched byte-for-byte
    assert orig_file.read_bytes() == orig_sha
    assert orig_file.read_text(encoding="utf-8") == orig_content
    # Edited copy exists at output_path with the new content
    edited_copy = Path(edit_res["output_path"])
    assert edited_copy.is_file()
    assert edited_copy != orig_file.resolve()
    assert "return 112" in edited_copy.read_text(encoding="utf-8")


@pytest.mark.live_fs
def test_12_live_fs_deny_folder_outside_permissions(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 12 (LIVE FILESYSTEM): Accessing a directory outside Connected Folders & Uploaded Folders is denied."""
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    unauthorized_dir = tmp_path / "folder_rahasia_tidak_terdaftar"
    unauthorized_dir.mkdir()
    (unauthorized_dir / "rahasia.txt").write_text("Data sensitif", encoding="utf-8")

    trav = ufe.list_and_traverse_directory(unauthorized_dir)
    assert trav["ok"] is False
    assert trav["status"] == "PATH_OUTSIDE_AUTHORIZED_RESOURCES"


@pytest.mark.live_fs
def test_13_live_fs_respect_read_only_folder(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 13 (LIVE FILESYSTEM): Connected Folder with `READ_ONLY` allows reading/traversal but blocks writing/editing."""
    app: NUILocalServiceApp = universal_env["app"]
    ufe: UniversalFileActionEngine = universal_env["ufe"]

    ro_dir = tmp_path / "folder_baca_saja"
    ro_dir.mkdir()
    ro_file = ro_dir / "konfigurasi.txt"
    ro_file.write_text("MODE=PRODUCTION\n", encoding="utf-8")

    app.storage.add_authorized_folder(ro_dir, label="folder_baca_saja", access_mode="READ_ONLY")
    ufe.registry.sync_system_resources()

    # Reading/traversal is allowed
    trav = ufe.list_and_traverse_directory(ro_dir)
    assert trav["ok"] is True
    assert trav["file_count"] == 1

    # Writing/editing in READ_ONLY folder is blocked
    edit_res = ufe.edit_resource_file(ro_file, new_content="MODE=HACKED\n")
    assert edit_res["ok"] is False
    assert edit_res["status"] == "FOLDER_READ_ONLY_DENIED"
    assert ro_file.read_text(encoding="utf-8") == "MODE=PRODUCTION\n"


@pytest.mark.live_fs
def test_14_live_fs_use_read_write_folder(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 14 (LIVE FILESYSTEM): Connected Folder with `READ_WRITE` permits authorized file creation and editing."""
    app: NUILocalServiceApp = universal_env["app"]
    ufe: UniversalFileActionEngine = universal_env["ufe"]

    rw_dir = tmp_path / "folder_kerja_rw"
    rw_dir.mkdir()
    rw_file = rw_dir / "modul.py"
    rw_file.write_text("VALUE = 1\n", encoding="utf-8")

    app.storage.add_authorized_folder(rw_dir, label="folder_kerja_rw", access_mode="READ_WRITE")
    ufe.registry.sync_system_resources()

    edit_res = ufe.edit_resource_file(rw_file, new_content="VALUE = 112\n")
    assert edit_res["ok"] is True
    assert edit_res["status"] == "EDITED_IN_PLACE"
    assert rw_file.read_text(encoding="utf-8") == "VALUE = 112\n"


# ===========================================================================
# TIER C: INTEGRATION TESTS (Scenarios 15, 16, 17)
# ===========================================================================


@pytest.mark.integration
def test_15_integration_chat_output_accessible_with_ui_actions(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 15 (INTEGRATION): Direct chat request generates verified output file and returns chat report with Copy, Open, and Reveal in Finder actions."""
    app: NUILocalServiceApp = universal_env["app"]
    app.storage.set_setting("active_provider", "native_nui")

    xlsx_file = tmp_path / "rekap_bulanan.xlsx"
    UniversalDocumentIntelligence.write_simple_xlsx(
        xlsx_file,
        sheet_name="Rekap",
        rows=[
            ["Item", "Jumlah"],
            ["Modul_L0", 12],
            ["Modul_L11", 31],
        ],
    )
    sess = app.storage.create_session("Chat Excel Report Session")
    sid = sess["session_id"]

    turn = app.orchestrator.handle_chat_turn(
        session_id=sid,
        user_message="Buatkan laporan dari semua file Excel ini.",
        attachments=[str(xlsx_file)],
        provider_id="native_nui",
    )
    assert turn["ok"] is True
    reply = turn["response"]
    assert "Laporan Eksekusi Berkas & Folder Universal NUI" in reply
    assert "file://" in reply
    assert "`Copy` · `Open` · `Reveal in Finder`" in reply

    uni_data = turn["data"]["universal_file_action"]
    assert uni_data["workflow_stages"] == list(ACTION_WORKFLOW_STAGES)
    assert len(uni_data["created_or_modified_files"]) == 1
    out_file = Path(uni_data["created_or_modified_files"][0])
    assert out_file.is_file()
    assert "43.0" in out_file.read_text(encoding="utf-8")

    # Verify Swift UI has Open and Reveal in Finder buttons bound to extractLocalFilePathsFromMessage
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "func extractLocalFilePathsFromMessage(_ content: String)" in swift_src
    assert "func openFileOutputInOS(_ path: String)" in swift_src
    assert "func revealFileOutputInFinder(_ path: String)" in swift_src
    assert 'Text("Reveal in Finder")' in swift_src


@pytest.mark.integration
def test_16_integration_process_multiple_attachments_in_one_job(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 16 (INTEGRATION): Process multiple heterogeneous attachments (DOCX + MD + TXT) in a single chat turn to merge into one PDF."""
    app: NUILocalServiceApp = universal_env["app"]
    app.storage.set_setting("active_provider", "native_nui")

    f_docx = tmp_path / "bagian_a.docx"
    UniversalDocumentIntelligence.write_simple_docx(
        f_docx, paragraphs=["Bagian A: Fondasi Atomik Huruf."]
    )
    f_md = tmp_path / "bagian_b.md"
    f_md.write_text("# Bagian B: Jembatan L4-L7\nParitas terverifikasi.", encoding="utf-8")
    f_txt = tmp_path / "bagian_c.txt"
    f_txt.write_text("Bagian C: Otonomi L8-L11.", encoding="utf-8")

    sess = app.storage.create_session("Multi Attachment Merge")
    sid = sess["session_id"]

    turn = app.orchestrator.handle_chat_turn(
        session_id=sid,
        user_message="Gabungkan semua laporan ini menjadi satu PDF.",
        attachments=[str(f_docx), str(f_md), str(f_txt)],
        provider_id="native_nui",
    )
    assert turn["ok"] is True
    uni_data = turn["data"]["universal_file_action"]
    assert uni_data["processed_file_count"] == 3
    out_pdf = Path(uni_data["output_location"])
    assert out_pdf.is_file()
    assert out_pdf.suffix == ".pdf"


@pytest.mark.integration
def test_17_integration_retain_resource_context_on_followup(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 17 (INTEGRATION): Retain resource context in the session so follow-up commands work without re-attaching files."""
    app: NUILocalServiceApp = universal_env["app"]
    app.storage.set_setting("active_provider", "native_nui")

    doc_alpha = tmp_path / "catatan_arsitektur.md"
    doc_alpha.write_text(
        "# Arsitektur CosmicTera\nNUI L0-L11 dan HCPU bekerja secara terpadu.",
        encoding="utf-8",
    )

    sess = app.storage.create_session("Followup Context Session")
    sid = sess["session_id"]

    # Turn 1: User attaches doc_alpha and asks NUI to inspect it
    t1 = app.orchestrator.handle_chat_turn(
        session_id=sid,
        user_message="Periksa file ini.",
        attachments=[str(doc_alpha)],
        provider_id="native_nui",
    )
    assert t1["ok"] is True
    assert "catatan_arsitektur.md" in t1["response"]

    # Turn 2: User sends a follow-up WITHOUT re-attaching the file: "Buat infografik berdasarkan dokumen tersebut."
    t2 = app.orchestrator.handle_chat_turn(
        session_id=sid,
        user_message="Buat infografik berdasarkan dokumen tersebut.",
        attachments=[],
        provider_id="native_nui",
    )
    assert t2["ok"] is True
    uni_t2 = t2["data"]["universal_file_action"]
    assert uni_t2["resolution"]["resolution_tier"] == "SESSION_PREVIOUS_ATTACHMENT"
    assert len(uni_t2["created_or_modified_files"]) == 1
    svg_out = Path(uni_t2["created_or_modified_files"][0])
    assert svg_out.is_file()
    assert svg_out.suffix == ".svg"


# ===========================================================================
# TIER B: MOCK TESTS (Scenario 18 — VPS Connection Verification Gate)
# ===========================================================================


@pytest.mark.mock
def test_18_mock_vps_transfer_only_after_verified_connection(
    universal_env: dict[str, Any], tmp_path: Path
):
    """Scenario 18 (MOCK): Transferring a file/folder to VPS is blocked when unconfigured or disconnected, and succeeds ONLY after SSH + host fingerprint + VPS_WRITE permission are verified."""
    app: NUILocalServiceApp = universal_env["app"]
    ufe: UniversalFileActionEngine = universal_env["ufe"]
    remote_engine: RemoteVPSDevelopmentEngine = universal_env["remote_engine"]
    mock_ssh: MockVPSVerificationTransport = universal_env["mock_ssh"]

    pkg_dir = tmp_path / "paket_deploy_yayasan"
    pkg_dir.mkdir()
    (pkg_dir / "app.py").write_text("print('Yayasan Service Ready')\n", encoding="utf-8")
    app.storage.add_authorized_folder(pkg_dir, label="paket_deploy_yayasan", access_mode="READ_WRITE")

    # 18a. Attempt transfer before any VPS profile exists -> blocked (VPS_NOT_CONFIGURED)
    res_no_prof = ufe.transfer_resource_to_vps(pkg_dir)
    assert res_no_prof["ok"] is False
    assert res_no_prof["status"] == "VPS_NOT_CONFIGURED"

    # 18b. Register VPS profile but do NOT connect -> blocked (VPS_NOT_CONNECTED_OR_UNVERIFIED)
    prof = remote_engine.register_profile(
        name="Yayasan Production VPS",
        host="203.0.113.88",
        username="ubuntu",
        expected_host_fingerprint=mock_ssh.known_fingerprint,
        remote_workspace="/home/ubuntu/workspace",
    )
    pid = prof["profile_id"]
    res_disconn = ufe.transfer_resource_to_vps(pkg_dir, profile_id=pid)
    assert res_disconn["ok"] is False
    assert res_disconn["status"] == "VPS_NOT_CONNECTED_OR_UNVERIFIED"
    assert len(mock_ssh.uploaded_files) == 0

    # 18c. Grant VPS_CONNECT + VPS_WRITE, connect with verified host fingerprint, then transfer -> succeeds!
    for scope in ("VPS_CONNECT", "VPS_WRITE"):
        app.permissions.set_rule(
            category=scope,
            target_type="endpoint",
            target_value="*",
            operation="*",
            decision="ALWAYS_ALLOW",
        )
    conn = remote_engine.connect_and_inspect(pid)
    assert conn["ok"] is True

    res_ok = ufe.transfer_resource_to_vps(pkg_dir, profile_id=pid)
    assert res_ok["ok"] is True
    assert res_ok["status"] == "TRANSFERRED_TO_VPS"
    assert res_ok["uploaded_file_count"] == 1
    assert "/home/ubuntu/workspace/paket_deploy_yayasan/app.py" in mock_ssh.uploaded_files
