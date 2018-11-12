import pytest
import vcr
from pathlib import Path

current_path = Path(__file__).parent / 'cassetes'


@pytest.fixture
def codecov_vcr(request):
    current_name = request.node.nodeid.replace('.py', '').replace('()::', '').replace('::', '/')
    casset_file_path = str(current_path / f"{current_name}.yaml")
    with vcr.use_cassette(
            casset_file_path,
            filter_headers=['authorization'],
            match_on=['method', 'scheme', 'host', 'port', 'path']) as cassete_maker:
        yield cassete_maker
