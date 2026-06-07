# app/modules/ml/engine/postprocessor.py
#
# -> post-processing output SOP dari model
#      -> clean_output       : bersihkan artifact model (token sisa, whitespace)
#      -> parse_steps_from_sop : ekstrak langkah bernomor → list StepItem dict
#      -> validate_output    : cek minimum quality output

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# clean ───────────────────────────────────────────────────────────────────────

# bersihkan artifact output model
# - input  : text (str raw output model)
# - output : str yang sudah dibersihkan
# - hapus  : <bos>, <eos>, <pad>, <unk>, leading/trailing whitespace berlebih
def clean_output(text: str) -> str:
    if not text:
        return ""
    # hapus special tokens sisa model
    text = re.sub(r"<(bos|eos|pad|unk|start_of_turn|end_of_turn)[^>]*>", "", text)
    # hapus baris yang hanya berisi whitespace berulang
    text = re.sub(r"\n{3,}", "\n\n", text)
    # hapus trailing whitespace per baris
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()

# end of clean ────────────────────────────────────────────────────────────────


# step parsing ────────────────────────────────────────────────────────────────

# ekstrak langkah bernomor dari teks SOP menjadi list dict
# - input  : text (str output SOP yang sudah di-clean)
# - output : list[dict] dengan field { no, judul, deskripsi, pic, durasi }
# - support: "1. Judul" atau "1. Judul\n   Deskripsi" atau "| 1 | Judul | Desc |"
def parse_steps_from_sop(text: str) -> list[dict]:
    steps = []

    # format: "1. Teks langkah" — bisa multiline sebelum nomor berikutnya
    pattern = re.compile(r"(?m)^(\d+)\.\s+(.+?)(?=\n\d+\.|\Z)", re.DOTALL)
    matches = pattern.findall(text)

    if matches:
        for no_str, content in matches:
            content = content.strip()
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            judul = lines[0] if lines else content
            deskripsi = " ".join(lines[1:]) if len(lines) > 1 else judul

            # bersihkan markdown dari judul (bold, italic)
            judul = re.sub(r"\*+|_+", "", judul).strip()

            steps.append({
                "no": int(no_str),
                "judul": judul[:200],
                "deskripsi": deskripsi[:500],
                "pic": None,
                "durasi": None,
            })
        return steps

    # format tabel markdown: | no | judul | deskripsi | pic | durasi |
    table_pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)\s*\|(?:\s*([^|]*)\s*\|)?(?:\s*([^|]*)\s*\|)?",
    )
    for match in table_pattern.finditer(text):
        groups = match.groups()
        if not groups[0]:
            continue
        steps.append({
            "no": int(groups[0]),
            "judul": (groups[1] or "").strip()[:200],
            "deskripsi": (groups[2] or "").strip()[:500],
            "pic": (groups[3] or "").strip() or None,
            "durasi": (groups[4] or "").strip() or None,
        })

    return steps

# end of step parsing ─────────────────────────────────────────────────────────


# validation ──────────────────────────────────────────────────────────────────

# validasi minimum kualitas output SOP
# - input  : text (str), min_chars (int, default 100)
# - output : bool True kalau output dianggap valid
def validate_output(text: str, min_chars: int = 100) -> bool:
    if not text or len(text.strip()) < min_chars:
        return False
    # cek ada konten bermakna (bukan hanya whitespace atau karakter berulang)
    if len(set(text.strip())) < 5:
        return False
    return True

# end of validation ───────────────────────────────────────────────────────────
