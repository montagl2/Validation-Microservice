import time
import unittest
import requests

BASE_URL = "http://127.0.0.1:3000/validate"


class TestValidationMicroservice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure the Flask server is running before executing tests."""
        try:
            # Using a supported date rule for the server connection check
            response = requests.post(
                BASE_URL,
                json={"data_type": "date", "value": "2026-11-15"},
                timeout=2,
            )
            if response.status_code != 200:
                raise RuntimeError("Server returned non-200 status.")
        except Exception as e:
            raise RuntimeError(
                f"\n[ERROR] Could not connect to validation microservice at {BASE_URL}.\n"
                "Please make sure you have started your Flask server by running 'python app.py' in another terminal window first!\n"
            ) from e

    #Helper function for displaying data
    def send(self, payload):
        """send a request to the microservice and print the data sent and received"""
        print(f"\n  REQUEST SENT:      {payload}")
        response = requests.post(BASE_URL, json=payload)
        res = response.json()
        print(f"  RESPONSE RECEIVED: HTTP {response.status_code} {res}")
        return res

    # USER STORY 1: Required Fields Validation
    def test_us1_missing_required_field(self):
        """test that a record with a blank required field is rejected"""
        payload = {
            "data_type": "record",
            "required_fields": ["item name"],
            "value": {"item name": ""},
        }
        res = self.send(payload)

        self.assertFalse(res["valid_boolean"])
        self.assertIn("item name", res["missing_fields"])
        self.assertTrue(any("MISSING_REQUIRED_FIELD" in code for code in res["codes"]))

    def test_us1_valid_required_field(self):
        """test that a record with a populated required field is accepted"""
        payload = {
            "data_type": "record",
            "required_fields": ["item name"],
            "value": {"item name": "Example"},
        }
        res = self.send(payload)

        self.assertTrue(res["valid_boolean"])
        self.assertEqual(res["missing_fields"], [])
        self.assertIn("VALID", res["codes"])

    # USER STORY 2: Numeric Range Validation
    def test_us2_numeric_range_valid(self):
        """test a numeric value within the allowed range (0 to 100)"""
        payload = {"data_type": "numeric", "value": 75, "min": 0, "max": 100}
        res = self.send(payload)

        self.assertTrue(res["valid_boolean"])
        self.assertIn("VALID", res["codes"])

    def test_us2_numeric_range_out_of_bounds_high(self):
        """test a numeric value above the allowed range"""
        payload = {"data_type": "numeric", "value": 120, "min": 0, "max": 100}
        res = self.send(payload)

        self.assertFalse(res["valid_boolean"])
        self.assertTrue(any("OUT_OF_RANGE" in code for code in res["codes"]))

    def test_us2_numeric_range_out_of_bounds_low(self):
        """test a numeric value below the allowed range"""
        payload = {"data_type": "numeric", "value": -5, "min": 0, "max": 100}
        res = self.send(payload)

        self.assertFalse(res["valid_boolean"])
        self.assertTrue(any("OUT_OF_RANGE" in code for code in res["codes"]))

    def test_us2_numeric_invalid_format(self):
        """test handling of non-numeric string input"""
        payload = {"data_type": "numeric", "value": "not-a-number"}
        res = self.send(payload)

        self.assertFalse(res["valid_boolean"])
        self.assertIn("INVALID_NUMERIC_FORMAT", res["codes"])

    # USER STORY 3: Date Validation
    def test_us3_date_valid(self):
        """test a valid date string in strict YYYY-MM-DD format"""
        payload = {"data_type": "date", "value": "2026-11-15"}
        res = self.send(payload)

        self.assertTrue(res["valid_boolean"])
        self.assertIn("VALID", res["codes"])

    def test_us3_date_invalid_calendar_date(self):
        """test an invalid calendar date (e.g., February 30th)"""
        payload = {"data_type": "date", "value": "2026-02-30"}
        res = self.send(payload)

        self.assertFalse(res["valid_boolean"])
        self.assertTrue(any("INVALID_CALENDAR_DATE" in code for code in res["codes"]))

    def test_us3_date_invalid_format(self):
        """test a date entered in the wrong format (MM/DD/YYYY)"""
        payload = {"data_type": "date", "value": "11/15/2026"}
        res = self.send(payload)

        self.assertFalse(res["valid_boolean"])
        self.assertTrue(any("INVALID_DATE_FORMAT" in code for code in res["codes"]))

    # error handling
    def test_error_missing_parameters(self):
        """test that requests lacking required parameters return an error"""
        payload = {"data_type": "date"}  # missing 'value'
        res = self.send(payload)

        self.assertFalse(res["valid_boolean"])
        self.assertTrue(any("MISSING_PARAMETERS" in code for code in res["codes"]))

    # NON-FUNCTIONAL REQUIREMENT (NFR) PERFORMANCE
    def test_nfr_performance_100_requests(self):
        """performance NFR: 100 sequential requests must complete in under 1 second."""
        session = requests.Session()
        # ask the server not to print these 100 requests
        session.headers["X-Quiet"] = "1"
        sample_record = {f"field_{i}": f"value_{i}" for i in range(20)}
        payload = {
            "data_type": "record",
            "required_fields": ["field_0", "field_19"],
            "value": sample_record,
        }

        start_time = time.perf_counter()
        success_count = 0
        for _ in range(100):
            r = session.post(BASE_URL, json=payload)
            if r.status_code == 200 and r.json().get("valid_boolean") is True:
                success_count += 1
        elapsed = time.perf_counter() - start_time

        print(f"\n  PERFORMANCE: {success_count}/100 requests passed in {elapsed:.4f} seconds (limit is 1.0s)")

        self.assertEqual(success_count, 100)
        self.assertLess(
            elapsed, 1.0, f"Performance NFR failed: took {elapsed:.4f} seconds (limit is 1.0s)"
        )


if __name__ == "__main__":
    unittest.main()