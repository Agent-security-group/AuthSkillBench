#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE="$SCRIPT_DIR/original"
TARGET=${1:-/Users/carl/Desktop/bench}

restore() {
  src=$1
  dst=$2
  mkdir -p "$(dirname -- "$TARGET/$dst")"
  install -m 0644 "$SOURCE/$src" "$TARGET/$dst"
}

restore evaluation.py threat_build_skill/skill-backend/threat_builder/evaluation.py
restore build_threats.py threat_build_skill/skill-backend/build_threats.py
restore SKILL.md threat_build_skill/prompt-injection-threat-builder/SKILL.md
restore ATTACK_GOALS.md docs/attack-goal-table/MODIFIED_FILE.md
restore test_email_specs.py threat_build_skill/skill-backend/tests/test_email_specs.py
restore test_threat_builder.py threat_build_skill/skill-backend/tests/test_threat_builder.py
restore successful-upgrades.json docs/email-real-model-experiment-20260916/successful-upgrades.json
restore strict_upgrade.py docs/email-real-model-experiment-20260916/strict_upgrade.py
restore successful/62bfb8cfab49c3d2addaba80.json threat_build_skill/runs/generated_threats/successful/confidentiality/email/62bfb8cfab49c3d2addaba80.json
restore successful/e8ba175a00b0bc8de678dc09.json threat_build_skill/runs/generated_threats/successful/confidentiality/email/e8ba175a00b0bc8de678dc09.json
restore successful/23de04a5a46230fb4dcb8856.json threat_build_skill/runs/generated_threats/successful/integrity/email/23de04a5a46230fb4dcb8856.json
restore successful/623bda18b9cb60784d35d552.json threat_build_skill/runs/generated_threats/successful/integrity/email/623bda18b9cb60784d35d552.json

printf 'ROLLBACK_OK target=%s restored_files=12 restored_success_records=4\n' "$TARGET"
