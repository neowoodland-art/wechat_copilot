import unittest
from unittest.mock import patch
from rpa.controller import get_ui_elements, analyze_ui_tree

class TestController(unittest.TestCase):

    @patch('rpa.controller.WeChatOperator')
    def test_get_ui_elements_success(self, MockOperator):
        mock_instance = MockOperator.return_value
        mock_instance.cpp_manager.get_ui_elements.return_value = [
            {"id": "button1", "type": "button", "text": "发送"},
            {"id": "input1", "type": "textbox", "text": ""}
        ]

        result = get_ui_elements()
        self.assertTrue(result['success'])
        self.assertEqual(len(result['elements']), 2)
        self.assertEqual(result['elements'][0]['id'], "button1")

    @patch('rpa.controller.WeChatOperator')
    def test_analyze_ui_tree_success(self, MockOperator):
        mock_instance = MockOperator.return_value
        mock_instance.cpp_manager.analyze_ui_tree.return_value = {
            "root": {
                "id": "root",
                "children": [
                    {"id": "child1", "type": "button"},
                    {"id": "child2", "type": "textbox"}
                ]
            }
        }

        result = analyze_ui_tree()
        self.assertTrue(result['success'])
        self.assertIn('root', result['analysis'])
        self.assertEqual(len(result['analysis']['root']['children']), 2)

    @patch('rpa.controller.WeChatOperator')
    def test_get_ui_elements_failure(self, MockOperator):
        mock_instance = MockOperator.return_value
        mock_instance.cpp_manager.get_ui_elements.side_effect = Exception("C++ 模块错误")

        result = get_ui_elements()
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @patch('rpa.controller.WeChatOperator')
    def test_analyze_ui_tree_failure(self, MockOperator):
        mock_instance = MockOperator.return_value
        mock_instance.cpp_manager.analyze_ui_tree.side_effect = Exception("C++ 模块错误")

        result = analyze_ui_tree()
        self.assertFalse(result['success'])
        self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main()