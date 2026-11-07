"""What a student may attach to a post, and how big it may be.

Students share the way they already do on WhatsApp: a photo of a worked
question, a past paper, a voice note explaining a step. So attachments are
expected, not exceptional.

The limits are here rather than in the router because an upload rule that
only exists at the edge is one bad import away from being skipped. These are
plain functions over a filename, a declared type and a byte count, so every
awkward case - the file named "notes.pdf.exe", the photo declared as text,
the empty upload - can be checked without a server.

Nothing here trusts the browser. A content type is a claim made by whatever
sent the request, so the bytes are sniffed as well, and the two must agree.
"""

# The ceiling, as asked for: 50MB. Generous enough for a scanned past paper,
# small enough that one student cannot fill the bucket.
MAX_BYTES = 50 * 1024 * 1024
# A voice note is a different thing from a file: long ones do not get
# listened to, and they are recorded in the browser so the size is ours to
# control. Ten minutes of decent audio sits well under this.
MAX_VOICE_BYTES = 16 * 1024 * 1024
MAX_VOICE_SECONDS = 600

# How many files may hang off one post. More than this is a folder, and a
# folder belongs in Documents where it gets indexed and searched.
MAX_ATTACHMENTS = 5

# What each kind is for, and which content types belong to it. Kinds exist
# because the page shows them differently: an image inline, a voice note as a
# player, everything else as something to download.
IMAGE = "image"
AUDIO = "audio"
FILE = "file"

IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/heic": ".heic",
}

AUDIO_TYPES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}

FILE_TYPES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/plain": ".txt",
    "text/csv": ".csv",
}

ALLOWED = {**IMAGE_TYPES, **AUDIO_TYPES, **FILE_TYPES}

# Deliberately absent: anything executable, and any archive. A zip cannot be
# scanned without unpacking it, and a room of teenagers passing each other
# zip files is a way to move things nobody has looked at.
NEVER = (
    ".exe", ".msi", ".bat", ".cmd", ".com", ".scr", ".pif", ".jar",
    ".app", ".dmg", ".deb", ".rpm", ".sh", ".ps1", ".vbs", ".js",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".apk", ".dll",
    ".html", ".htm", ".svg",  # can carry script, and render as a page
)

# Bytes that are never acceptable whatever the upload claims to be. These
# are checked before anything else, because an unrecognised signature is
# treated as "cannot confirm" and allowed through - which is right for an
# unusual document and badly wrong for a Windows executable renamed to
# .png. MZ was not in the signature list, so a program declared as an image
# was accepted on the browser's word alone.
DANGEROUS_SIGNATURES = (
    (b"MZ", "a Windows program"),
    (b"\x7fELF", "a Linux program"),
    (b"\xca\xfe\xba\xbe", "a Mac program"),
    (b"\xfe\xed\xfa", "a Mac program"),
    (b"Rar!", "an archive"),
    (b"7z\xbc\xaf", "an archive"),
    (b"\x1f\x8b", "an archive"),
    (b"#!", "a script"),
    (b"<?php", "a script"),
    (b"<!DOCTYPE", "a web page"),
    (b"<html", "a web page"),
    (b"<svg", "a web page"),
)

# The first bytes of a file say what it really is, whatever the browser
# claimed. Only the formats where this is cheap and unambiguous are listed;
# an unrecognised signature is not an error, it just cannot confirm.
SIGNATURES = (
    (b"\xff\xd8\xff", IMAGE),
    (b"\x89PNG\r\n\x1a\n", IMAGE),
    (b"GIF87a", IMAGE),
    (b"GIF89a", IMAGE),
    (b"%PDF-", FILE),
    (b"PK\x03\x04", FILE),   # docx, xlsx, pptx are zips underneath
    (b"\xd0\xcf\x11\xe0", FILE),  # old Office
    (b"OggS", AUDIO),
    (b"ID3", AUDIO),
    (b"\x1a\x45\xdf\xa3", AUDIO),  # webm/matroska
)


def kind_of(content_type: str) -> str | None:
    """Which of the three kinds this type is, or None if it is not allowed."""
    said = (content_type or "").split(";")[0].strip().lower()
    if said in IMAGE_TYPES:
        return IMAGE
    if said in AUDIO_TYPES:
        return AUDIO
    if said in FILE_TYPES:
        return FILE
    return None


def dangerous_bytes(head: bytes) -> str | None:
    """What this really is, if it is something that must never be stored.

    Checked before the kind-matching below, because an unrecognised
    signature is deliberately treated as "cannot confirm" and allowed
    through. That is right for an unusual document and badly wrong for a
    Windows executable renamed to .png: MZ was not in the signature list, so
    a program declared as an image was accepted on the browser's word alone.

    A plain zip is not listed. A docx, xlsx and pptx are all zips underneath
    and share its first bytes, so banning the signature would refuse every
    Office file a student has. The extension list in NEVER is what keeps
    archives out, and the kinds allowed above never include one.
    """
    for magic, what in DANGEROUS_SIGNATURES:
        if head.startswith(magic):
            return what
    return None


def sniffed_kind(head: bytes) -> str | None:
    """What the first bytes say this is, ignoring what the browser claimed."""
    for magic, kind in SIGNATURES:
        if head.startswith(magic):
            return kind
    return None


def safe_name(filename: str | None) -> str:
    """A filename safe to store and to show.

    Strips any path the browser sent, because "../../etc/passwd" is a
    filename as far as an upload form is concerned, and flattens the rest to
    characters that cannot surprise a shell, a URL or a filesystem.
    """
    raw = (filename or "").replace("\\", "/").split("/")[-1].strip()
    kept = "".join(
        c if (c.isalnum() or c in " ._-") else "_" for c in raw
    ).strip(" .")
    # Leading dots make a hidden file; a name of only dots leaves nothing.
    kept = kept.lstrip(".")
    if not kept:
        return "attachment"
    return kept[:120]


def extension_of(filename: str | None) -> str:
    """The lowercased extension, including the dot, or empty."""
    name = safe_name(filename)
    return ("." + name.rsplit(".", 1)[1].lower()) if "." in name else ""


def check_upload(
    filename: str | None,
    content_type: str | None,
    size: int,
    head: bytes = b"",
) -> tuple[str, str]:
    """Approve one attachment, or raise ValueError saying why not.

    Returns the kind and the safe filename. Every message is written to be
    read by a student, so it says what to do rather than what went wrong.
    """
    if size <= 0:
        raise ValueError("That file is empty.")

    kind = kind_of(content_type or "")
    if kind is None:
        raise ValueError(
            "That kind of file cannot be shared here. Photos, PDFs, Word, "
            "PowerPoint, Excel, text and voice notes are fine."
        )

    extension = extension_of(filename)
    if extension in NEVER:
        raise ValueError(
            "That kind of file cannot be shared here, for everyone's safety."
        )

    cap = MAX_VOICE_BYTES if kind == AUDIO else MAX_BYTES
    if size > cap:
        raise ValueError(
            f"That file is {size / (1024 * 1024):.0f}MB. The limit is "
            f"{cap // (1024 * 1024)}MB"
            + (" for a voice note." if kind == AUDIO else ".")
        )

    # A browser can claim anything, so the bytes get the final say. Known
    # dangerous content is refused first and outright, because the general
    # mismatch test below only fires when the bytes are recognisable, and
    # "unrecognised" must not become a way in for a program.
    if head:
        danger = dangerous_bytes(head)
        if danger is not None:
            raise ValueError(
                f"That file is {danger}, whatever it is named. It cannot be "
                "shared here."
            )
        real = sniffed_kind(head)
        if real is not None and real != kind:
            raise ValueError(
                "That file is not what it says it is, so it cannot be shared."
            )

    return kind, safe_name(filename)


def check_attachment_count(count: int) -> None:
    """At most MAX_ATTACHMENTS on one post."""
    if count > MAX_ATTACHMENTS:
        raise ValueError(
            f"At most {MAX_ATTACHMENTS} files on one post. "
            "Put the rest in a reply, or upload them to a project."
        )


def stored_path(grade: int, group_code: str, post_id: str, index: int, extension: str) -> str:
    """Where an attachment lives in the bucket.

    Keyed by room so a room's files can be found, and by post so deleting a
    post can find them again.
    """
    return f"community/{grade}-{group_code}/{post_id}/{index}{extension}"
