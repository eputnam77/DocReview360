from docuflow.models import Base, DocumentType, Organization, Project, User
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_models_crud() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        org = Organization(name="ACME")
        user = User(username="alice", organization=org)
        dt = DocumentType(name="policy")
        project = Project(name="Test", document_type=dt)
        session.add_all([org, user, dt, project])
        session.commit()
        assert session.query(User).filter_by(username="alice").one()
        assert session.query(Project).count() == 1
