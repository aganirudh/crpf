import os, sys
sys.path.insert(0, os.path.abspath('.'))
from pramaan.config import Settings
s = Settings()
print(f"is_mock_llm = {s.is_mock_llm}")
print(f"llm_api_key = {s.llm_api_key[:20]}... (len={len(s.llm_api_key)})")
print(f"llm_base_url = {s.llm_base_url}")
print(f"llm_extractor_model = {s.llm_extractor_model}")
