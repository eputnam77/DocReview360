from docreview360.stubs.task81 import AlfrescoClient


def test_alfresco_upload_download() -> None:
    client = AlfrescoClient()
    client.upload_document("1", "data")
    assert client.download_document("1") == "data"
