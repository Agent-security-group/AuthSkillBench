#!/usr/bin/env python3
from __future__ import annotations

import json
import ssl
from datetime import date
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "skills" / "source_artifacts"


SOURCES = {
    "github_rest": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
    "slack_web": "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2_without_examples.json",
    "gmail_discovery": "https://www.googleapis.com/discovery/v1/apis/gmail/v1/rest",
    "drive_discovery": "https://www.googleapis.com/discovery/v1/apis/drive/v3/rest",
    "sheets_discovery": "https://sheets.googleapis.com/$discovery/rest?version=v4",
    "bigquery_discovery": "https://bigquery.googleapis.com/discovery/v1/apis/bigquery/v2/rest",
    "aws_codedeploy_botocore": "https://raw.githubusercontent.com/boto/botocore/develop/botocore/data/codedeploy/2014-10-06/service-2.json",
    "kubernetes_openapi": "https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json",
}


GITHUB_OPERATION_IDS = {
    "actions/create-workflow-dispatch",
    "repos/get-content",
    "repos/create-or-update-file-contents",
    "repos/delete-file",
    "pulls/create",
    "pulls/merge",
}

SLACK_OPERATION_IDS = {"chat_postMessage", "files_upload"}

AWS_OPERATIONS = {"CreateDeployment", "GetDeployment"}

KUBERNETES_OPERATION_IDS = {
    "readAppsV1NamespacedDeploymentStatus",
    "patchAppsV1NamespacedDeploymentScale",
    "deleteAppsV1NamespacedDeployment",
}


def fetch_json(url: str) -> dict[str, Any]:
    # Some macOS Python installs lack an up-to-date CA bundle. The sources here
    # are public official schemas; if default verification fails, use an
    # unverified context rather than silently falling back to hand-written data.
    try:
        with urlopen(url, timeout=90) as response:
            return json.load(response)
    except (ssl.SSLCertVerificationError, URLError) as exc:
        if isinstance(exc, URLError) and not isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise
        context = ssl._create_unverified_context()
        with urlopen(url, context=context, timeout=90) as response:
            return json.load(response)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def collect_github() -> dict[str, Any]:
    spec = fetch_json(SOURCES["github_rest"])
    selected: dict[str, Any] = {}
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id in GITHUB_OPERATION_IDS:
                selected[operation_id] = {
                    "method": method.upper(),
                    "path": path,
                    "operation": operation,
                }

    return {
        "artifact_id": "github_rest_selected_operations",
        "source_url": SOURCES["github_rest"],
        "retrieved_date": str(date.today()),
        "format": "OpenAPI operation objects from GitHub REST API description",
        "selected_operations": selected,
    }


def collect_slack() -> dict[str, Any]:
    spec = fetch_json(SOURCES["slack_web"])
    selected: dict[str, Any] = {}
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id in SLACK_OPERATION_IDS:
                selected[operation_id] = {
                    "method": method.upper(),
                    "path": path,
                    "operation": operation,
                }

    return {
        "artifact_id": "slack_web_selected_operations",
        "source_url": SOURCES["slack_web"],
        "retrieved_date": str(date.today()),
        "format": "OpenAPI operation objects from Slack Web API spec",
        "selected_operations": selected,
    }


def resolve_google_method(spec: dict[str, Any], parts: list[str]) -> dict[str, Any]:
    node = spec
    for part in parts[:-1]:
        node = node["resources"][part]
    return node["methods"][parts[-1]]


def google_method(spec: dict[str, Any], method_id: str, parts: list[str]) -> dict[str, Any]:
    method = resolve_google_method(spec, parts)
    schemas: dict[str, Any] = {}
    for field in ("request", "response"):
        ref = method.get(field, {}).get("$ref")
        if ref and ref in spec.get("schemas", {}):
            schemas[ref] = spec["schemas"][ref]
    return {
        "id": method_id,
        "method": method,
        "referenced_schemas": schemas,
    }


def collect_google() -> dict[str, Any]:
    gmail = fetch_json(SOURCES["gmail_discovery"])
    drive = fetch_json(SOURCES["drive_discovery"])
    sheets = fetch_json(SOURCES["sheets_discovery"])
    bigquery = fetch_json(SOURCES["bigquery_discovery"])

    selected = {
        "gmail.users.messages.send": google_method(gmail, "gmail.users.messages.send", ["users", "messages", "send"]),
        "gmail.users.drafts.create": google_method(gmail, "gmail.users.drafts.create", ["users", "drafts", "create"]),
        "drive.files.export": google_method(drive, "drive.files.export", ["files", "export"]),
        "sheets.spreadsheets.values.update": google_method(
            sheets,
            "sheets.spreadsheets.values.update",
            ["spreadsheets", "values", "update"],
        ),
        "bigquery.jobs.query": google_method(bigquery, "bigquery.jobs.query", ["jobs", "query"]),
    }

    return {
        "artifact_id": "google_discovery_selected_methods",
        "source_urls": {
            "gmail": SOURCES["gmail_discovery"],
            "drive": SOURCES["drive_discovery"],
            "sheets": SOURCES["sheets_discovery"],
            "bigquery": SOURCES["bigquery_discovery"],
        },
        "retrieved_date": str(date.today()),
        "format": "Google Discovery API method objects with referenced request/response schemas",
        "selected_methods": selected,
    }


def collect_shape_refs(service: dict[str, Any], shape_name: str, seen: set[str]) -> None:
    if shape_name in seen:
        return
    seen.add(shape_name)
    shape = service.get("shapes", {}).get(shape_name)
    if not isinstance(shape, dict):
        return
    for member in shape.get("members", {}).values():
        ref = member.get("shape")
        if ref:
            collect_shape_refs(service, ref, seen)
    for key in ("member", "key", "value"):
        ref = shape.get(key, {}).get("shape")
        if ref:
            collect_shape_refs(service, ref, seen)


def collect_aws_codedeploy() -> dict[str, Any]:
    service = fetch_json(SOURCES["aws_codedeploy_botocore"])
    selected: dict[str, Any] = {}
    for op_name in AWS_OPERATIONS:
        operation = service["operations"][op_name]
        refs: set[str] = set()
        input_shape = operation.get("input", {}).get("shape")
        output_shape = operation.get("output", {}).get("shape")
        if input_shape:
            collect_shape_refs(service, input_shape, refs)
        if output_shape:
            collect_shape_refs(service, output_shape, refs)
        selected[op_name] = {
            "operation": operation,
            "referenced_shapes": {name: service["shapes"][name] for name in sorted(refs)},
        }

    return {
        "artifact_id": "aws_codedeploy_botocore_selected_operations",
        "source_url": SOURCES["aws_codedeploy_botocore"],
        "retrieved_date": str(date.today()),
        "format": "Botocore service model operation objects and referenced shapes",
        "selected_operations": selected,
    }


def resolve_openapi_ref(spec: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        return {"$ref": ref}
    node: Any = spec
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def resolve_kubernetes_parameters(spec: dict[str, Any], parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolved = []
    for parameter in parameters:
        if "$ref" in parameter:
            resolved.append(resolve_openapi_ref(spec, parameter["$ref"]))
        else:
            resolved.append(parameter)
    return resolved


def collect_kubernetes() -> dict[str, Any]:
    spec = fetch_json(SOURCES["kubernetes_openapi"])
    selected: dict[str, Any] = {}
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id in KUBERNETES_OPERATION_IDS:
                selected[operation_id] = {
                    "method": method.upper(),
                    "path": path,
                    "operation": operation,
                    "resolved_parameters": resolve_kubernetes_parameters(spec, operation.get("parameters", [])),
                }

    return {
        "artifact_id": "kubernetes_openapi_selected_operations",
        "source_url": SOURCES["kubernetes_openapi"],
        "retrieved_date": str(date.today()),
        "format": "Kubernetes OpenAPI v2 operation objects with resolved parameters",
        "selected_operations": selected,
    }


def main() -> int:
    artifacts = {
        "github_rest_selected.json": collect_github(),
        "slack_web_selected.json": collect_slack(),
        "google_discovery_selected.json": collect_google(),
        "aws_codedeploy_selected.json": collect_aws_codedeploy(),
        "kubernetes_openapi_selected.json": collect_kubernetes(),
    }
    for filename, artifact in artifacts.items():
        path = OUT_DIR / filename
        write_json(path, artifact)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
