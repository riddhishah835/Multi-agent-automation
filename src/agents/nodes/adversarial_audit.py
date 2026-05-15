async def node_adversarial_audit(state: AuditState) -> AuditState:
    """
    Policy-driven adversarial audit node.
    FIXED: Corrected indentation of control checking logic (lines 79-89).
    """
    state["current_node"] = "adversarial_audit"
    findings = []
    document_text = state["parsed_documents"].get("raw_text", "")
    rules = state["retrieved_rules"]["required_controls"]

    coverage = {
        "encryption": False,
        "mfa": False,
        "audit_logging": False
    }

    for control_name, control_config in rules.items():
        if not control_config["required"]:
            continue

        # FIXED: Moved inside loop (was incorrectly outside)
        keywords = control_config["keywords"]

        found = any(
            keyword.lower() in document_text.lower()
            for keyword in keywords
        )

        coverage[control_name] = found

        matched_keyword = None
        for keyword in keywords:
            if keyword.lower() in document_text.lower():
                matched_keyword = keyword
                break

        # FIXED: Moved inside loop (was incorrectly outside)
        if not found:
            findings.append({
                "severity": control_config["severity"],
                "issue": f"{control_name.replace('_', ' ').title()} controls missing",
                "status": "non_compliant",
                "evidence": (
                    f"Detected keyword: {matched_keyword}"
                    if matched_keyword
                    else f"No {control_name.replace('_', ' ')} controls detected in document"
                ),
                "finding_id": f"F-{len(findings)+1:03}",
                "page_reference": "Document-wide search",
                "frameworks": state["retrieved_rules"]["compliance_frameworks"],
                "control_description": control_config["description"],
                "confidence": 0.92
            })

    state["control_coverage"] = coverage
    state["audit_findings"] = findings

    return state