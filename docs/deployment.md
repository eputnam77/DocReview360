# Deploying DocReview360

This quick note explains how to run the container on common free-tier platforms.
The image expects a `PORT` environment variable supplied by the host.

1. **Render** – add a Postgres database service and set `DATABASE_URL` to the
   connection string. The platform automatically provides `PORT`.
2. **Heroku** – provision a Postgres add-on and enable the `PORT` config
   variable. The app will bind to it without further changes.
3. **Fly.io** – create a Postgres instance with `fly postgres`. Define `DATABASE_URL`
   and `PORT` in the app configuration.
4. **Railway** – add a Postgres plugin and copy the `DATABASE_URL`. Railway
   injects `PORT` when the container starts.

The Dockerfile installs backend and frontend dependencies and builds the Next.js
UI so the resulting image can run on these providers with minimal setup.

## Installing Office add-ins

The Word editor relies on a DocReview360 Office add-in. Install the add-in in
every environment so the editor can connect to Word:

1. **Local development** – open Word, choose *Insert → Add-ins → Upload My
   Add-in* and select the DocReview360 manifest.
2. **Staging / production** – deploy the same manifest through your Microsoft 365
   admin centre or a SharePoint catalog so that all users receive the add-in.
3. **Office Online** – sideload the manifest from the browser's *Add-ins* menu or
   use centralised deployment.

After the add-in is installed, restart Word and the editor will load normally.

## Secret management

DocReview360 resolves service credentials through a simple vault interface. To
configure a vault, add a section to `settings.yaml`:

```yaml
vault:
  url: http://localhost:8200
  token: my-dev-token
```

When configured, provider modules such as the OpenAI and SharePoint clients pull
their tokens from the vault. If no vault is configured, the application falls
back to environment variables like `OPENAI_KEY` or `SHAREPOINT_TOKEN`.
