from pathlib import Path

import pytest

import openioc

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def v10_minimal_path() -> Path:
    return FIXTURES / "v10" / "minimal.ioc"


@pytest.fixture
def v10_full_path() -> Path:
    return FIXTURES / "v10" / "full.ioc"


@pytest.fixture
def v10_malformed_path() -> Path:
    return FIXTURES / "v10" / "malformed.ioc"


@pytest.fixture
def v11_minimal_path() -> Path:
    return FIXTURES / "v11" / "minimal.ioc"


@pytest.fixture
def v11_full_path() -> Path:
    return FIXTURES / "v11" / "full.ioc"


@pytest.fixture
def v11_malformed_path() -> Path:
    return FIXTURES / "v11" / "malformed.ioc"


@pytest.fixture
def v10_minimal_ioc(v10_minimal_path) -> openioc.IOC:
    return openioc.read(v10_minimal_path)


@pytest.fixture
def v10_full_ioc(v10_full_path) -> openioc.IOC:
    return openioc.read(v10_full_path)


@pytest.fixture
def v11_minimal_ioc(v11_minimal_path) -> openioc.IOC:
    return openioc.read(v11_minimal_path)


@pytest.fixture
def v11_full_ioc(v11_full_path) -> openioc.IOC:
    return openioc.read(v11_full_path)


@pytest.fixture
def simple_ioc() -> openioc.IOC:
    """Minimal programmatically-built v1.1 IOC."""
    import uuid

    return openioc.IOC(
        id=str(uuid.uuid4()),
        metadata=openioc.Metadata(
            short_description="Simple IOC",
            authored_by="pytest",
            authored_date="2024-01-01T00:00:00",
        ),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[
                openioc.IndicatorItem(
                    id=str(uuid.uuid4()),
                    context=openioc.Context(document="FileItem", search="FileItem/FileName"),
                    content=openioc.Content(value="evil.exe"),
                    condition="is",
                )
            ],
        ),
        last_modified="2024-01-01T00:00:00",
        published_date="2024-01-01T00:00:00",
        format_version="1.1",
    )
