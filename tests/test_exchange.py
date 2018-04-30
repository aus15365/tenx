import unittest

from tenx.exchange import ExchangeOpimiser, ExchangeRateError

class TestExchangeOpimiser(unittest.TestCase):
    """Test the class ExchangeOpimiser
    """
    def setUp(self):
        """Set up for testing."""

        print(self.id())

        td = ExchangeOpimiser("Sydney Exchange")

    def tearDown(self):
        """Tear down after testing"""
        pass

    def test_constructor(self):
        """Test the constructor of the class ExchangeOpimiser"""
        pass

    def test_verify_price_update_request(self):
        """Test the verify_price_update_request method"""
        pass

    def test_price_update(self):
        """Test the price_update method"""
        pass

    def test_add_new_currency_id(self):
        """Test _add_new_currency_id method"""
        pass

    def test_find_path(self):
        """Test _find_path method"""
        pass

    def test_print_path(self):
        """Test _print_path method"""
        pass
    
    def test_latest_rate_table(self):
        """Test _latest_rate_table method"""
        pass

    def test_verify_best_price_request(self):
        """Test _verify_best_price_request method"""
        pass
    
    def test_best_rate(self):
        ""'Test best_rate method"""
        pass
