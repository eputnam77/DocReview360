# DocReview360

DocReview360 helps you organise documents, run simple approval workflows and keep track of your projects. The prototype ships with a small web API, a tiny frontend and a one-command CLI wizard. It is intentionally lightweight so you can explore the features and decide how they fit your own process.

## Quick start

1. **Install the package and web server**
   ```bash
   pip install -e .
   pip install uvicorn
   ```
2. **Create a configuration file**
   ```bash
   docreview360 init
   ```
   The wizard asks for your preferred database, editor and other options then stores them in `docreview360.yml`.
3. **Start the backend API**
   ```bash
   uvicorn docreview360.api:app --reload
   ```
4. **Start the React frontend** (requires Node 18+)
   ```bash
   npm install --legacy-peer-deps --prefix frontend  # install dependencies
   npm run dev --prefix frontend
   ```
   If you see `Cannot find module 'critters'`, run the install command again to rebuild `node_modules`.
5. **Open <http://localhost:3000/>** and sign in with `admin/admin`.
   The projects page loads at port 3000 and fetches data from the API on port 8000.

### GitHub Codespaces

Run the commands above from your Codespace terminal. When `uvicorn` is running,
forward port 8000 in the **Ports** panel and choose **Open in Browser** to access the login page.

A demo token is available with:
```bash
curl -X POST -d "username=alice&password=password" http://127.0.0.1:8000/oidc/token
```
Use the token in the `Authorization` header to call `/oidc/me`.

The API is a learning tool. Endpoints return dummy data but illustrate how projects, documents and approvals could work together. The frontend contains a login page, dashboard, project creation form, two editor pages and a review tracker table.

## Features

- In-memory storage for projects and documents
- Import/export of Markdown and DOCX files
- Search with saved queries
- Simple plugin system for editors and exporters
- Minimal authentication flow with a login form, dashboard and project creation page

Head over to the [documentation](https://example.com/docreview360) for a full tour of the API, CLI options and UI navigation tips. The
[architecture overview](docs/adr/0001-core-architecture.md) describes how the backend, frontend and future services fit together.

## Usage example

The following short session shows how a new user might work with DocReview360. After
starting the server open a second terminal and run:

```bash
# create a project and upload a document
docreview360 project create "My first project"
docreview360 document add --project "My first project" README.md

# request approval from a team member
docreview360 approval request --project "My first project" --user bob

# export the document to PDF using the default plugin
docreview360 export pdf --project "My first project" --out build/project.pdf
```

Reload the projects page and you will see the document listed with its approval
status. The quick turnaround gives a fresh-doc scent that highlights how light
the workflow can be.

## Deploy with Docker

Running the app inside containers is a handy way to share it on a server or your favourite cloud provider. The repository already contains a `Dockerfile` and a `docker-compose.yml` so you can start quickly.

1. **Build the image**
   ```bash
   docker build -t docreview360:latest .
   ```
2. **Launch the container on its own**
   ```bash
   docker run -d -p 8000:8000 docreview360:latest
   ```
   Visit <http://localhost:8000/> to confirm everything works.
3. **Run the full stack**
   ```bash
   docker compose up
   ```
   This command starts Postgres, OpenSearch, Redis and the DocReview360 services.

If you need to deploy on a remote host, tag the image with your registry name and push it:

```bash
docker tag docreview360:latest registry.example.com/docreview360:1.0.0
docker push registry.example.com/docreview360:1.0.0
```

Update your server or container orchestration tool to pull the new image and your DocReview360 instance will be online.
