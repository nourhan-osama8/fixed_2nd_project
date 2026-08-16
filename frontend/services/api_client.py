import requests
from typing import Optional, Any
from config.settings import BACKEND_URL
from utils.session import get_token


def _headers() -> dict:
    token = get_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get(endpoint: str, params: Optional[dict] = None) -> Any:
    try:
        resp = requests.get(f"{BACKEND_URL}{endpoint}", headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to the backend. Make sure the API server is running."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": detail, "status_code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}


def post(endpoint: str, data: dict) -> Any:
    try:
        resp = requests.post(f"{BACKEND_URL}{endpoint}", headers=_headers(), json=data, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to the backend."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": detail, "status_code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}


def patch(endpoint: str, data: dict) -> Any:
    try:
        resp = requests.patch(f"{BACKEND_URL}{endpoint}", headers=_headers(), json=data, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to the backend."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": detail, "status_code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}


def delete(endpoint: str) -> Any:
    try:
        resp = requests.delete(f"{BACKEND_URL}{endpoint}", headers=_headers(), timeout=15)
        resp.raise_for_status()
        return {"success": True}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to the backend."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": detail, "status_code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}


def upload_file(endpoint: str, file_bytes: bytes, filename: str, content_type: str) -> Any:
    token = get_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.post(
            f"{BACKEND_URL}{endpoint}",
            headers=headers,
            files={"file": (filename, file_bytes, content_type)},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to the backend."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": detail, "status_code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}


def ai_post(endpoint: str, data: dict) -> Any:
    """
    Like post(), but uses a much longer timeout (120 s) for AI endpoints
    that run multi-step agentic reasoning and can legitimately take time.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}{endpoint}",
            headers=_headers(),
            json=data,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "The AI assistant is taking longer than expected. Please try again or rephrase your question."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to the backend. Make sure the API server is running."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": detail, "status_code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}

