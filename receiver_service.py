"""
receiver_service.py — TCP server: listen for incoming screenshots.

Runs a background listener thread.  Each accepted connection is handled
in its own daemon thread so concurrent senders don't block each other.

The `on_received(metadata, image_bytes)` callback is called from the
connection-handler thread; callers must be thread-safe (e.g. emit a Qt
signal instead of touching the UI directly).
"""

import socket
import struct
import threading
import time
from typing import Callable

from protocol import MAGIC, HEADER_SIZE, MAX_IMAGE_BYTES, decode_stream

_RECV_CHUNK  = 65_536   # bytes per recv() call
_CONN_TIMEOUT = 15       # seconds to read a full frame before giving up


class ReceiverService:
    def __init__(self, settings, on_received: Callable) -> None:
        self._settings    = settings
        self._on_received = on_received
        self._running     = False
        self._server_sock: socket.socket | None = None
        self._listen_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._listen_thread = threading.Thread(
            target=self._serve, daemon=True, name="ReceiverListen"
        )
        self._listen_thread.start()
        print(f"[Receiver] Listening on 0.0.0.0:{self._settings.port}")

    def stop(self) -> None:
        self._running = False
        sock = self._server_sock
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        self._server_sock = None
        print("[Receiver] Stopped")

    # ------------------------------------------------------------------
    # Server loop
    # ------------------------------------------------------------------

    def _serve(self) -> None:
        while self._running:
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(("0.0.0.0", self._settings.port))
                srv.listen(5)
                srv.settimeout(1.0)
                self._server_sock = srv

                while self._running:
                    try:
                        conn, addr = srv.accept()
                    except socket.timeout:
                        continue
                    threading.Thread(
                        target=self._handle,
                        args=(conn, addr),
                        daemon=True,
                        name=f"RecvConn-{addr}",
                    ).start()

            except OSError as exc:
                if self._running:
                    print(f"[Receiver] Server error ({exc}), retrying in 3 s …")
                    time.sleep(3)
            finally:
                if self._server_sock is not None:
                    try:
                        self._server_sock.close()
                    except OSError:
                        pass
                    self._server_sock = None

    # ------------------------------------------------------------------
    # Per-connection handler
    # ------------------------------------------------------------------

    def _handle(self, conn: socket.socket, addr) -> None:
        buf = b""
        try:
            conn.settimeout(_CONN_TIMEOUT)
            with conn:
                while True:
                    chunk = conn.recv(_RECV_CHUNK)
                    if not chunk:
                        break
                    buf += chunk

                    # Early size-abuse check — read header fields as soon as we have them
                    if len(buf) >= HEADER_SIZE:
                        if buf[:4] != MAGIC:
                            print(f"[Receiver] Bad magic from {addr}, dropping")
                            return

                        _, img_len = struct.unpack(">II", buf[4:12])
                        if img_len > MAX_IMAGE_BYTES:
                            print(
                                f"[Receiver] Oversized payload ({img_len} bytes) "
                                f"from {addr}, dropping"
                            )
                            return

                        # Try to decode a complete frame
                        try:
                            result = decode_stream(buf)
                        except ValueError as exc:
                            print(f"[Receiver] Protocol error from {addr}: {exc}")
                            return

                        if result is not None:
                            metadata, image_data, _consumed = result
                            print(
                                f"[Receiver] Got screenshot from "
                                f"'{metadata.get('sender', addr)}' "
                                f"({len(image_data):,} bytes)"
                            )
                            self._on_received(metadata, image_data)
                            return   # one frame per connection

        except socket.timeout:
            print(f"[Receiver] Connection from {addr} timed out ({_CONN_TIMEOUT}s)")
        except OSError as exc:
            if self._running:
                print(f"[Receiver] Connection error from {addr}: {exc}")
