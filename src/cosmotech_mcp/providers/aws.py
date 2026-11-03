from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config

CLIENT_CONFIG = Config(
    connect_timeout=5,
    read_timeout=15,
    retries={"mode": "standard", "total_max_attempts": 3},
    max_pool_connections=16,
)
MAX_RESOURCES = 200


def aws_client(service: str, region: str | None = None) -> Any:
    session = boto3.Session()
    return session.client(service, region_name=region or session.region_name, config=CLIENT_CONFIG)


def _limited_pages(
    client: Any, operation: str, result_key: str, **kwargs: Any
) -> list[dict[str, Any]]:
    paginator = client.get_paginator(operation)
    result: list[dict[str, Any]] = []
    for page in paginator.paginate(**kwargs):
        result.extend(page.get(result_key, []))
        if len(result) >= MAX_RESOURCES:
            return result[:MAX_RESOURCES]
    return result


def get_identity() -> dict[str, Any]:
    response = aws_client("sts").get_caller_identity()
    return {key: response[key] for key in ("Account", "Arn", "UserId") if key in response}


def eks_inventory(region: str | None = None) -> dict[str, Any]:
    client = aws_client("eks", region)
    clusters = _limited_pages(client, "list_clusters", "clusters")
    results = []
    for name in clusters:
        cluster = client.describe_cluster(name=name)["cluster"]
        node_groups = client.list_nodegroups(clusterName=name).get("nodegroups", [])
        results.append(
            {
                "name": name,
                "status": cluster.get("status"),
                "version": cluster.get("version"),
                "createdAt": cluster.get("createdAt"),
                "endpointPublicAccess": cluster.get("resourcesVpcConfig", {}).get(
                    "endpointPublicAccess"
                ),
                "endpointPrivateAccess": cluster.get("resourcesVpcConfig", {}).get(
                    "endpointPrivateAccess"
                ),
                "publicAccessCidrs": cluster.get("resourcesVpcConfig", {}).get(
                    "publicAccessCidrs", []
                ),
                "nodeGroups": node_groups,
            }
        )
    return {"region": region or boto3.Session().region_name, "clusters": results}


def ecr_inventory(region: str | None = None) -> dict[str, Any]:
    client = aws_client("ecr", region)
    repos = _limited_pages(client, "describe_repositories", "repositories")
    return {
        "region": region or boto3.Session().region_name,
        "repositories": [
            {
                "name": repo.get("repositoryName"),
                "uri": repo.get("repositoryUri"),
                "createdAt": repo.get("createdAt"),
                "imageTagMutability": repo.get("imageTagMutability"),
                "scanOnPush": repo.get("imageScanningConfiguration", {}).get("scanOnPush"),
                "encryptionType": repo.get("encryptionConfiguration", {}).get("encryptionType"),
            }
            for repo in repos
        ],
    }


def ec2_inventory(region: str | None = None) -> dict[str, Any]:
    client = aws_client("ec2", region)
    reservations = _limited_pages(client, "describe_instances", "Reservations")
    instances = [
        instance for reservation in reservations for instance in reservation.get("Instances", [])
    ]
    return {
        "region": region or boto3.Session().region_name,
        "instances": [
            {
                "id": instance.get("InstanceId"),
                "state": instance.get("State", {}).get("Name"),
                "type": instance.get("InstanceType"),
                "availabilityZone": instance.get("Placement", {}).get("AvailabilityZone"),
                "subnetId": instance.get("SubnetId"),
                "vpcId": instance.get("VpcId"),
                "privateIp": instance.get("PrivateIpAddress"),
                "publicIp": instance.get("PublicIpAddress"),
                "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
            }
            for instance in instances[:MAX_RESOURCES]
        ],
    }


def sqs_inventory(region: str | None = None) -> dict[str, Any]:
    client = aws_client("sqs", region)
    urls = _limited_pages(client, "list_queues", "QueueUrls")
    queues = []
    for url in urls:
        attrs = client.get_queue_attributes(
            QueueUrl=url,
            AttributeNames=[
                "QueueArn",
                "VisibilityTimeout",
                "MessageRetentionPeriod",
                "RedrivePolicy",
                "SqsManagedSseEnabled",
                "KmsMasterKeyId",
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
            ],
        ).get("Attributes", {})
        queues.append({"url": url, **attrs})
    return {"region": region or boto3.Session().region_name, "queues": queues}


def dynamodb_inventory(region: str | None = None) -> dict[str, Any]:
    client = aws_client("dynamodb", region)
    names = _limited_pages(client, "list_tables", "TableNames")
    tables = []
    for name in names:
        table = client.describe_table(TableName=name)["Table"]
        pitr = client.describe_continuous_backups(TableName=name).get(
            "ContinuousBackupsDescription", {}
        )
        ttl = client.describe_time_to_live(TableName=name).get("TimeToLiveDescription", {})
        tables.append(
            {
                "name": name,
                "status": table.get("TableStatus"),
                "billingMode": table.get("BillingModeSummary", {}).get("BillingMode"),
                "itemCount": table.get("ItemCount"),
                "sizeBytes": table.get("TableSizeBytes"),
                "pointInTimeRecovery": pitr.get("PointInTimeRecoveryStatus"),
                "ttlStatus": ttl.get("TimeToLiveStatus"),
                "ttlAttribute": ttl.get("AttributeName"),
                "streamEnabled": table.get("StreamSpecification", {}).get("StreamEnabled", False),
            }
        )
    return {"region": region or boto3.Session().region_name, "tables": tables}


def iam_inventory() -> dict[str, Any]:
    client = aws_client("iam")
    roles = _limited_pages(client, "list_roles", "Roles")
    role_summaries = []
    for role in roles:
        role_name = role["RoleName"]
        attached = client.list_attached_role_policies(RoleName=role_name).get(
            "AttachedPolicies", []
        )
        inline = client.list_role_policies(RoleName=role_name).get("PolicyNames", [])
        role_summaries.append(
            {
                "name": role_name,
                "arn": role.get("Arn"),
                "createdAt": role.get("CreateDate"),
                "attachedPolicies": [policy.get("PolicyName") for policy in attached],
                "inlinePolicyNames": inline,
                "hasPermissionsBoundary": bool(role.get("PermissionsBoundary")),
            }
        )
    return {"roles": role_summaries, "note": "Credential and access-key values are never queried."}


INVENTORY_FUNCTIONS = {
    "eks": eks_inventory,
    "ecr": ecr_inventory,
    "ec2": ec2_inventory,
    "sqs": sqs_inventory,
    "dynamodb": dynamodb_inventory,
    "iam": lambda _region=None: iam_inventory(),
}


def inventory(region: str | None = None) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    for name, function in INVENTORY_FUNCTIONS.items():
        try:
            sections[name] = function(region)
        except Exception as exc:
            sections[name] = {"error": type(exc).__name__}
    return {"region": region or boto3.Session().region_name, "services": sections}
