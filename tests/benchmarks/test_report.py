import orjson
import pytest
import zstandard as zstd

from shared.reports.carryforward import generate_carryforward_report
from shared.reports.editable import EditableReport
from shared.reports.readonly import ReadOnlyReport
from shared.reports.resources import Report
from shared.torngit.base import TorngitBaseAdapter


def read_fixture(name: str) -> bytes:
    with open(name, "rb") as f:
        data = f.read()

    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)


READABLE_VARIANTS = [
    pytest.param(Report, False, id="Report"),
    pytest.param(ReadOnlyReport, False, id="ReadOnlyReport"),
    pytest.param(ReadOnlyReport, True, id="Rust ReadOnlyReport"),
    pytest.param(EditableReport, False, id="EditableReport"),
]

EDITABLE_VARIANTS = [Report, EditableReport]


def init_mocks(mocker, should_load_rust) -> tuple[bytes, bytes]:
    mocker.patch(
        "shared.reports.readonly.ReadOnlyReport.should_load_rust_version",
        return_value=should_load_rust,
    )

    raw_chunks = read_fixture("tests/benchmarks/fixtures/worker_chunks.txt.zst")
    raw_report_json = read_fixture("tests/benchmarks/fixtures/worker_report.json.zst")

    return raw_chunks, raw_report_json


def load_diff() -> dict:
    contents = read_fixture("tests/benchmarks/fixtures/worker.diff.zst").decode()

    torngit = TorngitBaseAdapter()
    return torngit.diff_to_json(contents)


def do_parse(report_class, raw_report_json, raw_chunks):
    report_json = orjson.loads(raw_report_json)
    chunks = raw_chunks.decode()
    return report_class.from_chunks(
        chunks=chunks, files=report_json["files"], sessions=report_json["sessions"]
    )


@pytest.mark.parametrize("report_class, should_load_rust", READABLE_VARIANTS)
def test_report_parsing(report_class, should_load_rust, mocker, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, should_load_rust)

    def bench_fn():
        do_parse(report_class, raw_report_json, raw_chunks)

    benchmark(bench_fn)


@pytest.mark.parametrize("report_class, should_load_rust", READABLE_VARIANTS)
def test_report_iterate_all(report_class, should_load_rust, mocker, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, should_load_rust)

    report = do_parse(report_class, raw_report_json, raw_chunks)

    def bench_fn():
        for file in report:
            for _line in file:
                pass

    benchmark(bench_fn)


@pytest.mark.parametrize("report_class, should_load_rust", READABLE_VARIANTS)
def test_report_process_totals(report_class, should_load_rust, mocker, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, should_load_rust)

    report = do_parse(report_class, raw_report_json, raw_chunks)

    def bench_fn():
        report._process_totals()
        for file in report:
            file._process_totals()

    benchmark(bench_fn)


@pytest.mark.parametrize("report_class, should_load_rust", READABLE_VARIANTS)
def test_report_filtering(report_class, should_load_rust, mocker, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, should_load_rust)

    report = do_parse(report_class, raw_report_json, raw_chunks)

    def bench_fn():
        filtered = report.filter(paths=[".*"], flags=["unit"])
        filtered._process_totals()
        for file in report:
            file._process_totals()
            # the `FilteredReportFile` has no `__iter__`, and all the other have no `.lines`.
            # what they do have in common is `eof` and `get`:
            for ln in range(1, file.eof):
                report.get(ln)

    benchmark(bench_fn)


@pytest.mark.parametrize(
    "do_filter",
    [pytest.param(False, id="Report"), pytest.param(True, id="FilteredReport")],
)
def test_report_diff_calculation(mocker, do_filter, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, False)
    diff = load_diff()

    report = do_parse(Report, raw_report_json, raw_chunks)
    if do_filter:
        report = report.filter(paths=[".*"], flags=["unit"])

    def bench_fn():
        report.apply_diff(diff)

    benchmark(bench_fn)


@pytest.mark.parametrize("report_class", EDITABLE_VARIANTS)
def test_report_serialize(report_class, mocker, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, False)

    report = do_parse(report_class, raw_report_json, raw_chunks)

    def bench_fn():
        report.to_database()
        report.to_archive()

    benchmark(bench_fn)


@pytest.mark.parametrize("report_class", EDITABLE_VARIANTS)
def test_report_merge(report_class, mocker, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, False)

    report1 = do_parse(report_class, raw_report_json, raw_chunks)
    report2 = do_parse(report_class, raw_report_json, raw_chunks)

    def bench_fn():
        report1.merge(report2)

    benchmark(bench_fn)


@pytest.mark.parametrize("report_class", EDITABLE_VARIANTS)
def test_report_carryforward(report_class, mocker, benchmark):
    raw_chunks, raw_report_json = init_mocks(mocker, False)

    report = do_parse(report_class, raw_report_json, raw_chunks)

    def bench_fn():
        generate_carryforward_report(report, paths=[".*"], flags=["unit"])

    benchmark(bench_fn)
