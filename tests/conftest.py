import pytest
from escondite import Cache


@pytest.fixture
def cache() -> Cache:
    return Cache()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "known_bug(reason): expected behaviour the package does not have yet")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for marker in item.iter_markers(name="known_bug"):
            item.add_marker(pytest.mark.xfail(reason=marker.args[0], strict=True))
