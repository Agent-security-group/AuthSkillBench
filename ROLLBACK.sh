#!/bin/sh
set -eu

target=${1:?usage: ROLLBACK.sh TARGET_COPY}
baseline=/Users/carl/Desktop/bench/threat_build_skill/skill-backend.baseline

mkdir -p "$target/threat_build_skill/skill-backend/threat_builder"
mkdir -p "$target/threat_build_skill/skill-backend/tests"
mkdir -p "$target/scenarios/email/app"
cp "$baseline/build_threats.py" "$target/threat_build_skill/skill-backend/build_threats.py"
for name in builder.py adapters.py goals.py evaluation.py; do
    cp "$baseline/threat_builder/$name" "$target/threat_build_skill/skill-backend/threat_builder/$name"
done
rm -f "$target/scenarios/email/app/email_specs.py"
rm -f "$target/threat_build_skill/skill-backend/tests/test_email_specs.py"
printf '%s\n' 'restored baseline threat builder and removed Email-specific spec/test from target copy'
