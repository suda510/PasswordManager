"""加密/解密模块

使用 AES-256-GCM 加密敏感字段，PBKDF2-HMAC-SHA256 派生密钥。

cryptography 的 import 延迟到函数内部，避免拖慢登录窗口弹出速度。
Python 会缓存已加载的模块，后续调用不会重复 import。
"""

import base64
import os
import secrets
import string


# 常量
SALT_LENGTH = 16  # 128-bit salt
NONCE_LENGTH = 12  # 96-bit nonce for GCM
KEY_LENGTH = 32  # 256-bit key
DEFAULT_ITERATIONS = 600_000  # OWASP 2023 推荐


def generate_salt() -> bytes:
    """生成随机盐值"""
    return os.urandom(SALT_LENGTH)


def derive_key(password: str, salt: bytes, iterations: int = DEFAULT_ITERATIONS) -> bytes:
    """从主密码派生 256-bit 加密密钥

    Args:
        password: 用户主密码
        salt: 盐值
        iterations: PBKDF2 迭代次数

    Returns:
        32 字节密钥
    """
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_field(key: bytes, plaintext: str) -> dict:
    """AES-GCM 加密单个字段

    Args:
        key: 256-bit 加密密钥
        plaintext: 明文字符串

    Returns:
        包含 nonce 和 ciphertext 的字典（base64 编码）
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(NONCE_LENGTH)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_field(key: bytes, nonce_b64: str, ciphertext_b64: str) -> str:
    """AES-GCM 解密单个字段

    Args:
        key: 256-bit 加密密钥
        nonce_b64: base64 编码的 nonce
        ciphertext_b64: base64 编码的密文

    Returns:
        解密后的明文字符串

    Raises:
        cryptography.exceptions.InvalidTag: 密钥错误或数据被篡改
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def derive_key_and_hash(password: str, salt: bytes, iterations: int = DEFAULT_ITERATIONS) -> tuple[bytes, str]:
    """一次 PBKDF2 同时返回加密密钥和验证哈希

    避免 login 时重复调用 derive_key + hash_master_password。

    Args:
        password: 用户主密码
        salt: 盐值
        iterations: PBKDF2 迭代次数

    Returns:
        (key, hash_b64) 元组
    """
    key = derive_key(password, salt, iterations)
    return key, base64.b64encode(key).decode("ascii")


def hash_master_password(password: str, salt: bytes, iterations: int = DEFAULT_ITERATIONS) -> str:
    """生成主密码验证哈希（不可逆）

    用于验证用户输入的主密码是否正确，不用于加密。

    Args:
        password: 用户主密码
        salt: 盐值
        iterations: PBKDF2 迭代次数

    Returns:
        base64 编码的哈希值
    """
    key = derive_key(password, salt, iterations)
    return base64.b64encode(key).decode("ascii")


def verify_master_password(password: str, salt: bytes, stored_hash: str, iterations: int = DEFAULT_ITERATIONS) -> bool:
    """验证主密码

    Args:
        password: 用户输入的密码
        salt: 存储的盐值
        stored_hash: 存储的验证哈希
        iterations: PBKDF2 迭代次数

    Returns:
        密码是否正确
    """
    computed_hash = hash_master_password(password, salt, iterations)
    # 使用常量时间比较，防止时序攻击
    import hmac
    return hmac.compare_digest(computed_hash, stored_hash)


# ---- 恢复密钥 ----

def generate_recovery_key() -> str:
    """生成恢复密钥

    格式: XXXX-XXXX-XXXX-XXXX（16 位随机字符，易读易输入）

    Returns:
        恢复密钥字符串
    """
    chars = string.ascii_uppercase + string.digits
    # 排除容易混淆的字符: 0/O, 1/I/L
    chars = chars.replace("O", "").replace("I", "").replace("L", "")
    segments = []
    for _ in range(4):
        segment = "".join(secrets.choice(chars) for _ in range(4))
        segments.append(segment)
    return "-".join(segments)


def hash_recovery_key(recovery_key: str, salt: bytes, iterations: int = DEFAULT_ITERATIONS) -> str:
    """生成恢复密钥的验证哈希

    Args:
        recovery_key: 恢复密钥
        salt: 盐值
        iterations: 迭代次数

    Returns:
        base64 编码的哈希值
    """
    return hash_master_password(recovery_key, salt, iterations)


def verify_recovery_key(recovery_key: str, salt: bytes, stored_hash: str, iterations: int = DEFAULT_ITERATIONS) -> bool:
    """验证恢复密钥

    Args:
        recovery_key: 用户输入的恢复密钥
        salt: 存储的盐值
        stored_hash: 存储的验证哈希
        iterations: 迭代次数

    Returns:
        恢复密钥是否正确
    """
    return verify_master_password(recovery_key, salt, stored_hash, iterations)
