import re


SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
EXECUTABLE_MAGIC_HEADERS = (
    b"MZ",  # PE/EXE
    b"\x7fELF",  # ELF
    b"\xfe\xed\xfa\xce",  # Mach-O (32-bit, big endian)
    b"\xce\xfa\xed\xfe",  # Mach-O (32-bit, little endian)
    b"\xfe\xed\xfa\xcf",  # Mach-O (64-bit, big endian)
    b"\xcf\xfa\xed\xfe",  # Mach-O (64-bit, little endian)
)


def is_safe_filename(filename: str) -> bool:
    if not filename or filename.startswith("."):
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    return SAFE_FILENAME_PATTERN.fullmatch(filename) is not None


def has_executable_signature(content: bytes) -> bool:
    for signature in EXECUTABLE_MAGIC_HEADERS:
        if content.startswith(signature):
            return True
    return False
