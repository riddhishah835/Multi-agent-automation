# tests/test_p2.py
from src.tools.registry import registry, HIGH_RISK_TOOLS
from src.tools.pruner import prune_tools
from src.tools.mcp_bridge import call_tool
from src.agents.runtime import researcher_agent, data_fetcher_agent, content_generator_agent


def test_registry_loads():
    tools = registry.get_all()
    assert len(tools) > 0, "Registry should have tools"
    print("✓ Registry:", [t.name for t in tools])


def test_tenant_filtering():
    acme_tools = registry.get_for_tenant("tenant_acme")
    default_tools = registry.get_for_tenant("tenant_demo")
    # tenant_acme can use database_write, tenant_demo cannot
    acme_names = [t.name for t in acme_tools]
    demo_names = [t.name for t in default_tools]
    assert "database_write" in acme_names
    assert "database_write" not in demo_names
    print("✓ Tenant isolation OK")


def test_pruner_returns_top3():
    top = prune_tools("search the web for AI trends", "tenant_demo")
    assert 1 <= len(top) <= 3
    print("✓ Pruner top tools:", [t.name for t in top])


def test_pruner_hard_cap():
    top = prune_tools("any task", "tenant_acme", top_k=99)
    assert len(top) <= 5, "Pruner must never exceed MAX_TOOLS"
    print("✓ Hard cap enforced")


def test_bridge_validates_input():
    try:
        call_tool("web_search", {})  # missing 'query'
        assert False, "Should have raised"
    except ValueError:
        print("✓ Bridge rejects bad input")


def test_bridge_mock_call():
    result = call_tool("web_search", {"query": "AI trends 2025"})
    assert "results" in result
    print("✓ Bridge mock call OK:", result)


def test_high_risk_set():
    assert "send_email" in HIGH_RISK_TOOLS
    assert "database_write" in HIGH_RISK_TOOLS
    print("✓ HIGH_RISK_TOOLS:", HIGH_RISK_TOOLS)


def test_researcher_agent():
    result = researcher_agent("Find AI news", "tenant_demo")
    assert result.status == "success"
    assert result.agent_name == "researcher"
    print("✓ Researcher:", result.tools_used)


def test_data_fetcher_agent():
    result = data_fetcher_agent("Fetch customer data", "tenant_acme", {"customer_id": "C001"})
    assert result.status == "success"
    print("✓ Data fetcher:", result.tools_used)


def test_content_generator_uses_high_risk():
    result = content_generator_agent(
        "Send compliance summary email",
        "tenant_demo",
        {"to": "cto@acme.com", "subject": "Q3 Report"},
    )
    # At least one high-risk tool should have been selected
    used_high_risk = any(t in HIGH_RISK_TOOLS for t in result.tools_used)
    assert used_high_risk, f"Expected high-risk tool, got: {result.tools_used}"
    print("✓ Content generator triggered HITL tools:", result.tools_used)


if __name__ == "__main__":
    test_registry_loads()
    test_tenant_filtering()
    test_pruner_returns_top3()
    test_pruner_hard_cap()
    test_bridge_validates_input()
    test_bridge_mock_call()
    test_high_risk_set()
    test_researcher_agent()
    test_data_fetcher_agent()
    test_content_generator_uses_high_risk()
    print("\n✅ All P2 tests passed")