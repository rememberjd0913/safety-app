"""NHN Object Storage persistence for one Streamlit deployment.

Files are stored separately by SHA-256. SQLite contains only metadata and file
references; committed changes are uploaded before the app reports success.
All connections in this Python process share a lock. Do not run a second app
deployment against the same bucket/prefix/database files.
"""

from __future__ import annotations

import base64
import hashlib
import io
import sqlite3
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path


PHOTO_REF = "nhn-object-v1:"
BLOB_REF = b"KECO-NHN-BLOB-V1:"
ENDPOINTS = {
    "KR1": "https://kr1-api-object-storage.nhncloudservice.com",
    "KR2": "https://kr2-api-object-storage.nhncloudservice.com",
    "KR3": "https://kr3-api-object-storage.nhncloudservice.com",
    "JP1": "https://jp1-api-object-storage.nhncloudservice.com",
}
_COORDINATORS = {}
_COORDINATORS_LOCK = threading.RLock()


class StorageError(RuntimeError):
    """A storage failure with a user-safe message."""


def _error_code(exc):
    response = getattr(exc, "response", {})
    return str(response.get("Error", {}).get("Code", ""))


def _file_type(raw):
    if raw.startswith(b"%PDF-"):
        return "pdf", "application/pdf"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return "webp", "image/webp"
    if raw.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "hwp", "application/x-hwp"
    if raw.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = set(archive.namelist())
                if "Contents/section0.xml" in names:
                    return "hwpx", "application/vnd.hancom.hwpx"
                if "word/document.xml" in names:
                    return "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except zipfile.BadZipFile:
            pass
    return "bin", "application/octet-stream"


class NhnObjectStorage:
    def __init__(self, *, region, bucket, access_key="", secret_key="",
                 prefix="safety-app/v1", client=None):
        region = str(region).strip().upper()
        if region not in ENDPOINTS:
            raise StorageError("저장소 리전을 확인해 주세요. 판교 KR1, 평촌 KR2, 광주 KR3, 도쿄 JP1입니다.")
        bucket = str(bucket).strip()
        if not bucket or "/" in bucket or "\\" in bucket:
            raise StorageError("저장소 컨테이너 이름을 확인해 주세요.")
        prefix = str(prefix).strip("/")
        if not prefix or any(part in (".", "..", "") for part in prefix.split("/")):
            raise StorageError("저장소 prefix 설정을 확인해 주세요.")
        self.region = region
        self.bucket = bucket
        self.prefix = prefix
        self.endpoint = ENDPOINTS[region]
        if client is None:
            if not str(access_key).strip() or not str(secret_key).strip():
                raise StorageError("Streamlit Secrets에 NHN 접근 키와 비밀 키를 입력해 주세요.")
            try:
                import boto3
                from botocore.config import Config
            except ImportError:
                raise StorageError("requirements.txt에 boto3가 필요합니다. 수정 파일을 함께 적용해 주세요.") from None
            client = boto3.client(
                "s3", region_name=region, endpoint_url=self.endpoint,
                aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                    connect_timeout=10, read_timeout=60,
                    retries={"mode": "standard", "max_attempts": 2},
                    request_checksum_calculation="when_required",
                    response_checksum_validation="when_required",
                ),
            )
        self.client = client
        self._uploaded = set()
        self._files_lock = threading.RLock()

    def _full_key(self, key):
        key = str(key)
        if key.startswith("/") or any(part in (".", "..", "") for part in key.split("/")):
            raise StorageError("저장할 파일 경로를 확인해 주세요.")
        return self.prefix + "/" + key

    def read(self, key, *, missing_ok=False):
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._full_key(key))
            body = response["Body"]
            try:
                return body.read()
            finally:
                body.close()
        except Exception as exc:
            if missing_ok and _error_code(exc) in ("NoSuchKey", "NotFound", "404"):
                return None
            if isinstance(exc, StorageError):
                raise
            raise StorageError("저장소에서 파일을 읽지 못했습니다. 리전·키·접근 권한과 인터넷 연결을 확인해 주세요.") from None

    def write(self, key, raw, content_type="application/octet-stream"):
        raw = bytes(raw)
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=self._full_key(key), Body=raw,
                ContentType=content_type,
            )
        except Exception:
            # A timeout may occur after the server accepted the PUT. A verified
            # read resolves that ambiguity without another write.
            try:
                if self.read(key, missing_ok=True) == raw:
                    return
            except StorageError:
                pass
            raise StorageError("저장소 저장 결과를 확인하지 못했습니다. 저장 완료로 처리하지 않았습니다. 연결을 확인해 주세요.") from None

    def save_bytes(self, raw, *, category="files"):
        raw = bytes(raw)
        if not raw:
            raise StorageError("빈 파일은 저장할 수 없습니다.")
        ext, mime = _file_type(raw)
        digest = hashlib.sha256(raw).hexdigest()
        key = f"{category}/{digest}.{ext}"
        with self._files_lock:
            if key not in self._uploaded:
                self.write(key, raw, mime)
                self._uploaded.add(key)
        return key

    def photo_pack(self, raw):
        return PHOTO_REF + self.save_bytes(raw, category="images")

    def photo_bytes(self, value):
        if isinstance(value, str) and value.startswith(PHOTO_REF):
            key = value[len(PHOTO_REF):]
            if not key.startswith("images/"):
                raise StorageError("사진 저장 경로를 확인해 주세요.")
            raw = self.read(key)
            if hashlib.sha256(raw).hexdigest() != Path(key).stem:
                raise StorageError("저장한 사진의 무결성을 확인하지 못했습니다.")
            return raw
        return base64.b64decode(value, validate=True)

    def _pack_parameter(self, value):
        if isinstance(value, (bytes, bytearray, memoryview)):
            raw = bytes(value)
            # SQL reads and writes remain transparent to the existing app.
            if not raw:
                return raw
            return BLOB_REF + self.save_bytes(raw).encode("ascii")
        return value

    def _restore_blob(self, value):
        if isinstance(value, bytes) and value.startswith(BLOB_REF):
            key = value[len(BLOB_REF):].decode("ascii")
            if not key.startswith("files/"):
                raise StorageError("문서 저장 경로를 확인해 주세요.")
            raw = self.read(key)
            if hashlib.sha256(raw).hexdigest() != Path(key).stem:
                raise StorageError("저장한 문서의 무결성을 확인하지 못했습니다.")
            return raw
        return value

    def connect(self, filename):
        if Path(filename).name != filename or not filename.endswith(".sqlite3"):
            raise StorageError("기록 저장 파일명을 확인해 주세요.")
        identity = (self.endpoint, self.bucket, self.prefix, filename)
        with _COORDINATORS_LOCK:
            coordinator = _COORDINATORS.get(identity)
            if coordinator is None:
                coordinator = _Coordinator(self, filename)
                _COORDINATORS[identity] = coordinator
        return _Connection(coordinator, self)

    def check_connection(self):
        key = "connection-tests/" + uuid.uuid4().hex + ".txt"
        value = b"safety-app storage connection test"
        self.write(key, value, "text/plain")
        if self.read(key) != value:
            raise StorageError("저장소 읽기·쓰기 확인에 실패했습니다.")
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._full_key(key))
        except Exception:
            return "저장·조회 성공. 임시 연결 확인 파일은 저장소에 남아 있습니다."
        return "저장소 연결 성공: 사진과 보고서를 저장하고 다시 읽을 수 있습니다."


class _Coordinator:
    def __init__(self, store, filename):
        self.store = store
        self.key = "metadata/" + filename
        self.lock = threading.RLock()
        self.folder = Path(tempfile.mkdtemp(prefix="keco-nhn-"))
        self.path = self.folder / filename
        self.synced = None
        self.ready = False
        self.blocked = False

    def prepare(self, store):
        if self.blocked:
            raise StorageError("저장 결과 확인이 필요해 추가 저장을 중단했습니다. 앱을 재시작한 뒤 기록을 확인해 주세요.")
        if self.ready:
            return
        raw = store.read(self.key, missing_ok=True)
        if raw is not None:
            if not raw.startswith(b"SQLite format 3\x00"):
                raise StorageError("저장된 기록 파일의 형식을 확인하지 못했습니다.")
            self.path.write_bytes(raw)
        self.synced = raw
        self.ready = True


class _Cursor(sqlite3.Cursor):
    def execute(self, sql, parameters=()):
        store = self.connection._store
        if isinstance(parameters, dict):
            parameters = {key: store._pack_parameter(value) for key, value in parameters.items()}
        else:
            parameters = tuple(store._pack_parameter(value) for value in parameters)
        return super().execute(sql, parameters)

    def executemany(self, sql, parameters):
        return super().executemany(sql, [tuple(self.connection._store._pack_parameter(v) for v in row) for row in parameters])

    def _restore(self, row):
        if row is None:
            return None
        values = tuple(self.connection._store._restore_blob(value) for value in row)
        return sqlite3.Row(self, values) if isinstance(row, sqlite3.Row) else values

    def fetchone(self):
        return self._restore(super().fetchone())

    def fetchmany(self, size=None):
        rows = super().fetchmany() if size is None else super().fetchmany(size)
        return [self._restore(row) for row in rows]

    def fetchall(self):
        return [self._restore(row) for row in super().fetchall()]

    def __iter__(self):
        return self

    def __next__(self):
        return self._restore(super().__next__())


class _Connection(sqlite3.Connection):
    def __init__(self, coordinator, store):
        self._coordinator = coordinator
        self._store = store
        self._closed = False
        coordinator.lock.acquire()
        try:
            coordinator.prepare(store)
            super().__init__(str(coordinator.path), timeout=30)
            self.execute("PRAGMA journal_mode=DELETE")
            check = self.execute("PRAGMA quick_check").fetchone()
            if not check or check[0] != "ok":
                raise StorageError("저장된 점검 기록의 무결성을 확인하지 못했습니다.")
        except Exception:
            try:
                super().close()
            except Exception:
                pass
            self._closed = True
            coordinator.lock.release()
            raise

    def cursor(self, factory=None):
        return super().cursor(factory or _Cursor)

    def execute(self, sql, parameters=()):
        return self.cursor().execute(sql, parameters)

    def executemany(self, sql, parameters):
        return self.cursor().executemany(sql, parameters)

    def _sync(self):
        coordinator = self._coordinator
        if coordinator.blocked:
            raise StorageError("저장소 결과 확인이 필요합니다. 앱을 재시작해 주세요.")
        try:
            raw = self.serialize()
        except sqlite3.OperationalError:
            # A new connection with no tables has no serialized database yet.
            return
        if raw == coordinator.synced:
            return
        previous = coordinator.synced
        try:
            self._store.write(coordinator.key, raw, "application/vnd.sqlite3")
            coordinator.synced = raw
        except StorageError:
            # An upload failure must not leave a locally successful write that
            # another user could see or that a later commit might upload.
            try:
                remote = self._store.read(coordinator.key, missing_ok=True)
                if remote == raw:
                    coordinator.synced = raw
                    return
                if remote != previous:
                    coordinator.blocked = True
                if remote is not None:
                    self.deserialize(remote)
                    self.backup_to_local()
                    coordinator.synced = remote
                else:
                    coordinator.blocked = True
            except Exception:
                coordinator.blocked = True
            raise

    def backup_to_local(self):
        target = sqlite3.connect(str(self._coordinator.path))
        try:
            self.backup(target)
        finally:
            target.close()

    def commit(self):
        super().commit()
        self._sync()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
        else:
            super().rollback()
        return False

    def close(self):
        if self._closed:
            return
        try:
            if self.in_transaction:
                super().rollback()
            if not self._coordinator.blocked:
                self._sync()
        finally:
            super().close()
            self._closed = True
            self._coordinator.lock.release()


def legacy_photo_bytes(value):
    """Decode pre-migration photo records without configuring cloud storage."""
    if isinstance(value, str) and value.startswith(PHOTO_REF):
        raise StorageError("이 사진을 읽으려면 NHN 저장소 설정이 필요합니다.")
    return base64.b64decode(value, validate=True)
