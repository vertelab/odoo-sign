# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Resolve BankID client certificates without hardcoded filesystem paths.

`pybankid.BankIDClient` takes *filesystem paths* to a PEM certificate and a
PEM private key, not the certificate bytes. Odoo stores uploaded files as
Binary fields (base64 in the database), so the bytes have to be materialised
on disk before the client is built.

Two credential sources are supported, in this order:

1. The provider's ``bankid_cert_file`` / ``bankid_key_file`` Binary fields
   (uploaded through the UI). These are written to a private temporary
   directory (mode 0700, files mode 0600) for the lifetime of the client.
2. The bundled test certificates shipped with the ``pybankid`` package,
   used only when the provider is in test mode and no upload exists.

The previous implementation hardcoded absolute paths into a developer's home
directory (``/home/<user>/Downloads/...``). Those paths do not exist on any
server, so every signing attempt raised ``FileNotFoundError``. Never
reintroduce a machine-specific path here.
"""

import base64
import binascii
import logging
import os
import shutil
import tempfile

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Certificates bundled with the pybankid package (BankID's public test certs).
BANKID_PACKAGE_CERT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "certs"
)
BUNDLED_TEST_CERT = "FPTestcert5_20240610_cert.pem"
BUNDLED_TEST_KEY = "FPTestcert5_20240610_key.pem"


def _bundled_test_certificates():
    """Return (cert, key) paths for the pybankid bundled test certificate."""
    try:
        import bankid

        cert_dir = os.path.join(os.path.dirname(os.path.abspath(bankid.__file__)), "certs")
    except ImportError:  # pragma: no cover - pybankid is a hard dependency
        cert_dir = BANKID_PACKAGE_CERT_DIR

    cert = os.path.join(cert_dir, BUNDLED_TEST_CERT)
    key = os.path.join(cert_dir, BUNDLED_TEST_KEY)
    return cert, key


def _decode_binary(value):
    """Decode an Odoo Binary field value to bytes.

    Odoo hands back base64 bytes (or str) for Binary fields. Returns None when
    the field is empty or cannot be decoded.
    """
    if not value:
        return None, True
    if isinstance(value, str):
        value = value.encode()
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        _logger.warning("BankID: uploaded certificate is not valid base64")
        return None, False
    return (decoded or None), True


class BankIDCredentials:
    """Context manager yielding (cert_path, key_path) for BankIDClient.

    When certificates come from uploaded Binary fields they are written to a
    private temporary directory that is removed on exit. When the bundled test
    certificate is used, nothing is written and nothing is removed.
    """

    def __init__(self, cert_binary=None, key_binary=None, allow_test_fallback=True):
        self.cert_binary = cert_binary
        self.key_binary = key_binary
        self.allow_test_fallback = allow_test_fallback
        self._tmpdir = None
        self.cert_path = None
        self.key_path = None
        self.using_bundled_test_cert = False

    def __enter__(self):
        cert_bytes, cert_ok = _decode_binary(self.cert_binary)
        key_bytes, key_ok = _decode_binary(self.key_binary)

        # A corrupt upload must fail loudly. Falling back to the bundled test
        # certificate would hide the problem and, in production, sign with the
        # wrong credentials.
        if not (cert_ok and key_ok):
            raise UserError(
                _(
                    "BankID: the uploaded %(what)s could not be read (not "
                    "valid base64). Upload it again.",
                    what=_("private key") if not key_ok else _("certificate"),
                )
            )

        if cert_bytes and key_bytes:
            self._tmpdir = tempfile.mkdtemp(prefix="bankid-")
            os.chmod(self._tmpdir, 0o700)
            self.cert_path = os.path.join(self._tmpdir, "cert.pem")
            self.key_path = os.path.join(self._tmpdir, "key.pem")
            for path, data in ((self.cert_path, cert_bytes), (self.key_path, key_bytes)):
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as fh:
                    fh.write(data)
            return self.cert_path, self.key_path

        if bool(cert_bytes) != bool(key_bytes):
            raise UserError(
                _(
                    "BankID: both the certificate and the private key must be "
                    "uploaded. Only one of them is set."
                )
            )

        if not self.allow_test_fallback:
            raise UserError(
                _(
                    "BankID: no certificate uploaded. Upload the BankID "
                    "certificate and private key on the provider before signing."
                )
            )

        cert, key = _bundled_test_certificates()
        if not (os.path.isfile(cert) and os.path.isfile(key)):
            raise UserError(
                _(
                    "BankID: no certificate uploaded and the bundled pybankid "
                    "test certificate was not found at %(dir)s. Upload the "
                    "certificate and private key on the provider.",
                    dir=os.path.dirname(cert),
                )
            )

        self.using_bundled_test_cert = True
        self.cert_path, self.key_path = cert, key
        _logger.warning(
            "BankID: using the bundled pybankid TEST certificate. "
            "Signatures are not legally valid. Upload a real certificate "
            "on the provider to sign for production."
        )
        return self.cert_path, self.key_path

    def __exit__(self, exc_type, exc, tb):
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
        return False
