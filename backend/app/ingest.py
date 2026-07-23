import re
from pypdf import PdfReader


def extract_text(filename: str, file_obj) -> str:
    """Extract Text in PDF"""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(file_obj)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return file_obj.read().decode("utf-8", errors="ignore")

def make_base_id(filename: str) -> str:
    """Format File name"""
    stem = filename.rsplit(".", 1)[0].lower()
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_")