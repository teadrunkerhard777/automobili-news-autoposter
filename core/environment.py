import os

import certifi


def configure_ssl():
    """Use certifi without disabling TLS verification."""

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    return os.environ["SSL_CERT_FILE"]

