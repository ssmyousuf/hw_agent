import unittest
import json
import re
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAgentLogic(unittest.TestCase):
    def extract_tool_call(self, content):
        """The logic currently in agent.py but isolated for testing."""
        if '"name"' in content and '{' in content and '}' in content:
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]
            try:
                loaded = json.loads(json_str)
                if "name" in loaded:
                    return loaded
            except:
                pass
        return None

    def test_detect_raw_json(self):
        content = '{"name": "summarize_spending", "parameters": {"group_by": "category"}}'
        call = self.extract_tool_call(content)
        self.assertIsNotNone(call)
        self.assertEqual(call["name"], "summarize_spending")

    def test_detect_json_in_markdown(self):
        content = 'Certainly! Here is the summary: ```json\n{"name": "read_transactions", "parameters": {"category": "food"}}\n```'
        call = self.extract_tool_call(content)
        self.assertIsNotNone(call)
        self.assertEqual(call["name"], "read_transactions")
        
    def test_detect_json_with_parameters_key(self):
        content = '{"name": "read_transactions", "parameters": {"category": "food"}}'
        call = self.extract_tool_call(content)
        self.assertIsNotNone(call)
        self.assertEqual(call["parameters"]["category"], "food")

if __name__ == '__main__':
    unittest.main()
