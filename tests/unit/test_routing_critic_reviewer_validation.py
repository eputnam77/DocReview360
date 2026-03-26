import pytest
from docreview360.ml.routing_critic import RoutingExample, train_routing_critic


def test_train_routing_critic_rejects_unknown_reviewer():
    example = RoutingExample(text="sample", reviewer="bob", approved=True)

    with pytest.raises(ValueError, match="unknown reviewer"):
        train_routing_critic(["alice"], [example], epochs=1)


def test_train_routing_critic_rejects_duplicate_reviewers():
    example = RoutingExample(text="sample", reviewer="alice", approved=True)

    with pytest.raises(ValueError, match="reviewers must be unique"):
        train_routing_critic(["alice", "alice"], [example], epochs=1)
