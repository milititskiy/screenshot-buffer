"""
sender_service.py — TCP client: frame and ship a screenshot to the target.
"""

import socket
from protocol import encode_message


class SenderService:
    def __init__(self, settings) -> None:
        self._settings = settings

    def send_screenshot(self, image_data: bytes) -> bool:
        """
        Encode and send *image_data* to the configured target.

        Returns True on success, False on any network error.
        """
        ip   = self._settings.target_ip
        port = self._settings.port
        name = self._settings.sender_name

        payload = encode_message(name, image_data)

        try:
            with socket.create_connection((ip, port), timeout=10) as sock:
                # sendall guarantees every byte is delivered or raises
                sock.sendall(payload)
            print(f"[Sender] Sent {len(payload):,} bytes → {ip}:{port}")
            return True

        except ConnectionRefusedError:
            print(f"[Sender] Connection refused — is the receiver running on {ip}:{port}?")
        except socket.timeout:
            print(f"[Sender] Connection to {ip}:{port} timed out")
        except OSError as exc:
            print(f"[Sender] Network error: {exc}")

        return False
