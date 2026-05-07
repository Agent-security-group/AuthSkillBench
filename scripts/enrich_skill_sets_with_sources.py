#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "data" / "skills" / "source_artifacts"


ARTIFACT_FILES = {
    "github_rest": "github_rest_selected.json",
    "slack_web": "slack_web_selected.json",
    "google": "google_discovery_selected.json",
    "aws_codedeploy": "aws_codedeploy_selected.json",
    "kubernetes": "kubernetes_openapi_selected.json",
}


SKILL_SOURCE_MAP = {
    "github.get_file_contents": ("github_rest", "repos/get-content"),
    "github.create_or_update_file": ("github_rest", "repos/create-or-update-file-contents"),
    "github.delete_file": ("github_rest", "repos/delete-file"),
    "github.create_pull_request": ("github_rest", "pulls/create"),
    "github.merge_pull_request": ("github_rest", "pulls/merge"),
    "github.actions.create_workflow_dispatch": ("github_rest", "actions/create-workflow-dispatch"),
    "gmail.users.messages.send": ("google", "gmail.users.messages.send"),
    "gmail.users.drafts.create": ("google", "gmail.users.drafts.create"),
    "slack.chat_postMessage": ("slack_web", "chat_postMessage"),
    "slack.files_upload": ("slack_web", "files_upload"),
    "aws.codedeploy.create_deployment": ("aws_codedeploy", "CreateDeployment"),
    "aws.codedeploy.get_deployment": ("aws_codedeploy", "GetDeployment"),
    "kubernetes.read_namespaced_deployment_status": ("kubernetes", "readAppsV1NamespacedDeploymentStatus"),
    "kubernetes.patch_namespaced_deployment_scale": ("kubernetes", "patchAppsV1NamespacedDeploymentScale"),
    "kubernetes.delete_namespaced_deployment": ("kubernetes", "deleteAppsV1NamespacedDeployment"),
    "bigquery.jobs.query": ("google", "bigquery.jobs.query"),
    "google_drive.files.export": ("google", "drive.files.export"),
    "google_sheets.spreadsheets.values.update": ("google", "sheets.spreadsheets.values.update"),
}


SOURCE_KIND = {
    "github_rest": "github_rest_openapi_operation",
    "slack_web": "slack_web_openapi_operation",
    "google": "google_discovery_method",
    "aws_codedeploy": "aws_botocore_service_model_operation",
    "kubernetes": "kubernetes_openapi_operation",
}


PROJECTION_NOTES = {
    "gmail.users.messages.send": "The real Gmail API accepts a Message resource, typically with raw RFC822 content. The benchmark projection exposes to/subject/body fields as a common agent wrapper interface.",
    "gmail.users.drafts.create": "The real Gmail API accepts a Draft resource containing a Message. The benchmark projection exposes to/subject/body fields as a common agent wrapper interface.",
    "aws.codedeploy.create_deployment": "The Botocore model is the source operation. The benchmark projection keeps deploymentGroupName and revision explicit because they are central to authorization even though AWS can infer defaults.",
    "kubernetes.patch_namespaced_deployment_scale": "The Kubernetes operation patches the scale subresource. The benchmark projection exposes replicas directly as the common agent-level wrapper argument.",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")


def load_artifacts() -> dict[str, dict[str, Any]]:
    return {
        key: load_json(ARTIFACT_DIR / filename)
        for key, filename in ARTIFACT_FILES.items()
    }


def source_artifact_path(source_key: str) -> str:
    return f"data/skills/source_artifacts/{ARTIFACT_FILES[source_key]}"


def github_schema(artifact: dict[str, Any], operation_id: str) -> dict[str, Any]:
    entry = artifact["selected_operations"][operation_id]
    operation = entry["operation"]
    return {
        "kind": SOURCE_KIND["github_rest"],
        "operation_id": operation_id,
        "http_method": entry["method"],
        "path": entry["path"],
        "summary": operation.get("summary"),
        "parameters": operation.get("parameters", []),
        "request_body": operation.get("requestBody"),
        "responses": operation.get("responses"),
        "external_docs": operation.get("externalDocs"),
    }


def slack_schema(artifact: dict[str, Any], operation_id: str) -> dict[str, Any]:
    entry = artifact["selected_operations"][operation_id]
    operation = entry["operation"]
    return {
        "kind": SOURCE_KIND["slack_web"],
        "operation_id": operation_id,
        "http_method": entry["method"],
        "path": entry["path"],
        "description": operation.get("description"),
        "consumes": operation.get("consumes"),
        "parameters": operation.get("parameters", []),
        "responses": operation.get("responses"),
        "external_docs": operation.get("externalDocs"),
    }


def google_schema(artifact: dict[str, Any], method_id: str) -> dict[str, Any]:
    entry = artifact["selected_methods"][method_id]
    method = entry["method"]
    return {
        "kind": SOURCE_KIND["google"],
        "method_id": method_id,
        "http_method": method.get("httpMethod"),
        "path": method.get("path"),
        "flat_path": method.get("flatPath"),
        "description": method.get("description"),
        "parameters": method.get("parameters", {}),
        "parameter_order": method.get("parameterOrder", []),
        "request": method.get("request"),
        "response": method.get("response"),
        "scopes": method.get("scopes", []),
        "supports_media_upload": method.get("supportsMediaUpload"),
        "supports_media_download": method.get("supportsMediaDownload"),
        "referenced_schemas": entry.get("referenced_schemas", {}),
    }


def aws_schema(artifact: dict[str, Any], operation_name: str) -> dict[str, Any]:
    entry = artifact["selected_operations"][operation_name]
    operation = entry["operation"]
    input_shape = operation.get("input", {}).get("shape")
    output_shape = operation.get("output", {}).get("shape")
    shapes = entry.get("referenced_shapes", {})
    return {
        "kind": SOURCE_KIND["aws_codedeploy"],
        "operation_name": operation_name,
        "http": operation.get("http"),
        "documentation": operation.get("documentation"),
        "input_shape_name": input_shape,
        "input_shape": shapes.get(input_shape),
        "output_shape_name": output_shape,
        "output_shape": shapes.get(output_shape),
        "errors": operation.get("errors", []),
    }


def kubernetes_schema(artifact: dict[str, Any], operation_id: str) -> dict[str, Any]:
    entry = artifact["selected_operations"][operation_id]
    operation = entry["operation"]
    return {
        "kind": SOURCE_KIND["kubernetes"],
        "operation_id": operation_id,
        "http_method": entry["method"],
        "path": entry["path"],
        "description": operation.get("description"),
        "parameters": entry.get("resolved_parameters", []),
        "responses": operation.get("responses"),
        "tags": operation.get("tags", []),
    }


def real_tool_schema(artifacts: dict[str, dict[str, Any]], source_key: str, operation_id: str) -> dict[str, Any]:
    if source_key == "github_rest":
        return github_schema(artifacts[source_key], operation_id)
    if source_key == "slack_web":
        return slack_schema(artifacts[source_key], operation_id)
    if source_key == "google":
        return google_schema(artifacts[source_key], operation_id)
    if source_key == "aws_codedeploy":
        return aws_schema(artifacts[source_key], operation_id)
    if source_key == "kubernetes":
        return kubernetes_schema(artifacts[source_key], operation_id)
    raise ValueError(f"unknown source key: {source_key}")


def enrich_skill(skill: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    skill = dict(skill)
    projection_schema = skill.pop("arguments_schema", None)
    if projection_schema is None:
        projection_schema = skill.get("benchmark_projection", {}).get("arguments_schema")
    if projection_schema is None:
        raise ValueError(f"skill has no benchmark projection schema: {skill['name']}")

    source = SKILL_SOURCE_MAP.get(skill["name"])
    if source is None:
        raise ValueError(f"skill has no real source mapping: {skill['name']}")
    else:
        source_key, operation_id = source
        skill["source_provenance"] = {
            "source_type": SOURCE_KIND[source_key],
            "source_artifact": source_artifact_path(source_key),
            "source_operation": operation_id,
        }
        skill["real_tool_schema"] = real_tool_schema(artifacts, source_key, operation_id)

    skill["benchmark_projection"] = {
        "arguments_schema": projection_schema,
        "note": PROJECTION_NOTES.get(
            skill["name"],
            "Benchmark-facing projection of the real tool/API schema used to keep authorization samples readable and comparable.",
        ),
    }
    return skill


def main() -> int:
    artifacts = load_artifacts()
    paths = sorted((ROOT / "data" / "skills").glob("*.skills.json"))
    for path in paths:
        skill_set = load_json(path)
        skill_set["schema_layers"] = {
            "real_tool_schema": "Source-derived operation schema extracted from official API/tool specifications.",
            "benchmark_projection": "Controlled agent-facing argument schema used by benchmark samples.",
        }
        skill_set["source_artifacts"] = sorted(
            {
                source_artifact_path(source_key)
                for skill in skill_set.get("skills", [])
                for source_key, _ in [SKILL_SOURCE_MAP[skill["name"]]]
            }
        )
        skill_set["skills"] = [enrich_skill(skill, artifacts) for skill in skill_set["skills"]]
        write_json(path, skill_set)
        print(f"enriched {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
