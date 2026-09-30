from model import paths


def test_data_dir_defaults_to_repo_data(monkeypatch):
    monkeypatch.delenv("DP_DATA_DIR", raising=False)
    assert paths.data_dir() == paths.REPO_ROOT / "data"


def test_data_dir_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DP_DATA_DIR", str(tmp_path))
    assert paths.data_dir() == tmp_path
    assert paths.testsets_dir() == tmp_path / "testsets"


def test_contracts_dir_is_in_repo():
    assert paths.CONTRACTS_DIR == paths.REPO_ROOT / "contracts"
