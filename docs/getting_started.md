# Getting Started

This short guide walks you through the first steps with DocuFlow. It assumes Python and Git are already installed.

## 1. Install DocuFlow

```bash
pip install -e .
```
This installs the package in editable mode so local changes are picked up immediately.

## 2. Configure the application

Run the interactive CLI wizard to generate a configuration file:
```bash
python -m docuflow.cli init
```
Answer the prompts about your preferred database, editor and other options. The resulting `docuflow.yml` sits in your working directory.

## 3. Start the development server

Launch the API and frontend with:
```bash
uvicorn docuflow.api:app --reload
```
Open `http://127.0.0.1:8000/` in your browser. Use the credentials `admin/admin` to sign in.

## 4. Explore the dashboard

After logging in you land on a very small dashboard. From here you can open the editor or browse the automatically generated API documentation. The editor does not save documents yet but demonstrates how future editing will look.

## 5. Next steps

Try importing a Markdown file, run a search query and create a dummy approval via the API. These simple examples show how projects, documents and approvals interact.
