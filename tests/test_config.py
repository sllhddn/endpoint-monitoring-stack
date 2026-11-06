import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_targets as gt  # noqa: E402


def write(tmp_path, text):
    p = tmp_path / "t.csv"
    p.write_text(text)
    return p


def test_generates_file_sd(tmp_path):
    out = tmp_path / "t.json"
    assert gt.main(["--csv", str(ROOT / "targets.csv"), "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert len(data) == 6
    assert data[0]["targets"] == ["http://app-portal:8080/monitoring"]
    assert set(data[0]["labels"]) == {"env", "module", "node", "hostname"}


def test_rejects_duplicates_and_bad_urls(tmp_path):
    p = write(tmp_path, "env,module,node,hostname,url\n"
                        "prod,a,a1,h,http://x/m\nprod,a,a2,h,http://x/m\nprod,b,b1,h,ftp://y\n")
    with pytest.raises(ValueError) as e:
        gt.load(p)
    assert "duplicate" in str(e.value) and "http(s)" in str(e.value)


def test_rejects_missing_columns(tmp_path):
    with pytest.raises(ValueError):
        gt.load(write(tmp_path, "env,url\nprod,http://x\n"))


def test_committed_targets_json_is_in_sync():
    expected = gt.to_file_sd(gt.load(ROOT / "targets.csv"))
    assert json.loads((ROOT / "prometheus/targets/targets.json").read_text()) == expected


def test_dashboard_is_valid_and_uses_known_labels():
    d = json.loads((ROOT / "grafana/dashboards/app-monitoring-overview.json").read_text())
    ids = [p["id"] for p in d["panels"]]
    assert len(ids) == len(set(ids))
    exprs = [t["expr"] for p in d["panels"] for t in p.get("targets", [])]
    assert exprs and all('job="app_monitoring"' in e for e in exprs)
    # stat panels must not show "No data" when everything is up/down
    for p in d["panels"]:
        if p["type"] == "stat" and p["title"].startswith("Nodes"):
            assert "OR vector(0)" in p["targets"][0]["expr"]
