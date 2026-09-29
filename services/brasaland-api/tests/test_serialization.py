from brasaland_api.main import app


def test_every_api_route_declares_a_response_model():
    paths = app.openapi()["paths"]
    operations = [operation for methods in paths.values() for operation in methods.values()]

    assert len(operations) == 16
    assert all(operation["responses"] for operation in operations)
    assert all(
        "content" in response
        for operation in operations
        for status, response in operation["responses"].items()
        if status in {"200", "201"}
    )


def test_sensitive_fields_are_absent_from_response_schemas():
    schemas = app.openapi()["components"]["schemas"]
    schema_text = repr(schemas)

    assert "hashed_password" not in schema_text
    assert "UserRegistrationOut" in schemas
    assert "email" not in schemas["UserRegistrationOut"]["properties"]
    assert "PurchaseOrderOut" in schemas
    assert "created_by" not in schemas["PurchaseOrderOut"]["properties"]


def test_list_endpoints_use_flat_response_projections():
    paths = app.openapi()["paths"]

    assert paths["/operations/sales"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"].endswith("SalesSummary")
    assert paths["/operations/inventory"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"].endswith("InventoryItem")
    assert paths["/supply-chain/suppliers"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"].endswith("SupplierOut")
    assert paths["/hr/employees"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"].endswith("EmployeeOut")
