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
