# ruff: noqa: E402
import asyncio
import statistics
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from docreview360.documents import import_document

api_module = types.ModuleType("docreview360.api")
webhooks_module = types.ModuleType("docreview360.api.webhooks")


def emit_verification_completed(*args, **kwargs) -> None:
    pass


webhooks_module.emit_verification_completed = emit_verification_completed
api_module.webhooks = webhooks_module
sys.modules["docreview360.api"] = api_module
sys.modules["docreview360.api.webhooks"] = webhooks_module

from docreview360.approvals import (
    create_approval,
    handle_signature_return,
    send_for_signature,
    verify_document_signature,
)
from docreview360.integrations.signature import documenso


@dataclass
class Metrics:
    avg_latency: float
    throughput: float
    failures: int
    total: int

    @property
    def failure_rate(self) -> float:
        return self.failures / self.total if self.total else 0.0


def _generate_certificate() -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DocReview360 Test CA")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow() - timedelta(days=1))
        .not_valid_after(datetime.utcnow() + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return cert, key


def _prepare_documents(n: int) -> List[str]:
    cert, key = _generate_certificate()
    docs: List[str] = []
    for i in range(n):
        content = f"performance document {i}".encode()
        doc = import_document(f"perf{i}.txt", content)
        approval = create_approval(
            f"wf{i}", f"user{i}", doc.id, document=content, signature_provider="documenso"
        )
        send_for_signature(approval.id, doc.id, f"user{i}")
        documenso.complete_signature(approval.signature_id)
        signature = key.sign(content, padding.PKCS1v15(), hashes.SHA256())
        cert_url = f"https://example.com/cert/{i}"
        documenso.register_test_certificate(cert_url, cert, signature)
        documenso._sig_certificates[approval.signature_id] = cert_url
        asyncio.run(
            handle_signature_return(
                approval.signature_id,
                document=content,
                certificate_url=cert_url,
            )
        )
        docs.append(doc.id)
    return docs


def _verify(doc_id: str) -> Tuple[float, bool]:
    start = time.perf_counter()
    result = verify_document_signature(doc_id)
    latency = time.perf_counter() - start
    success = result["status"] == "pass"
    return latency, success


def run_stress(total_docs: int = 50, workers: int = 10) -> Metrics:
    docs = _prepare_documents(total_docs)
    latencies: List[float] = []
    failures = 0
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for latency, success in pool.map(_verify, docs):
            latencies.append(latency)
            if not success:
                failures += 1
    duration = time.perf_counter() - start
    throughput = total_docs / duration if duration else 0.0
    avg_latency = statistics.mean(latencies) if latencies else 0.0
    return Metrics(
        avg_latency=avg_latency,
        throughput=throughput,
        failures=failures,
        total=total_docs,
    )


def main() -> None:
    metrics = run_stress()
    print(f"Average latency: {metrics.avg_latency:.4f} s")
    print(f"Throughput: {metrics.throughput:.2f} verifications/s")
    print(f"Failure rate: {metrics.failure_rate:.2%} ({metrics.failures}/{metrics.total})")


if __name__ == "__main__":
    main()
