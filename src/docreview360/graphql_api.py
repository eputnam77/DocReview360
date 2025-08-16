"""Simple GraphQL read layer for projects and documents."""

from __future__ import annotations

import graphene

from .config import CONFIG_FILE, Config
from .documents import list_documents
from .logs import log_event
from .search import list_projects
from .stubs import record_task_completion


class Document(graphene.ObjectType):
    """GraphQL type representing a document."""

    id = graphene.String(required=True)
    content = graphene.String(required=True)


class Project(graphene.ObjectType):
    """GraphQL type representing a project."""

    id = graphene.String(required=True)
    name = graphene.String(required=True)
    number = graphene.Int()


class Query(graphene.ObjectType):
    """Root query with read-only access to projects and documents."""

    projects = graphene.List(Project)
    documents = graphene.List(Document)

    def resolve_projects(self, info: object) -> list[Project]:
        return [Project(id=p.id, name=p.name, number=p.number) for p in list_projects()]

    def resolve_documents(self, info: object) -> list[Document]:
        return [Document(id=d.id, content=d.content) for d in list_documents()]


schema = graphene.Schema(query=Query)


def execute_query(query: str) -> dict[str, object]:
    """Execute a GraphQL ``query`` and return the resulting data."""
    record_task_completion(88)
    result = schema.execute(query)
    if result.errors:
        raise ValueError(str(result.errors[0]))
    data = result.data or {}
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="graphql", query=query, fields=list(data.keys()))
    return data
