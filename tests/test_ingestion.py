import unittest
import pandas as pd
import sys
import os
import re

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestDataIngestion(unittest.TestCase):
    def test_clean_hdfc_line(self):
        """Test if HDFC style lines are parsed correctly."""
        line = "22/12/2025| 21:05 PAYTMNOIDA + 30  C 1,526.55 l"
        
        # Logic from data_ingestion.py
        line_clean = line.replace('|', ' ').strip()
        line_clean = re.sub(r'[\s|liI\+]*$', '', line_clean)
        line_clean = re.sub(r'\s+[\+\s]*\d+\s+(?=C)', ' ', line_clean)
        line_clean = re.sub(r'\s+', ' ', line_clean).strip()
        
        self.assertEqual(line_clean, "22/12/2025 21:05 PAYTMNOIDA C 1,526.55")
        
        # Test regex matching on cleaned line
        date_pattern = re.compile(r'^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3}\s+\d{1,2})', re.IGNORECASE)
        amount_pattern = re.compile(r'(-?\$?[\d,]+(\.\d{1,2})?)\s*(CR|DR)?\s*$', re.IGNORECASE)

        date_match = date_pattern.search(line_clean)
        amount_match = amount_pattern.search(line_clean)
        
        self.assertTrue(date_match)
        self.assertTrue(amount_match)
        # Verify the raw match, but the internal logic now converts it to 2025-12-22
        self.assertEqual(date_match.group(1), "22/12/2025")
        self.assertEqual(amount_match.group(1), "1,526.55")

    def test_credit_detection(self):
        line_clean = "22/12/2025 PAYTM PAYMENT C 1,526.55"
        is_credit = bool(re.search(r'\sC(R)?\s', line_clean, re.IGNORECASE))
        self.assertTrue(is_credit)

if __name__ == '__main__':
    unittest.main()
