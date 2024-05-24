"""Test simple composable memory."""

from typing import Any, List
from llama_index.core.memory import (
    VectorMemory,
    SimpleComposableMemory,
    ChatMemoryBuffer,
)
from llama_index.core.embeddings.mock_embed_model import MockEmbedding
from unittest.mock import patch
from llama_index.core.llms import ChatMessage


def mock_get_text_embedding(text: str) -> List[float]:
    """Mock get text embedding."""
    # assume dimensions are 5
    if text == "Jerry likes juice.":
        return [1, 1, 0, 0, 0]
    elif text == "Bob likes burgers.":
        return [0, 1, 0, 1, 0]
    elif text == "Alice likes apples.":
        return [0, 0, 1, 0, 0]
    elif text == "What does Jerry like?":
        return [1, 1, 0, 0, 1]
    elif (
        text == "Jerry likes juice. That's nice."
    ):  # vector memory batches conversation turns starting with user
        return [1, 1, 0, 0, 1]
    else:
        raise ValueError("Invalid text for `mock_get_text_embedding`.")


def mock_get_text_embeddings(texts: List[str]) -> List[List[float]]:
    """Mock get text embeddings."""
    return [mock_get_text_embedding(text) for text in texts]


@patch.object(MockEmbedding, "_get_text_embedding", side_effect=mock_get_text_embedding)
@patch.object(
    MockEmbedding, "_get_text_embeddings", side_effect=mock_get_text_embeddings
)
def test_vector_memory(
    _mock_get_text_embeddings: Any, _mock_get_text_embedding: Any
) -> None:
    """Test vector memory."""
    # arrange
    composable_memory = SimpleComposableMemory.from_defaults(
        sources=[
            ChatMemoryBuffer.from_defaults(),
            VectorMemory.from_defaults(
                vector_store=None,
                embed_model=MockEmbedding(embed_dim=5),
                retriever_kwargs={"similarity_top_k": 1},
            ),
        ]
    )
    msgs = [
        ChatMessage.from_str("Jerry likes juice.", "user"),
        ChatMessage.from_str("That's nice.", "assistant"),
        ChatMessage.from_str("Bob likes burgers.", "user"),
        ChatMessage.from_str("Alice likes apples.", "user"),
    ]
    for m in msgs:
        composable_memory.put(m)

    # act
    retrieved_msgs = composable_memory.get("What does Jerry like?")

    # assert
    assert len(retrieved_msgs) == 5
    assert retrieved_msgs[0].role == "system"
    expected_system_string = """You are a helpful assistant.\n\nBelow are a set of relevant dialogues retrieved from potentially several memory sources:\n\n=====Relevant messages from memory source 1=====\n\n\tUSER: Jerry likes juice.\n\tASSISTANT: That's nice.\n\n=====End of relevant messages from memory source 1======\n\nThis is the end of the of retrieved message dialogues."""
    assert expected_system_string == retrieved_msgs[0].content

    assert retrieved_msgs[1:] == msgs
