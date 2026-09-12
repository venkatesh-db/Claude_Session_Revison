from rxflow_ops_mcp.azure_devops_client import AzureDevOpsClient


def _client() -> AzureDevOpsClient:
    return AzureDevOpsClient(organization="myorg", project="RxFlow", pat="fake-pat")


async def test_get_work_item(httpx_mock):
    httpx_mock.add_response(
        url="https://dev.azure.com/myorg/RxFlow/_apis/wit/workitems/42?api-version=7.1",
        json={"id": 42, "fields": {"System.Title": "Hello"}},
    )
    result = await _client().get_work_item(42)
    assert result["id"] == 42


async def test_search_uses_org_level_batch_endpoint(httpx_mock):
    httpx_mock.add_response(
        url="https://dev.azure.com/myorg/RxFlow/_apis/wit/wiql?api-version=7.1",
        json={"workItems": [{"id": 1, "url": "x"}, {"id": 2, "url": "y"}]},
    )
    httpx_mock.add_response(
        url="https://dev.azure.com/myorg/_apis/wit/workitemsbatch?api-version=7.1",
        json={"value": [{"id": 1}, {"id": 2}]},
    )
    result = await _client().search_work_items("SELECT [System.Id] FROM WorkItems")
    assert [w["id"] for w in result] == [1, 2]


async def test_create_work_item_uses_json_patch(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://dev.azure.com/myorg/RxFlow/_apis/wit/workitems/$Issue?api-version=7.1",
        json={"id": 99},
    )
    result = await _client().create_work_item("RxFlow", "Title", "Desc", "Issue")
    assert result["id"] == 99

    request = httpx_mock.get_requests()[0]
    assert request.headers["content-type"] == "application/json-patch+json"


async def test_list_valid_states(httpx_mock):
    httpx_mock.add_response(
        url="https://dev.azure.com/myorg/RxFlow/_apis/wit/workitemtypes/Issue/states?api-version=7.1",
        json={"value": [{"name": "To Do"}, {"name": "Doing"}, {"name": "Done"}]},
    )
    states = await _client().list_valid_states("Issue")
    assert states == ["To Do", "Doing", "Done"]
