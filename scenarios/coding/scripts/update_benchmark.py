import json
with open("app/benchmark.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add compose_case_from_variant
old = '''def iter_case_specs('''
new = '''def compose_case_from_variant(
    group: dict,
    variant: dict,
    threats_dir: Path = DEFAULT_THREATS_DIR,
    tasks_dir: Path = DEFAULT_TASKS_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict:
    profile_ref = variant["threat_profile_ref"]
    profile = load_threat_profile(profile_ref, threats_dir=threats_dir)
    task_ref = variant["task_variant_ref"]
    task = load_task_variant(task_ref, tasks_dir=tasks_dir)
    skill = load_skill_descriptor(group["trusted_skill_ref"], skills_dir=skills_dir)
    return {
        "case_id": variant["case_id"],
        "contrast_group_id": group["contrast_group_id"],
        "trusted_skill_ref": group["trusted_skill_ref"],
        "skill_under_test": group["trusted_skill_name"],
        "trusted_skill": skill,
        "task": {"task_type": task["task_type"], "description": task["description"]},
        "task_variant": task,
        "task_variant_ref": task_ref,
        "threat_profile_ref": profile_ref,
        "threat_type": profile["threat_type"],
        "threat_profile": profile,
    }


def iter_case_specs('''
src = src.replace(old, new)

# Add list_cases
if "def list_cases" not in src:
    src = src.replace(
        "def iter_case_specs(",
        "def list_cases(contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> list[dict]:\n    cases: list[dict] = []\n    for group, variant in iter_case_specs(contrast_groups_dir=contrast_groups_dir):\n        cases.append({\"case_id\": variant[\"case_id\"], \"contrast_group_id\": group[\"contrast_group_id\"], \"task_variant_ref\": variant.get(\"task_variant_ref\"), \"threat_profile_ref\": variant.get(\"threat_profile_ref\")})\n    return cases\n\n\ndef iter_case_specs(",
    )

# Add load_case
if "def load_case" not in src:
    src = src.replace(
        "def list_cases(",
        "def load_case(case_id_or_group: str, contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> dict:\n    matches = iter_case_specs(contrast_groups_dir=contrast_groups_dir, selected=[case_id_or_group])\n    if len(matches) == 1:\n        group, variant = matches[0]\n        return compose_case_from_variant(group, variant)\n    if matches:\n        return {\"contrast_group_id\": matches[0][0][\"contrast_group_id\"], \"variants\": [{\"case_id\": v[\"case_id\"], \"task_variant_ref\": v.get(\"task_variant_ref\"), \"threat_profile_ref\": v.get(\"threat_profile_ref\")} for _, v in matches]}\n    raise KeyError(f\"unknown case: {case_id_or_group}\")\n\n\ndef list_cases(",
    )

# Add list_task_groups
if "def list_task_groups" not in src:
    src = src.replace(
        "def load_case(",
        "def list_task_groups(tasks_dir: Path = DEFAULT_TASKS_DIR) -> list[dict]:\n    groups: list[dict] = []\n    for group_dir in sorted(p for p in tasks_dir.iterdir() if p.is_dir()):\n        variants = [json.load(open(f, encoding=\"utf-8\")) for f in sorted(group_dir.glob(\"*.json\"))]\n        groups.append({\"task_group_id\": group_dir.name, \"variant_count\": len(variants), \"operations\": sorted({v.get(\"operation\",\"\") for v in variants})})\n    return groups\n\n\ndef load_case(",
    )

# Add list_threat_groups
if "def list_threat_groups" not in src:
    src = src.replace(
        "def list_task_groups(",
        "def list_threat_groups(threats_dir: Path = DEFAULT_THREATS_DIR) -> list[dict]:\n    groups: list[dict] = []\n    for group_dir in sorted(p for p in threats_dir.iterdir() if p.is_dir()):\n        profiles = [json.load(open(f, encoding=\"utf-8\")) for f in sorted(group_dir.glob(\"*.json\"))]\n        groups.append({\"threat_group_id\": group_dir.name, \"profile_count\": len(profiles), \"threat_types\": sorted({p.get(\"threat_type\",\"\") for p in profiles})})\n    return groups\n\n\ndef list_task_groups(",
    )

with open("app/benchmark.py", "w", encoding="utf-8") as f:
    f.write(src)

print("benchmark.py patched OK")
