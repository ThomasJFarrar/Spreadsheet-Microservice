"""
This module implements a basic RESTful API for interacting with a spreadsheet-like database.
It allows creating, reading, updating, and deleting cells, as well as listing all available cells.
"""

import json
import os
import re
import string
import sqlite3
import sys
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

if "-r" in sys.argv and "sqlite" in sys.argv:
    FIREBASE = False
elif "-r" in sys.argv and "firebase" in sys.argv:
    FIREBASE = True
else:
    print("Specify the database using the '-r' flag followed by either 'sqlite' or 'firebase'.")
    sys.exit(1)

# Firebase configuration
if FIREBASE:
    firebase_name = str(os.getenv('FBASE'))
    if not firebase_name:
        raise ValueError("Firebase db name url not provided in the environment variable FBASE")
    firebase_url = f"https://{firebase_name}-default-rtdb.europe-west1.firebasedatabase.app"
    firebase_api_url = f"{firebase_url}/cells"

@app.route('/cells/<string:cell_id>', methods=['PUT'])
def create_cell(cell_id):
    """
    Create or update a cell in the database with the provided ID and formula.
    """
    js = request.get_json()

    url_id = cell_id
    formula = js.get("formula")
    cell_id = js.get("id")

    # An id can be [A-Z][1-999]
    id_validation = r'^[A-Z]([1-9]\d{0,2}|[1-9]\d{0,2}|999)$'
    if len(js) != 2 or cell_id is None or cell_id != url_id \
       or re.match(id_validation, cell_id) is None:
        return "", 400 # Bad Request

    try:
        if FIREBASE:
            try:
                response = requests.get(f"{firebase_api_url}.json", timeout = 20)
                if cell_id in response.json().keys():
                    response = requests.put(f"{firebase_api_url}/{cell_id}.json",
                                            json = {"formula": formula}, timeout = 20)
                    return "", 204 # No Content
                response = requests.put(f"{firebase_api_url}/{cell_id}.json",
                                        json = {"formula": formula}, timeout = 20)
                return "", 201 # Created
            except:
                response = requests.put(f"{firebase_api_url}/{cell_id}.json", json = {"formula": formula}, timeout = 20)
                return "", 201 # Created
        # Check if a record already exists with the ID
        with sqlite3.connect("sc.db") as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id, formula FROM cells WHERE id=?",
                (cell_id,)
            )
            cell = cursor.fetchone()
            if cell:
                cursor.execute(
                    "UPDATE cells SET formula=? WHERE id=?",
                    (formula, cell_id)
                )
                connection.commit()
                cursor.close()
                return "", 204 # No Content
            cursor.execute(
                    "INSERT INTO cells (id, formula) VALUES (?, ?)",
                (cell_id, formula)
            )
            connection.commit()
            cursor.close()
            return "", 201 # Created
    except:
        return "", 500 # Internal Server Error

def validate_formula(formula):
    """
    Validates the given formula, checking for invalid characters, text and cells.
    """
    letters = string.ascii_uppercase
    numbers = "1234567890"
    valid_characters = set("()+-*/" + letters + numbers)

    formula = "".join(formula.split())  # Remove whitespace from formula

    # Iterate through the formula and check for invalid characters, and text and cells.
    for i, char in enumerate(formula):
        if char not in valid_characters:
            return False

        if char in letters:
            if i < len(formula) - 1 and formula[i + 1] not in numbers + letters:
                return False

        if char in numbers:
            if i < len(formula) - 1 and formula[i + 1] in letters:
                return False
    return True

def evaluate_formula(formula):
    """
    Evaluate the given formula recursively by substituting cell references with their values.
    """
    # Check if there are references in the formula
    references = re.findall(r'[A-Z]+\d+', formula)
    # Find reference values and replace in formula
    if references:
        for cell_id in references:
            try:
                if FIREBASE:
                    try:
                        response = requests.get(f"{firebase_api_url}/{cell_id}.json", timeout = 20)
                        cell = response.json()
                        referenced_formula = cell["formula"]
                    except:
                        referenced_formula = 0
                else:
                    with sqlite3.connect("sc.db") as connection:
                        cursor = connection.cursor()
                        cursor.execute(
                            "SELECT id, formula FROM cells WHERE id=?",
                            (cell_id,)
                        )
                        cell = cursor.fetchone()
                        if cell is None:
                            referenced_formula = 0
                        else:
                            referenced_formula = cell[1]
                # Recursively evaluate inner formula
                try:
                    inner_value = evaluate_formula(referenced_formula)
                except:
                    inner_value = "0"
                # Replace reference with evaluated value
                formula = formula.replace(cell_id, str(inner_value))
            except:
                return "", 500 # Internal Server Error
    # Evaluate the modified formula
    return eval(formula)

@app.route('/cells/<string:cell_id>', methods=['GET'])
def read_cell(cell_id):
    """
    Retrieve the evaluated formula of a cell.
    """
    try:
        if FIREBASE:
            try:
                try:
                    response = requests.get(f"{firebase_api_url}/{cell_id}.json", timeout = 20)
                except:
                    return "", 500 # Internal Server Error
                cell = response.json()
                formula = cell["formula"]
            except:
                return "", 404 # Not Found
        else:
            with sqlite3.connect("sc.db") as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT id, formula FROM cells WHERE id=?",
                    (cell_id,)
                )
                cell = cursor.fetchone()
                if cell:
                    formula = cell[1]
                else:
                    return "", 404 # Not Found
        if validate_formula(formula):
            try:
                result = evaluate_formula(formula)
            except:
                result = 0
        else:
            result = 0
        data = {"id":cell_id, "formula":str(result)}
        return json.dumps(data, separators=(',', ':')), 200 # OK
    except:
        return "", 500 # Internal Server Error

@app.route('/cells/<string:cell_id>', methods=['DELETE'])
def delete_cell(cell_id):
    """
    Delete a cell from the database.
    """
    if cell_id is None:
        return "", 404 # Not Found

    try:
        if FIREBASE:
            response = requests.delete(f"{firebase_api_url}/{cell_id}", timeout = 20)
            if response.status_code != 204:
                return "", 500 # Internal Server Error
        else:
            with sqlite3.connect("sc.db") as connection:
                cursor = connection.cursor()
            cursor.execute(
                    "DELETE FROM cells WHERE id=?",
                    (cell_id,)
                )
            connection.commit()
            return "", 204 # No Content
    except:
        return "", 500 # Internal Server Error

@app.route('/cells', methods=['GET'])
def list_cells():
    """
    Retrieve a list of all call IDs from the database.
    """
    try:
        if FIREBASE:
            response = requests.get(f"{firebase_api_url}.json", timeout = 20)
            if response.json():
                ids = list(response.json().keys())
            else:
                ids = []
        else:
            with sqlite3.connect("sc.db") as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT id FROM cells"
                )
                ids = [cell[0] for cell in cursor.fetchall()]
        return jsonify(ids), 200 # OK
    except:
        return "", 500 # Internal Server Error

def main():
    """
    Set up the SQLite database.
    """
    if not FIREBASE:
        try:
            with sqlite3.connect("sc.db") as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS cells" +
                    "(id TEXT PRIMARY KEY, formula TEXT)"
                )
                connection.commit()
        except:
            return "", 500

if __name__ == '__main__':
    main()
    app.run(port=3000)
