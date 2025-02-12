import typing as t

# import httpx
import pytest

# from app.api.endpoints.overlap import scope_restriction
# from main import get_app
#
#
# @pytest.fixture
# async def async_client() -> t.AsyncIterator[httpx.AsyncClient]:
#    # Set up auth router for test purposes.
#    app = get_app()
#    # No auth testing
#    app.dependency_overrides[scope_restriction] = lambda: True
#
#    async with httpx.AsyncClient(app=app, base_url="http://test/api/overlap") as client:
#        yield client


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--regenerate", action="store_true", help="Regenerate the .expected files")


@pytest.fixture(scope="session")
def regenerate(pytestconfig: pytest.Config) -> bool:
    return t.cast(bool, pytestconfig.getoption("regenerate"))
