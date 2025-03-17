import orjson
import pytest
import zstandard as zstd

from shared.reports.carryforward import generate_carryforward_report
from shared.reports.resources import Report
from shared.torngit.base import TorngitBaseAdapter


def read_fixture(name: str) -> bytes:
    with open(name, "rb") as f:
        data = f.read()

    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)


def load_report() -> tuple[bytes, bytes]:
    raw_chunks = read_fixture("tests/benchmarks/fixtures/worker_chunks.txt.zst")
    raw_report_json = read_fixture("tests/benchmarks/fixtures/worker_report.json.zst")

    return raw_chunks, raw_report_json


def load_diff() -> dict:
    contents = read_fixture("tests/benchmarks/fixtures/worker.diff.zst").decode()

    torngit = TorngitBaseAdapter()
    return torngit.diff_to_json(contents)


def do_parse(raw_report_json, raw_chunks):
    report_json = orjson.loads(raw_report_json)
    chunks = raw_chunks.decode()
    return Report.from_chunks(
        chunks=chunks, files=report_json["files"], sessions=report_json["sessions"]
    )


def do_full_parse(raw_report_json, raw_chunks):
    report = do_parse(raw_report_json, raw_chunks)
    # full parsing in this case means iterating over everything in the report
    for file in report:
        # Which in particular means iterating over every `ReportLine`s,
        # which are unfortunately being re-parsed *every damn time* :-(
        for _line in file:
            pass

    return report


def test_parse_shallow(benchmark):
    raw_chunks, raw_report_json = load_report()

    def bench_fn():
        do_parse(raw_report_json, raw_chunks)

    benchmark(bench_fn)


def test_parse_full(benchmark):
    raw_chunks, raw_report_json = load_report()

    def bench_fn():
        do_full_parse(raw_report_json, raw_chunks)

    benchmark(bench_fn)


def test_process_totals(benchmark):
    raw_chunks, raw_report_json = load_report()

    report = do_full_parse(raw_report_json, raw_chunks)

    def bench_fn():
        # both `ReportFile` and `Report` have a cached `_totals` field,
        # and a `totals` accessor calculating the cache on-demand
        for file in report:
            file._totals = None
            _totals = file.totals

        report._totals = None
        _totals = report.totals

    benchmark(bench_fn)


def test_report_filtering(benchmark):
    raw_chunks, raw_report_json = load_report()

    report = do_full_parse(raw_report_json, raw_chunks)

    def bench_fn():
        filtered = report.filter(paths=[".*"], flags=["unit"])

        for filename in filtered.files:
            # contrary to the normal `Report`, `FilteredReport` does not have a `bind` parameter,
            # but instead always maintains a cache
            file = filtered.get(filename)

            # the `FilteredReportFile` has no `__iter__`, and all the other have no `.lines`.
            # what they do have in common is `eof` and `get`:
            for ln in range(1, file.eof):
                file.get(ln)

            file._totals = None
            _totals = file.totals

        filtered._totals = None
        _totals = filtered.totals

    benchmark(bench_fn)


@pytest.mark.parametrize(
    "do_filter",
    [pytest.param(False, id="Report"), pytest.param(True, id="FilteredReport")],
)
def test_report_diff_calculation(do_filter, benchmark):
    raw_chunks, raw_report_json = load_report()
    diff = load_diff()

    report = do_full_parse(raw_report_json, raw_chunks)
    if do_filter:
        report = report.filter(paths=[".*"], flags=["unit"])

    def bench_fn():
        report.apply_diff(diff)

    benchmark(bench_fn)


def test_report_serialize(benchmark):
    raw_chunks, raw_report_json = load_report()

    report = do_parse(raw_report_json, raw_chunks)

    def bench_fn():
        report.serialize()

    benchmark(bench_fn)


def test_report_merge(benchmark):
    raw_chunks, raw_report_json = load_report()

    report2 = do_full_parse(raw_report_json, raw_chunks)

    def bench_fn():
        report1 = do_parse(raw_report_json, raw_chunks)
        report1.merge(report2)

    benchmark(bench_fn)


def test_report_carryforward(benchmark):
    raw_chunks, raw_report_json = load_report()

    report = do_full_parse(raw_report_json, raw_chunks)

    def bench_fn():
        generate_carryforward_report(report, paths=[".*"], flags=["unit"])

    benchmark(bench_fn)
