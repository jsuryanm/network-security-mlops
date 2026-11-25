import boto3
import pytest
from moto import mock_aws

from app.cloud.s3_syncer import S3Sync
from app.exception.exceptions import NetworkSecurityException

BUCKET = "test-bucket"


@pytest.fixture
def syncer(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        client = boto3.client("s3")
        client.create_bucket(Bucket=BUCKET)
        yield S3Sync(client=client)


def make_tree(root):
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("aaa")
    (root / "sub" / "b.txt").write_text("bbbb")


def test_upload_then_skip_unchanged(syncer, tmp_path):
    make_tree(tmp_path / "src")
    assert syncer.sync_folder_to_s3(tmp_path / "src", BUCKET, "run/1") == 2
    keys = {o["Key"] for o in syncer.s3.list_objects_v2(Bucket=BUCKET)["Contents"]}
    assert keys == {"run/1/a.txt", "run/1/sub/b.txt"}
    assert syncer.sync_folder_to_s3(tmp_path / "src", BUCKET, "run/1") == 0  # nothing changed


def test_changed_file_is_reuploaded(syncer, tmp_path):
    make_tree(tmp_path / "src")
    syncer.sync_folder_to_s3(tmp_path / "src", BUCKET, "p")
    (tmp_path / "src" / "a.txt").write_text("longer content")
    assert syncer.sync_folder_to_s3(tmp_path / "src", BUCKET, "p") == 1


def test_roundtrip_download(syncer, tmp_path):
    make_tree(tmp_path / "src")
    syncer.sync_folder_to_s3(tmp_path / "src", BUCKET, "p")
    assert syncer.sync_folder_from_s3(tmp_path / "dst", BUCKET, "p") == 2
    assert (tmp_path / "dst" / "sub" / "b.txt").read_text() == "bbbb"
    assert syncer.sync_folder_from_s3(tmp_path / "dst", BUCKET, "p") == 0


def test_missing_folder_raises(syncer, tmp_path):
    with pytest.raises(NetworkSecurityException):
        syncer.sync_folder_to_s3(tmp_path / "nope", BUCKET, "p")


def test_missing_bucket_raises(syncer, tmp_path):
    make_tree(tmp_path / "src")
    with pytest.raises(NetworkSecurityException):
        syncer.sync_folder_to_s3(tmp_path / "src", "no-such-bucket", "p")


def test_unsafe_key_rejected(syncer, tmp_path):
    syncer.s3.put_object(Bucket=BUCKET, Key="p/../evil.txt", Body=b"x")
    with pytest.raises(NetworkSecurityException):
        syncer.sync_folder_from_s3(tmp_path / "dst", BUCKET, "p")
    assert not (tmp_path / "evil.txt").exists()
