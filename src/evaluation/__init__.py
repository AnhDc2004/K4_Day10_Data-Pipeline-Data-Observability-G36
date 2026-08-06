from .metrics import EvaluationBundle, JudgeVerdict, evaluate_pipeline
from .testset import build_test_set, verify_test_set_against_index

import sys
import types

if "langchain_community.chat_models.vertexai" not in sys.modules:
    shim = types.ModuleType("langchain_community.chat_models.vertexai")
    shim.ChatVertexAI = type("ChatVertexAI", (), {})
    sys.modules["langchain_community.chat_models.vertexai"] = shim

from .metrics import EvaluationBundle, JudgeVerdict, evaluate_pipeline

__all__ = ["EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"]