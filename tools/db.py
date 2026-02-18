import os

_client = None


def get_db():
    global _client
    if _client is not None:
        return _client

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        return None

    try:
        from google.cloud import firestore
        _client = firestore.Client(project=project)
        return _client
    except Exception:
        return None
