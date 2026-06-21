from ccx.context import default_context


def test_default_context_shape():
    ctx = default_context()
    assert "@context" in ctx
    terms = ctx["@context"]
    assert terms["ccx"] == "https://w3id.org/ccx/"
    assert terms["schema"] == "https://schema.org/"
    assert terms["Person"] == "schema:Person"
    assert terms["name"] == "schema:name"


def test_default_context_is_copied_not_shared():
    a = default_context()
    a["@context"]["mutated"] = "x"
    b = default_context()
    assert "mutated" not in b["@context"]
