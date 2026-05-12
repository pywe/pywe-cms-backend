def envelope(success: bool, data=None, message=None) -> dict:
    """JSON-serializable API body. Callers wrap with ``Response(...)`` and set HTTP status."""
    body: dict = {"success": success}
    if data is not None:
        body["data"] = data
    if message is not None:
        body["message"] = message
    return body
