import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api import probe
from api.probe import base_url, image_payload
from stability.resources import safe_to_continue, safe_to_start


class HarnessUnitTests(unittest.TestCase):
    def test_url_accepts_base_and_existing_endpoint(self):
        self.assertEqual(base_url("http://127.0.0.1:8080/"), "http://127.0.0.1:8080")
        self.assertEqual(base_url("http://127.0.0.1:8080/layout-parsing"), "http://127.0.0.1:8080")

    def test_resource_thresholds(self):
        sample = {"mem_available_gib": 10, "psi_some_avg10": 0, "psi_full_avg10": 0}
        self.assertFalse(safe_to_start(sample))
        self.assertTrue(safe_to_continue(sample))
        sample["psi_some_avg10"] = 11
        self.assertFalse(safe_to_continue(sample))

    def test_fixture_payload(self):
        payload = image_payload(Path(__file__).parent / "fixtures/ocr-smoke.png")
        self.assertEqual(payload["fileType"], 1)
        self.assertFalse(payload["visualize"])
        self.assertGreater(len(payload["file"]), 100)

    def test_api_contract_accepts_variable_text(self):
        body = {"errorCode": 0, "result": {"layoutParsingResults": [
            {"prunedResult": {}, "markdown": {"text": "OCR output varies"}}]}}
        captured = []
        with patch.object(probe, "request_json", return_value=(200, body, 2.0)):
            result = probe.infer("http://127.0.0.1:8080", Path(__file__).parent / "fixtures/ocr-smoke.png",
                                 on_response=lambda *args: captured.append(args))
        self.assertEqual(result["pages"], 1)
        self.assertEqual(captured, [(200, body, 2.0)])

    def test_api_contract_rejects_empty_markdown(self):
        body = {"errorCode": 0, "result": {"layoutParsingResults": [
            {"prunedResult": {}, "markdown": {"text": "  "}}]}}
        with patch.object(probe, "request_json", return_value=(200, body, 2.0)):
            with self.assertRaises(AssertionError):
                probe.infer("http://127.0.0.1:8080", Path(__file__).parent / "fixtures/ocr-smoke.png")


if __name__ == "__main__":
    unittest.main()
