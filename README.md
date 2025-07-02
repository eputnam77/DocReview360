# DocuFlow

DocuFlow is a document workflow management system. The current code base
includes a minimal FastAPI application and a small CLI tool.  It is not yet a
full product but you can start the prototype locally and experiment with the
login page and dashboard.

## Quick start

1. **Install the package**

   ```bash
   pip install -e .
   ```

2. **Run the configuration wizard** (optional)

   ```bash
   python -m docuflow.cli init
   ```

3. **Launch the development server**

   ```bash
   uvicorn docuflow.api:app --reload
   ```

4. **Open <http://127.0.0.1:8000/>** in your browser.

   Use username `admin` and password `admin` to sign in.  On successful login
   you will be redirected to the placeholder dashboard.

The API currently returns placeholder data and the CLI merely writes a YAML
file, but this provides a starting point for further development.
