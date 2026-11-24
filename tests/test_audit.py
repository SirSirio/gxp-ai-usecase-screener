import json


def test_chain_verifies(audit):
    for i in range(3):
        audit.append("assessment", {"request_id": f"r{i}", "verdict": "x"})
    assert audit.verify() == (True, None)
    assert audit.find("r1")[0]["verdict"] == "x"


def test_tampering_detected(audit):
    for i in range(3):
        audit.append("assessment", {"request_id": f"r{i}", "verdict": "annex22_full"})
    lines = audit.path.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[1])
    rec["verdict"] = "permitted_with_hitl"  # someone edits a past answer
    lines[1] = json.dumps(rec)
    audit.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert audit.verify() == (False, 2)


def test_deletion_detected(audit):
    for i in range(3):
        audit.append("assessment", {"request_id": f"r{i}"})
    lines = audit.path.read_text(encoding="utf-8").splitlines()
    audit.path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
    assert audit.verify() == (False, 2)


def test_parallel_requests_keep_the_chain(tmp_path):
    """W55: each request creates its own AuditLog; the lock is shared per file, so the chain stays intact."""
    import threading
    from app.audit import AuditLog

    path = tmp_path / "audit.jsonl"

    def write(n):
        for i in range(25):
            AuditLog(path).append("assessment", {"writer": n, "i": i})
    threads = [threading.Thread(target=write, args=(n,)) for n in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    ok, bad = AuditLog(path).verify()
    assert ok and not bad and len(path.read_text(encoding="utf-8").splitlines()) == 150
