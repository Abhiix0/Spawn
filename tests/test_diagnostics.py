"""Contract, isolation, and containment tests for internal diagnostics."""

import os
import subprocess
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from spawn.diagnostics import service
from spawn.diagnostics.models import (
    Coverage,
    DiagnosticsReport,
    Evidence,
    IssueDescription,
    Outcome,
    Reason,
    ReportStatus,
    RepositoryIdentity,
    RepositoryIssue,
    RuleOutcome,
    Severity,
)
from spawn.diagnostics.rules import Rule, WorkLimits
from spawn.diagnostics.serialization import (
    ReportDecodeError,
    from_dict,
    from_json,
    to_dict,
    to_json,
)
from spawn.inspection import _reading
from spawn.inspection.exceptions import InspectionError
from spawn.inspection.models import Diagnostic

_ID = RepositoryIdentity("a" * 64)
_DESCRIPTION = IssueDescription(
    "empty-setting",
    Severity.WARNING,
    "Empty setting",
    "The setting is empty.",
    "Set it to a supported value.",
)
_MARKER = Evidence("config.ini", key="project.setting")


def _issue(evidence=_MARKER, *, rule_id="config", description=_DESCRIPTION):
    return RepositoryIssue(rule_id, "configuration", description, (evidence,))


def _outcome(rule_id, outcome, reason, **kwargs):
    return RuleOutcome(rule_id, "configuration", outcome, reason, **kwargs)


def _rule(rule_id, check, **kwargs):
    return Rule(rule_id, "configuration", check, **kwargs)


def _pass(rule_id="config"):
    return _outcome(rule_id, Outcome.PASS, Reason.CONDITION_ABSENT)


def _find(*issues):
    return _outcome(
        issues[0].rule_id, Outcome.FINDING, Reason.CONDITION_PROVED, findings=issues
    )


@pytest.mark.parametrize(
    ("outcomes", "coverage", "status", "clean"),
    [
        ((), Coverage.COMPLETE, ReportStatus.COMPLETE, False),
        ((_pass(),), Coverage.COMPLETE, ReportStatus.COMPLETE, True),
        ((_find(_issue()),), Coverage.COMPLETE, ReportStatus.COMPLETE, False),
        (
            (
                _outcome(
                    "x",
                    Outcome.NOT_APPLICABLE,
                    Reason.OUTSIDE_SCOPE,
                    scope_evidence=(_MARKER,),
                ),
            ),
            Coverage.COMPLETE,
            ReportStatus.COMPLETE,
            False,
        ),
        (
            (_outcome("x", Outcome.UNKNOWN, Reason.SCOPE_UNCLEAR),),
            Coverage.COMPLETE,
            ReportStatus.PARTIAL,
            False,
        ),
        (
            (_outcome("x", Outcome.NOT_CHECKED, Reason.CHECK_SKIPPED),),
            Coverage.COMPLETE,
            ReportStatus.PARTIAL,
            False,
        ),
        (
            (_outcome("x", Outcome.FAILED, Reason.RULE_CRASHED),),
            Coverage.COMPLETE,
            ReportStatus.PARTIAL,
            False,
        ),
        ((_pass(),), Coverage.INVENTORY_INCOMPLETE, ReportStatus.PARTIAL, False),
        ((), Coverage.DISCOVERY_FAILED, ReportStatus.FAILED, False),
    ],
)
def test_status_and_counts(outcomes, coverage, status, clean):
    report = DiagnosticsReport(_ID, coverage, outcomes)
    assert report.status is status
    assert report.is_clean is clean
    assert sum(report.outcome_counts.values()) == len(outcomes)
    assert report.outcome_counts[Outcome.PASS] == sum(
        o.outcome is Outcome.PASS for o in outcomes
    )
    assert sum(report.severity_counts.values()) == len(report.findings)
    assert from_json(to_json(report)) == report


@pytest.mark.parametrize(
    ("outcome", "reason", "kwargs"),
    [
        (Outcome.PASS, Reason.CONDITION_PROVED, {}),
        (Outcome.PASS, Reason.CONDITION_ABSENT, {"findings": (_issue(),)}),
        ("pass", Reason.CONDITION_ABSENT, {}),
        (Outcome.UNKNOWN, "scope_unclear", {}),
        (Outcome.FINDING, Reason.CONDITION_PROVED, {}),
        (
            Outcome.FINDING,
            Reason.CONDITION_PROVED,
            {"findings": (_issue(rule_id="other"),)},
        ),
        (
            Outcome.FINDING,
            Reason.CONDITION_PROVED,
            {
                "findings": (
                    _issue(),
                    _issue(
                        description=replace(_DESCRIPTION, title="Conflicting title")
                    ),
                )
            },
        ),
        (Outcome.NOT_APPLICABLE, Reason.OUTSIDE_SCOPE, {}),
        (Outcome.UNKNOWN, Reason.SCOPE_UNCLEAR, {"scope_evidence": (_MARKER,)}),
    ],
)
def test_reject_inconsistent_outcomes(outcome, reason, kwargs):
    with pytest.raises(ValueError):
        _outcome("config", outcome, reason, **kwargs)


@pytest.mark.parametrize(
    "value", ["", "Mixed", "two words", "-rule", "rule..test", "../a"]
)
def test_require_stable_ids(value):
    with pytest.raises(ValueError):
        _pass(value)


@pytest.mark.parametrize(
    "value",
    [
        "/etc/passwd",
        "../data",
        "src/../data",
        "C:/data",
        "a\\b",
        "a//b",
        "file.txt:stream",
        "aux.txt",
        "dir./data",
        "src/[red].py",
        "data\x1b.txt",
        "data\u202e.txt",
        "bad\udcff.txt",
        "<x>",
        ".env.example",
        ".ssh/config",
        "config/credentials.json",
        "cert.pem",
        "ghp_abcdefghijklmnopqrstuvwxyz.txt",
    ],
)
def test_reject_unsafe_evidence_paths(value):
    with pytest.raises(ValueError, match="Unsafe diagnostics evidence path"):
        Evidence(value)


@pytest.mark.parametrize(
    "kwargs",
    [{"line": True}, {"line": -1}, {"line": 1, "key": "setting"}, {"key": "key=value"}],
)
def test_validate_location_selectors(kwargs):
    with pytest.raises(ValueError):
        Evidence("config.ini", **kwargs)


@pytest.mark.parametrize(
    "title",
    [
        "[red]text",
        "<tag>",
        "bad\x00",
        "bad\udcff",
        "password=private-canary",
        "https://user:pass@example.org",
    ],
)
def test_unsafe_text_rejected_without_echo(title):
    with pytest.raises(ValueError) as exc:
        replace(_DESCRIPTION, title=title)
    assert title not in str(exc.value)
    with pytest.raises(ValueError):
        replace(_DESCRIPTION, severity="warning")


def test_require_evidence_and_unique_rule_outcomes():
    with pytest.raises(ValueError):
        replace(_issue(), evidence=())
    with pytest.raises(ValueError, match="Duplicate rule"):
        DiagnosticsReport(_ID, Coverage.COMPLETE, (_pass(), _pass()))
    with pytest.raises(ValueError):
        DiagnosticsReport(_ID, Coverage.DISCOVERY_FAILED, (_pass(),))


def test_order_dedup_and_utf8_roundtrip():
    earlier = _issue(Evidence("données.ini", line=2))
    later = _issue(Evidence("données.ini", line=11))
    critical = _issue(
        Evidence("z.ini"),
        rule_id="z",
        description=replace(_DESCRIPTION, severity=Severity.ERROR),
    )
    outcome = _find(later, earlier, later)
    report = DiagnosticsReport(_ID, Coverage.COMPLETE, (_find(critical), outcome))
    second = DiagnosticsReport(
        _ID, Coverage.COMPLETE, (_find(earlier, later), _find(critical))
    )
    assert outcome.findings == (earlier, later)
    assert report.findings == (critical, earlier, later)
    assert len({issue.occurrence_id for issue in report.findings}) == 3
    assert report.severity_counts == {
        Severity.ERROR: 1,
        Severity.WARNING: 2,
        Severity.INFO: 0,
    }
    assert to_json(report) == to_json(second)
    assert "données.ini" in to_json(report)
    assert from_json(to_json(report).encode("utf-8")) == report
    assert from_dict(to_dict(report)) == report


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.pop("schema_version"),
        lambda data: data.update(schema_version="1.1"),
        lambda data: data.update(schema_version="2.0"),
        lambda data: data.update(status="partial"),
        lambda data: data.update(is_clean=0),
        lambda data: data["repository"].update(root="/private"),
        lambda data: data["outcome_counts"].update(finding=True),
        lambda data: data["outcomes"][0].update(reason="private-canary"),
        lambda data: data["outcomes"][0]["findings"][0].update(occurrence_id="invalid"),
        lambda data: data["outcomes"][0]["findings"][0].update(
            title="secret=private-canary"
        ),
    ],
)
def test_decode_rejects_inconsistent_or_unknown_fields(mutate):
    data = to_dict(DiagnosticsReport(_ID, Coverage.COMPLETE, (_find(_issue()),)))
    mutate(data)
    with pytest.raises(ReportDecodeError) as exc:
        from_dict(data)
    assert "private-canary" not in str(exc.value)


@pytest.mark.parametrize(
    "payload", [b"\xff", '{"status": "failed", "status": "complete"}', "{"]
)
def test_reject_invalid_json(payload):
    with pytest.raises(ReportDecodeError):
        from_json(payload)


def test_one_inventory_one_inspection_one_context_and_shared_cache(
    tmp_path, monkeypatch
):
    (tmp_path / "app.py").write_text("import flask\n", encoding="utf-8")
    (tmp_path / "config.ini").touch()
    calls = []
    actual_discover, actual_inspect = (
        service.discover_repository,
        service._inspect_inventory,
    )
    actual_context, actual_read = service.repository_reads, _reading._read_from_root
    inventory = None
    opened = []

    def discover(*args, **kwargs):
        nonlocal inventory
        calls.append("discover")
        inventory = actual_discover(*args, **kwargs)
        return inventory

    @contextmanager
    def reader(*args, **kwargs):
        calls.append("enter")
        with actual_context(*args, **kwargs):
            yield
        calls.append("exit")

    def inspect(target, discovered, analyzers):
        calls.append("inspect")
        assert discovered is inventory
        assert _reading._ACTIVE_READS.get() is not None
        return actual_inspect(target, discovered, analyzers)

    def read(handle, parts, limit):
        opened.append(parts)
        return actual_read(handle, parts, limit)

    def check(context):
        calls.append("rule")
        assert _reading._ACTIVE_READS.get() is not None
        assert context.read_text("app.py").replace("\r\n", "\n") == ("import flask\n")
        return _find(_issue())

    monkeypatch.setattr(service, "discover_repository", discover)
    monkeypatch.setattr(service, "_inspect_inventory", inspect)
    monkeypatch.setattr(service, "repository_reads", reader)
    monkeypatch.setattr(_reading, "_read_from_root", read)
    report = service._run(
        tmp_path,
        (
            _rule(
                "config",
                check,
                descriptions=(_DESCRIPTION,),
                evidence_keys=(_MARKER.key,),
            ),
        ),
    )
    assert report.status is ReportStatus.COMPLETE
    assert report.findings == (_issue(),)
    assert calls == ["discover", "enter", "inspect", "rule", "exit"]
    assert opened.count(("app.py",)) == 1


def test_rule_crashes_and_malformed_returns_are_isolated(tmp_path, capsys):
    def crash(context):
        raise RuntimeError("token=private-canary [bold]")

    def succeed(context):
        assert context.inventory_covers("config.ini")
        return _pass("z")

    report = service._run(
        tmp_path,
        (
            _rule("z", succeed),
            _rule("a", crash),
            _rule("b", lambda ctx: {"secret": "private-canary"}),
            _rule("c", lambda ctx: _pass("z")),
        ),
    )
    assert report.status is ReportStatus.PARTIAL
    assert [result.reason for result in report.outcomes] == [
        Reason.RULE_CRASHED,
        Reason.INVALID_RESULT,
        Reason.INVALID_RESULT,
        Reason.CONDITION_ABSENT,
    ]
    assert "private-canary" not in repr(report) + to_json(report)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("case", ["unknown-file", "unowned-description", "unowned-key"])
def test_rule_evidence_and_text_require_provenance(tmp_path, case):
    if case != "unknown-file":
        (tmp_path / "config.ini").touch()
    issue = (
        _issue(description=replace(_DESCRIPTION, problem="A private canary value."))
        if case == "unowned-description"
        else _issue()
    )
    rule = _rule(
        "config",
        lambda ctx: _find(issue),
        descriptions=(_DESCRIPTION,),
        evidence_keys=() if case == "unowned-key" else (_MARKER.key,),
    )
    report = service._run(tmp_path, (rule,))
    assert report.outcomes[0].reason is Reason.INVALID_RESULT
    assert not report.findings
    assert "private canary" not in repr(report) + to_json(report)


@pytest.mark.parametrize("content", [None, b"\xff", b"oversized"])
def test_incomplete_reads_abstain(tmp_path, content):
    if content is not None:
        (tmp_path / "config.ini").write_bytes(content)

    def check(context):
        assert context.read_text("config.ini", limit=3) is None
        return _pass()

    report = service._run(tmp_path, (_rule("config", check),))
    assert report.status is ReportStatus.PARTIAL
    assert report.outcomes[0].reason is Reason.EVIDENCE_MISSING
    assert report.outcome_counts[Outcome.PASS] == 0


def test_absence_requires_coverage_of_relevant_inventory(tmp_path, monkeypatch):
    discover = service.discover_repository

    def incomplete(*args, **kwargs):
        inventory = discover(*args, **kwargs)
        gap = Diagnostic(
            "discovery.filesystem_error",
            "private-canary",
            "warning",
            "discovery",
            "nested",
        )
        return replace(inventory, diagnostics=(gap,))

    def check_gap(context):
        assert not context.inventory_covers("nested/config.ini")
        return _pass("gap")

    def good(context):
        assert context.inventory_covers("config.ini")
        return _pass("good")

    monkeypatch.setattr(service, "discover_repository", incomplete)
    report = service._run(
        tmp_path,
        (
            _rule("gap", check_gap),
            _rule("good", good),
            _rule("unchecked", lambda ctx: _pass("unchecked")),
        ),
    )
    assert report.coverage is Coverage.INVENTORY_INCOMPLETE
    assert [item.reason for item in report.outcomes] == [
        Reason.COVERAGE_INCOMPLETE,
        Reason.CONDITION_ABSENT,
        Reason.EVIDENCE_MISSING,
    ]
    assert "private-canary" not in repr(report) + to_json(report)


@pytest.mark.parametrize("budget", ["files", "bytes", "work"])
@pytest.mark.parametrize("aggregate", [False, True])
def test_rule_and_aggregate_limits(tmp_path, budget, aggregate):
    (tmp_path / "config.ini").write_bytes(b"abc")
    limited = replace(WorkLimits(20, 100, 100), **{budget: 1})

    def expensive(context):
        context.read_text("config.ini", limit=4)
        context.read_text("config.ini", limit=4)
        return _pass("a")

    rule = _rule("a", expensive) if aggregate else _rule("a", expensive, limits=limited)
    kwargs = {"limits": limited} if aggregate else {}
    report = service._run(
        tmp_path,
        (
            rule,
            _rule(
                "z", lambda ctx: _outcome("z", Outcome.UNKNOWN, Reason.SCOPE_UNCLEAR)
            ),
        ),
        **kwargs,
    )
    assert report.status is ReportStatus.PARTIAL
    assert report.outcomes[0].reason is Reason.LIMIT_REACHED
    assert report.outcomes[1].outcome is (
        Outcome.NOT_CHECKED if aggregate else Outcome.UNKNOWN
    )


def test_discovery_limit_and_invalid_root(tmp_path):
    assert (
        service.run_diagnostics(tmp_path / "missing").coverage
        is Coverage.ROOT_UNAVAILABLE
    )
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "app.py").touch()
    rule = _rule("config", lambda ctx: pytest.fail("No rules should run"))
    report = service._run(tmp_path, (rule,), max_entries=1)
    assert report.coverage is Coverage.LIMIT_REACHED
    assert report.status is ReportStatus.PARTIAL
    assert report.outcomes[0].outcome is Outcome.NOT_CHECKED
    assert service._run(tmp_path, (), max_entries=2).coverage is Coverage.COMPLETE
    with pytest.raises(ValueError, match="Duplicate diagnostics rule"):
        service._run(tmp_path, (rule, rule))


def test_fatal_discovery_suppresses_raw_error(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise InspectionError("private-canary")

    monkeypatch.setattr(service, "discover_repository", fail)
    report = service.run_diagnostics(tmp_path)
    assert report.coverage is Coverage.DISCOVERY_FAILED
    assert report.status is ReportStatus.FAILED
    assert not report.outcomes
    assert "private-canary" not in repr(report) + to_json(report)


def test_screening_and_read_only_analysis(tmp_path, monkeypatch):
    root = tmp_path / "private-canary"
    root.mkdir()
    (root / ".env.py").write_text("private-canary", encoding="utf-8")
    (root / "credentials.py").write_text("private-canary", encoding="utf-8")
    (root / "[red].py").write_text("private-canary", encoding="utf-8")
    (root / "app.py").write_text(
        "raise RuntimeError('private-canary')\n", encoding="utf-8"
    )
    actual_read = _reading._read_from_root

    def fail(*args, **kwargs):
        pytest.fail("Unexpected unsafe operation")

    def read(handle, parts, limit):
        assert parts == ("app.py",)
        return actual_read(handle, parts, limit)

    def check(context):
        assert context.files == ("app.py",)
        assert context.read_text(".env.py") is None
        assert context.read_text("../app.py") is None
        return _pass()

    monkeypatch.setattr(subprocess, "Popen", fail)
    monkeypatch.setattr(Path, "read_text", fail)
    monkeypatch.setattr(Path, "write_text", fail)
    monkeypatch.setattr(_reading, "_read_from_root", read)
    report = service._run(root, (_rule("config", check),))
    assert report.coverage is Coverage.INVENTORY_INCOMPLETE
    assert report.outcomes[0].outcome is Outcome.UNKNOWN
    assert "private-canary" not in repr(report) + to_json(report)
    assert "[red]" not in repr(report) + to_json(report)


def test_link_swap_after_discovery_is_incomplete(tmp_path, monkeypatch):
    root, outside = tmp_path / "repo", tmp_path / "outside"
    child = root / "nested"
    child.mkdir(parents=True)
    outside.mkdir()
    (child / "config.ini").touch()
    (outside / "config.ini").write_text("private-canary", encoding="utf-8")
    discover = service.discover_repository

    def swap(*args, **kwargs):
        inventory = discover(*args, **kwargs)
        child.rename(tmp_path / "moved")
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(child), str(outside)],
                capture_output=True,
                check=False,
            )
            if result.returncode or not child.is_junction():
                pytest.skip("Creating Windows junctions is unavailable")
        else:
            child.symlink_to(outside, target_is_directory=True)
        return inventory

    def check(context):
        assert context.read_text("nested/config.ini") is None
        return _pass()

    monkeypatch.setattr(service, "discover_repository", swap)
    report = service._run(root, (_rule("config", check),))
    assert report.outcomes[0].reason is Reason.EVIDENCE_MISSING
    assert "private-canary" not in repr(report) + to_json(report)
