from docreview360.approvals import create_approval, send_for_signature


def test_provider_metadata_persisted() -> None:
    appr = create_approval("wf1", "alice", "doc1", document=b"data", signature_provider="documenso")
    send_for_signature(appr.id, "doc1", "alice")
    assert appr.provider_metadata.get("envelope_id") == appr.signature_id
