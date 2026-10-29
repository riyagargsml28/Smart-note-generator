"""
Integration Tests for Flask API endpoints.
"""

import unittest
import json
import io
from app import app, db


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_config_status(self):
        res = self.client.get("/api/config-status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("active_llm_model", data)
        self.assertIn("detail_levels", data)

    def test_test_connection_endpoint(self):
        res = self.client.get("/api/test-connection")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("status", data)
        self.assertIn("configured", data)
        self.assertIn("model", data)

    def test_get_samples(self):
        res = self.client.get("/api/samples")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("samples", data)
        self.assertGreater(len(data["samples"]), 0)

    def test_upload_text_file(self):
        test_content = b"This is a lecture on algorithmic complexity and Big-O notation. O(n) is linear time."
        data = {
            "file": (io.BytesIO(test_content), "algorithms_lecture.txt")
        }
        res = self.client.post("/api/upload-file", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        resp_data = res.get_json()
        self.assertEqual(resp_data["filename"], "algorithms_lecture.txt")
        self.assertIn("algorithmic complexity", resp_data["text"])

    def test_generate_notes_pipeline(self):
        payload = {
            "transcript": (
                "Today we are discussing thermodynamics. "
                "The First Law of Thermodynamics states that energy cannot be created or destroyed. "
                "The equation is delta_U = Q - W. "
                "For example, heating a gas in a piston causes it to expand and do work. "
                "In conclusion, energy is strictly conserved."
            ),
            "subject": "Physics",
            "detail_level": "medium",
            "clean_fillers": True,
            "remove_timestamps": True
        }
        res = self.client.post(
            "/api/generate-notes",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("note_id", data)
        self.assertIn("structured_notes", data)
        self.assertEqual(data["subject"], "Physics")
        note_id = data["note_id"]

        # Test single note fetch
        fetch_res = self.client.get(f"/api/notes/{note_id}")
        self.assertEqual(fetch_res.status_code, 200)
        fetched = fetch_res.get_json()
        self.assertEqual(fetched["id"], note_id)

        # Test PDF export
        pdf_res = self.client.get(f"/api/notes/{note_id}/export?format=pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers["Content-Type"], "application/pdf")
        self.assertTrue(pdf_res.data.startswith(b"%PDF"))

        # Test Markdown export
        md_res = self.client.get(f"/api/notes/{note_id}/export?format=markdown")
        self.assertEqual(md_res.status_code, 200)
        self.assertIn("text/markdown", md_res.headers["Content-Type"])

        # Test note deletion
        del_res = self.client.delete(f"/api/notes/{note_id}")
        self.assertEqual(del_res.status_code, 200)

        # Verify 404 after deletion
        verify_res = self.client.get(f"/api/notes/{note_id}")
        self.assertEqual(verify_res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
