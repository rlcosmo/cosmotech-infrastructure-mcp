from __future__ import annotations

from typing import Any

from cosmotech_mcp.providers import aws


def test_get_identity_does_not_request_credentials(monkeypatch: Any) -> None:
    class FakeSts:
        def get_caller_identity(self) -> dict[str, str]:
            return {
                "Account": "123456789012",
                "Arn": "arn:aws:iam::123456789012:role/read-only",
                "UserId": "AIDEXAMPLE",
            }

    monkeypatch.setattr(aws, "aws_client", lambda service, region=None: FakeSts())
    result = aws.get_identity()
    assert result["Account"] == "123456789012"
    assert "AccessKey" not in result
    assert "SecretAccessKey" not in result


def test_iam_inventory_returns_role_metadata_without_credential_calls(monkeypatch: Any) -> None:
    class FakeIam:
        def get_paginator(self, operation: str) -> Any:
            assert operation == "list_roles"

            class Paginator:
                def paginate(self) -> list[dict[str, Any]]:
                    return [
                        {
                            "Roles": [
                                {
                                    "RoleName": "read-only",
                                    "Arn": "arn:aws:iam::123456789012:role/read-only",
                                    "CreateDate": "2026-01-01T00:00:00Z",
                                }
                            ]
                        }
                    ]

            return Paginator()

        def list_attached_role_policies(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["RoleName"] == "read-only"
            return {"AttachedPolicies": [{"PolicyName": "ReadOnlyInventory"}]}

        def list_role_policies(self, **kwargs: Any) -> dict[str, Any]:
            return {"PolicyNames": []}

    monkeypatch.setattr(aws, "aws_client", lambda service, region=None: FakeIam())
    result = aws.iam_inventory()
    assert result["roles"][0]["attachedPolicies"] == ["ReadOnlyInventory"]
    assert "access-key values are never queried" in result["note"]
