from __future__ import annotations

import hashlib


def test_update_version_and_architecture(monkeypatch) -> None:
    from app.ui.components import update_dialog

    assert update_dialog._version_key("v0.1.10") > update_dialog._version_key("0.1.9")
    monkeypatch.setattr(update_dialog.platform, "system", lambda: "Windows")
    monkeypatch.setattr(update_dialog.platform, "machine", lambda: "AMD64")
    assert update_dialog._architecture_asset() == "AIMux-Windows-x64.exe"
    monkeypatch.setattr(update_dialog.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(update_dialog.platform, "machine", lambda: "arm64")
    assert update_dialog._architecture_asset() == "AIMux-macOS-arm64.zip"


def test_update_worker_downloads_and_validates_release(monkeypatch, tmp_path) -> None:
    from app.ui.components import update_dialog

    data = b"installer-data"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(update_dialog, "project_version", lambda: "0.1.2")
    monkeypatch.setattr(update_dialog.platform, "system", lambda: "Windows")
    monkeypatch.setattr(update_dialog.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(update_dialog.tempfile, "gettempdir", lambda: str(tmp_path))

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "tag_name": "v0.1.3",
                "assets": [{
                    "name": "AIMux-Windows-x64.exe",
                    "size": len(data),
                    "digest": f"sha256:{digest}",
                    "browser_download_url": "https://example.test/AIMux.exe",
                }],
            }

        def iter_bytes(self, _size: int):
            yield data

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, _url):
            return Response()

        def stream(self, _method, _url):
            return Response()

    monkeypatch.setattr(update_dialog.httpx, "Client", Client)
    worker = update_dialog.UpdateWorker()
    result: list[tuple[str, str]] = []
    worker.finished_success.connect(lambda path, message: result.append((path, message)))
    worker.run()
    assert result and result[0][0].endswith("AIMux-Windows-x64.exe")
    assert (tmp_path / "AIMux-updates" / "AIMux-Windows-x64.exe").read_bytes() == data
