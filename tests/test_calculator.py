import unittest

from app.tools.calculator import calculate


class TestCalculator(unittest.TestCase):

    def test_multiplication(self):
        result = calculate("300 * 12")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 3600)

    def test_addition(self):
        result = calculate("125 + 75")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 200)

    def test_expression_with_parentheses(self):
        result = calculate("(1250 - 950) * 12")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 3600)

    def test_division(self):
        result = calculate("20 / 4")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 5)

    def test_division_by_zero_is_rejected(self):
        result = calculate("10 / 0")
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])

    def test_arbitrary_code_is_rejected(self):
        result = calculate("__import__('os').system('echo unsafe')")
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])


if __name__ == "__main__":
    unittest.main()
