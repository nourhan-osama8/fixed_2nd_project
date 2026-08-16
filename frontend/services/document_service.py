from services import api_client


def get_documents(skip=0, limit=50, status=None):
    params = {"skip": skip, "limit": limit}
    if status:
        params["status"] = status
    return api_client.get("/documents", params=params)


def get_document(document_id: str):
    return api_client.get(f"/documents/{document_id}")


def upload_document(uploaded_file) -> dict:
    """Accept a Streamlit UploadedFile object."""
    return api_client.upload_file(
        "/documents/upload",
        uploaded_file.read(),
        uploaded_file.name,
        uploaded_file.type,
    )


def delete_document(document_id: str):
    return api_client.delete(f"/documents/{document_id}")
