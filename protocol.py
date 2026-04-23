"""
protocol.py — Binary framing for screenshot transfer.

Wire format:
  [4 bytes]  magic: b'SNAP'
  [4 bytes]  metadata length  (uint32 big-endian)
  [4 bytes]  image data length (uint32 big-endian)
  [N bytes]  JSON metadata (UTF-8)
  [M bytes]  PNG image data
"""

import json
import struct
import time

MAGIC = b"SNAP"
HEADER_SIZE = 12          # 4 magic + 4 meta_len + 4 img_len
MAX_IMAGE_BYTES = 100 * 1024 * 1024   # 100 MB hard ceiling


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------

def encode_message(sender_name: str, image_data: bytes) -> bytes:
    """Pack sender metadata + PNG bytes into a wire frame."""
    meta = json.dumps(
        {
            "sender": sender_name,
            "timestamp": time.time(),
            "image_size": len(image_data),
        },
        separators=(",", ":"),
    ).encode("utf-8")

    header = MAGIC + struct.pack(">II", len(meta), len(image_data))
    return header + meta + image_data


# ---------------------------------------------------------------------------
# Decode
# ---------------------------------------------------------------------------

def decode_stream(buf: bytes):
    """
    Try to decode one complete frame from *buf*.

    Returns:
        (metadata: dict, image_data: bytes, consumed: int)  — on success
        None                                                 — need more data
    Raises:
        ValueError  — malformed frame (bad magic, oversized, invalid JSON)
    """
    if len(buf) < HEADER_SIZE:
        return None

    if buf[:4] != MAGIC:
        raise ValueError(f"Bad magic bytes: {buf[:4]!r}")

    meta_len, img_len = struct.unpack(">II", buf[4:12])

    if img_len > MAX_IMAGE_BYTES:
        raise ValueError(f"Payload too large: {img_len} bytes (max {MAX_IMAGE_BYTES})")

    total = HEADER_SIZE + meta_len + img_len
    if len(buf) < total:
        return None   # need more data

    meta_bytes = buf[HEADER_SIZE : HEADER_SIZE + meta_len]
    img_bytes  = buf[HEADER_SIZE + meta_len : total]

    try:
        metadata = json.loads(meta_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid metadata JSON: {exc}") from exc

    return metadata, img_bytes, total
