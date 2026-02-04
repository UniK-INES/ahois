"""
Test runner utility for the unit tests.
This script serves as a wrapper for executing pytest on the Houseowner test suite. 
It is designed to resolve common path and import issues by automatically setting 
the working directory and Python path to the project root before execution. 
It allows users to run specific tests or groups of tests by providing a keyword argument.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""

import os
import sys
import pytest

# --- CONFIGURATION ---
TEST_FILE_NAME = "test_houseowner.py" 
# ---------------------

def main():
    # 1. Determine location
    script_location = os.path.abspath(__file__)
    tests_dir = os.path.dirname(script_location)
    project_root = os.path.dirname(tests_dir)

    # 2. Force CWD to Project Root
    os.chdir(project_root)

    # 3. Fix Imports
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    target_test_path = os.path.join("tests", TEST_FILE_NAME)

    # 4. Construct Pytest Arguments
    pytest_args = ["-v", target_test_path]

    # 5. Check for arguments
    # If an argument is provided (e.g. via command line), use it as a filter.
    # If NOT provided (e.g. clicking Run in Eclipse), run ALL tests.
    if len(sys.argv) >= 2:
        search_term = sys.argv[1]
        print(f"Context set to Project Root: {project_root}")
        print(f"Running tests matching: '{search_term}'")
        pytest_args.extend(["-k", search_term])
    else:
        print(f"Context set to Project Root: {project_root}")
        print(f"No keyword provided. Running ALL tests in {TEST_FILE_NAME}")

    print("-" * 40)

    # 6. Run Pytest
    pytest.main(pytest_args)

if __name__ == "__main__":
    main()