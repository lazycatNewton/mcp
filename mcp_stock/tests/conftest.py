import pytest


@pytest.fixture
def mock_akshare(monkeypatch):
    """Mock AKShare responses for testing."""
    ...


@pytest.fixture
def sample_stock_data():
    """Return sample stock data matching AKShare output format."""
    return {
        "symbol": "000001",
        "name": "平安银行",
        "price": 10.50,
        "change": 0.15,
        "change_pct": 1.45,
        "volume": 50000000,
        "turnover": 525000000,
    }
