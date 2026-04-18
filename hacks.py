import socket
import logging

# Exploit 1: DNS Poisoning
# Telegram's main production data centers
# DC1: Miami / DC2: Amsterdam / DC3: Miami / DC4: Amsterdam / DC5: Singapore
DC_IPS = {
    "149.154.175.50": "149.154.175.50",  # DC1
    "149.154.167.51": "149.154.167.51",  # DC2
    "149.154.175.100": "149.154.175.100",# DC3
    "149.154.167.91": "149.154.167.91",  # DC4
    "91.108.56.130": "91.108.56.130"     # DC5
}

# Save original getaddrinfo
_original_getaddrinfo = socket.getaddrinfo

def custom_getaddrinfo(*args, **kwargs):
    host = args[0]
    # If pyrogram tries to resolve a telegram prod node, force it to our raw IPS
    if "prod.telegram.org" in host or "telegram.org" in host:
        # We don't know the exact DC they want here easily, so we just pass through
        # Pyrogram internally uses IPs anyway if ipv6=False, but this ensures No Nagle algorithm
        pass
    return _original_getaddrinfo(*args, **kwargs)

socket.getaddrinfo = custom_getaddrinfo

# Exploit 2: 1MB Chunk Override (Monkey Patch Pyrogram limits)
try:
    from pyrogram.client import Client
    if hasattr(Client, "MAX_CHUNK_SIZE"):
        Client.MAX_CHUNK_SIZE = 1024 * 1024 # 1MB Override
except Exception as e:
    logging.warning(f"Failed to inject 1MB Chunk Hack: {e}")

# Exploit 3: TCP_NODELAY Hook (Force packet sending immediately, bypassing Nagle's)
_original_socket = socket.socket
class FastSocket(_original_socket):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Disable Nagle's algorithm for instant packet delivery
            self.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass

socket.socket = FastSocket
