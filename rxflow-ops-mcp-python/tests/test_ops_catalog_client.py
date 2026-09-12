from rxflow_ops_mcp.ops_catalog_client import OpsCatalogClient


async def test_mock_mode_returns_canned_data_with_zero_http_calls(monkeypatch, httpx_mock):
    monkeypatch.setenv("OPS_CATALOG_MOCK", "true")
    client = OpsCatalogClient()

    owner = await client.get_service_owner("billing")
    runbook = await client.get_runbook("billing")
    health = await client.get_lab_health("lab-1")

    assert owner.service_name == "billing"
    assert runbook.service_name == "billing"
    assert health.lab_name == "lab-1"
    assert len(httpx_mock.get_requests()) == 0


async def test_real_mode_calls_http(monkeypatch, httpx_mock):
    monkeypatch.delenv("OPS_CATALOG_MOCK", raising=False)
    httpx_mock.add_response(
        url="https://ops.example.com/services/billing/owner",
        json={"service_name": "billing", "team": "payments", "on_call_contact": "a@b.com"},
    )
    client = OpsCatalogClient(base_url="https://ops.example.com")
    owner = await client.get_service_owner("billing")
    assert owner.team == "payments"
