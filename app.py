# import required libraries for datetime parsing, regular expressions, and flask web framework
from datetime import datetime
import re
from flask import Flask, jsonify, request

# initialize the flask application instance
app = Flask(__name__)


def validate_required(value, field_name="field"):
    """User Story 1: reject records with missing required fields"""
    # check if value is missing or entirely blank whitespace
    if value is None or str(value).strip() == "":
        return False, [f"MISSING_REQUIRED_FIELD: {field_name}"]
    return True, ["VALID"]


def validate_numeric_range(value, min_val=0, max_val=100):
    """User Story 2: check if a numeric value is within a required range"""
    # attempt to parse the input value as a floating-point number
    try:
        num = float(value)
    except (ValueError, TypeError):
        return False, ["INVALID_NUMERIC_FORMAT"]

    # check if the parsed number falls within the specified minimum and maximum bounds
    if min_val <= num <= max_val:
        return True, ["VALID"]
    return False, [f"OUT_OF_RANGE: Expected between {min_val} and {max_val}"]


def validate_date(value):
    """User Story 3: validate date inputs strictly in YYYY-MM-DD format"""
    # ensure the input value is a string before processing
    if not isinstance(value, str):
        return False, ["INVALID_DATE_FORMAT: Expected YYYY-MM-DD"]

    # check strict format pattern first (rejects MM/DD/YYYY or single-digit month/day)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return False, ["INVALID_DATE_FORMAT: Required format is YYYY-MM-DD"]

    # check calendar validity (rejects dates like 2026-02-30)
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True, ["VALID"]
    except ValueError:
        return False, ["INVALID_CALENDAR_DATE: Date does not exist"]


# define the primary http post endpoint for all validation checks
@app.route("/validate", methods=["POST"])
def validate():
    # parse incoming json payload safely, returning none if parsing fails
    data = request.get_json(silent=True)

    # invalid json case
    if not data:
        return jsonify({
            "valid_boolean": False,
            "original_value": None,
            "codes": ["INVALID_JSON_PAYLOAD"],
        }), 400

    # MODE A: Multi-field Record Validation (User Story 1)
    # Expects: {"data_type": "record", "value": {"item name": ""}, "required_fields": ["item name"]}
    if data.get("data_type") == "record":
        record = data.get("value", {})
        required_fields = data.get("required_fields", [])

        # ensure the record value payload is formatted as a dictionary object
        if not isinstance(record, dict):
            return jsonify({
                "valid_boolean": False,
                "original_value": record,
                "codes": ["INVALID_RECORD_TYPE: 'value' must be a JSON object"],
            }), 400

        # iterate through required fields to check for missing or blank values
        missing_fields = []
        for field in required_fields:
            if field not in record or str(record[field]).strip() == "":
                missing_fields.append(field)

        # return validation failure if any required fields are missing
        if missing_fields:
            return jsonify({
                "valid_boolean": False,
                "original_value": record,
                "missing_fields": missing_fields,
                "codes": [f"MISSING_REQUIRED_FIELD: {f}" for f in missing_fields],
            }), 200

        # return validation success if all required fields are present and populated
        return jsonify({
            "valid_boolean": True,
            "original_value": record,
            "missing_fields": [],
            "codes": ["VALID"],
        }), 200

    # --- MODE B: Single-Field Validation (Matches Sections 6 & 7 Contract) ---
    # verify that both required protocol parameters are present in the request body
    if "data_type" not in data or "value" not in data:
        return jsonify({
            "valid_boolean": False,
            "original_value": data.get("value"),
            "codes": ["MISSING_PARAMETERS: 'data_type' and 'value' are required"],
        }), 400

    # extract and normalize the requested validation type and target value
    data_type = str(data["data_type"]).lower().strip()
    value = data["value"]

    # route the request to the appropriate specialized validation helper function
    if data_type in ("required", "name"):
        field_name = data.get("field_name", data_type)
        is_valid, codes = validate_required(value, field_name)
    elif data_type in ("number", "numeric", "range"):
        min_val = data.get("min", 0)
        max_val = data.get("max", 100)
        is_valid, codes = validate_numeric_range(value, min_val, max_val)
    elif data_type == "date":
        is_valid, codes = validate_date(value)
    else:
        # handle unsupported or unrecognized validation rule types
        return jsonify({
            "valid_boolean": False,
            "original_value": value,
            "codes": [f"UNSUPPORTED_DATA_TYPE: {data_type}"],
        }), 400

    # return the structured json response containing the validation outcome
    return jsonify({
        "valid_boolean": is_valid,
        "original_value": value,
        "codes": codes,
    }), 200


# start the flask development server on port 3000 with multi-threading enabled
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, threaded=True)
