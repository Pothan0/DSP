import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from adapters.langchain import TrustChainAdapter
from adapters.openai import patch_openai

def test_langchain_adapter():
    assert hasattr(TrustChainAdapter, "__init__")

def test_patch_openai():
    assert callable(patch_openai)
