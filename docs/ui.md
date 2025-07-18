# Navigating the UI

The user interface contains a handful of simple pages that demonstrate the overall flow.

## Login

Visit `/` and sign in with the credentials you created in the configuration file (the defaults are `admin/admin`). If the details are wrong, an error message appears above the form.

## Projects page

After logging in you're redirected to the projects page. It lists your projects in a sortable table with a **Create New Project** button. Quick links to the editors, review tracker and dashboard remain available from the navigation.

## Create Project

The project creation page lets you submit a new project identifier and name. Once submitted you return to the projects page.

## Editor

The editor page loads a basic rich text control. You can type and format text but nothing is saved yet. The goal is to give a preview of how future document editing might feel.

## Document Editor

The `/doceditor` page showcases a richer editor powered by Tiptap. It opens in a modal dialog and lets you experiment with additional formatting options.

## Review Tracker

The review tracker page lists example documents along with progress bars and due dates. It demonstrates how a reviewer dashboard might appear in the finished product.

## Project Tracker

The project tracker lists all projects in a sortable table. Columns show the document number, title, assigned user, status and last update. Use the **Create New Project** button to open the wizard and the table refreshes once a project is saved.

## Project Details

Clicking a document number opens a details view with metadata and recent audit messages. From here you can launch the rich TipTap editor and upon saving you return to the project page automatically.

## Interactive Dashboard

The dashboard now reads data from `/metrics/summary` and `/api/audit`. A dropdown lets you filter audit messages by project so you can focus on recent activity. Counts for projects, documents and approvals update live.

## Global Search

A search bar appears at the top of the sidebar. Enter any term and press **Enter** to open the Search page. Queries run against all projects and documents so you can quickly find related content from anywhere in the interface.

Use your browser's back button or the navigation links to move between pages.
