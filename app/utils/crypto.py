from __future__ import annotations

import base64
import hashlib
import platform
import uuid

from cryptography.fernet import Fernet

def _fernet() -> Fernet:
    """由当前机器稳定信息派生 Fernet 密钥，不额外保存明文密钥文件。"""
    material = f"aimux:{platform.system()}:{platform.node()}:{uuid.getnode()}".encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def encrypt_api_key(api_key: str) -> bytes:
    """加密上游 API Key，供数据库以 BLOB 形式保存。"""
    return _fernet().encrypt(api_key.encode("utf-8"))


def decrypt_api_key(ciphertext: bytes) -> str:
    """仅在向上游发起请求前解密 API Key。"""
    return _fernet().decrypt(ciphertext).decode("utf-8")
