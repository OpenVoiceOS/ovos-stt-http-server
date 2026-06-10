# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the UTCP manual endpoint."""
import pytest
from fastapi.testclient import TestClient

from ovos_stt_http_server.routers.utcp import build_utcp_manual, make_utcp_router


# ---------------------------------------------------------------------------
# Unit tests for build_utcp_manual()
# ---------------------------------------------------------------------------

class TestBuildUtcpManual:
    BASE = "http://localhost:8080"

    def setup_method(self):
        self.manual = build_utcp_manual(self.BASE)

    def test_top_level_keys(self):
        assert "utcp_version" in self.manual
        assert "manual_version" in self.manual
        assert "tools" in self.manual

    def test_utcp_version_is_string(self):
        assert isinstance(self.manual["utcp_version"], str)
        assert self.manual["utcp_version"]

    def test_manual_version_is_string(self):
        assert isinstance(self.manual["manual_version"], str)

    def test_tools_is_list(self):
        assert isinstance(self.manual["tools"], list)

    def test_three_tools_registered(self):
        """Expect stt, lang_detect, status."""
        names = {t["name"] for t in self.manual["tools"]}
        assert names == {"stt", "lang_detect", "status"}

    def test_stt_tool_structure(self):
        stt = next(t for t in self.manual["tools"] if t["name"] == "stt")
        assert "description" in stt
        assert "inputs" in stt
        assert "outputs" in stt
        assert "tool_call_template" in stt

    def test_stt_tool_call_template_url(self):
        stt = next(t for t in self.manual["tools"] if t["name"] == "stt")
        assert stt["tool_call_template"]["url"] == f"{self.BASE}/stt"
        assert stt["tool_call_template"]["method"] == "POST"

    def test_lang_detect_tool_call_template_url(self):
        ld = next(t for t in self.manual["tools"] if t["name"] == "lang_detect")
        assert ld["tool_call_template"]["url"] == f"{self.BASE}/lang_detect"

    def test_status_tool_call_template_url(self):
        st = next(t for t in self.manual["tools"] if t["name"] == "status")
        assert st["tool_call_template"]["url"] == f"{self.BASE}/status"
        assert st["tool_call_template"]["method"] == "GET"

    def test_stt_inputs_has_body_field(self):
        stt = next(t for t in self.manual["tools"] if t["name"] == "stt")
        assert "body" in stt["inputs"]["properties"]
        assert "body" in stt["inputs"]["required"]

    def test_lang_detect_inputs_requires_valid_langs(self):
        ld = next(t for t in self.manual["tools"] if t["name"] == "lang_detect")
        assert "valid_langs" in ld["inputs"]["required"]

    def test_trailing_slash_stripped(self):
        """base_url with trailing slash must produce clean URLs."""
        manual = build_utcp_manual(self.BASE + "/")
        stt = next(t for t in manual["tools"] if t["name"] == "stt")
        assert not stt["tool_call_template"]["url"].endswith("//stt")

    def test_all_tools_have_tags(self):
        for tool in self.manual["tools"]:
            assert isinstance(tool.get("tags"), list)
            assert len(tool["tags"]) > 0

    def test_all_tools_have_average_response_size(self):
        for tool in self.manual["tools"]:
            assert isinstance(tool.get("average_response_size"), int)
            assert tool["average_response_size"] > 0

    def test_auth_none_on_all_tools(self):
        for tool in self.manual["tools"]:
            assert tool["tool_call_template"]["auth"] == {"type": "none"}


# ---------------------------------------------------------------------------
# Integration test: GET /utcp via TestClient
# ---------------------------------------------------------------------------

class TestUtcpEndpoint:
    """Mount only the UTCP router on a bare FastAPI app and test the endpoint."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(make_utcp_router())
        self.client = TestClient(app)

    def test_get_utcp_returns_200(self):
        resp = self.client.get("/utcp")
        assert resp.status_code == 200

    def test_get_utcp_content_type_json(self):
        resp = self.client.get("/utcp")
        assert "application/json" in resp.headers["content-type"]

    def test_get_utcp_body_has_tools(self):
        data = self.client.get("/utcp").json()
        assert "tools" in data
        assert len(data["tools"]) == 3

    def test_get_utcp_tool_names(self):
        data = self.client.get("/utcp").json()
        names = {t["name"] for t in data["tools"]}
        assert names == {"stt", "lang_detect", "status"}

    def test_get_utcp_base_url_inferred(self):
        """URLs in the manual must use the request base URL."""
        data = self.client.get("/utcp").json()
        stt = next(t for t in data["tools"] if t["name"] == "stt")
        # TestClient uses http://testserver by default
        assert "testserver" in stt["tool_call_template"]["url"]

    def test_get_utcp_version_fields_present(self):
        data = self.client.get("/utcp").json()
        assert "utcp_version" in data
        assert "manual_version" in data
