#!/usr/bin/env bash
# Tests for packaging/package_version.sh (run by the CI version job).
# Needs dpkg for the Debian version ordering.
#
# Usage: packaging/test_package_version.sh

set -euo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/package_version.sh"
failed=0

# expect REF EXPECTED_OUTPUT: package_version.sh 1.0.0 REF must print exactly that
expect() {
    local ref="$1" expected="$2" actual
    if ! actual="$("$SCRIPT" 1.0.0 "$ref" 2>&1)"; then
        echo "FAIL: $ref: exited with an error: $actual"
        failed=$((failed + 1))
    elif [ "$actual" != "$expected" ]; then
        printf 'FAIL: %s\n  expected:\n%s\n  actual:\n%s\n' "$ref" "$expected" "$actual"
        failed=$((failed + 1))
    else
        echo "ok:   $ref -> $(echo "$actual" | tr '\n' ' ')"
    fi
}

# expect_error VERSION REF: package_version.sh must fail
expect_error() {
    local out
    if out="$("$SCRIPT" "$1" "$2" 2>&1)"; then
        echo "FAIL: $1 $2: expected an error, got: $out"
        failed=$((failed + 1))
    else
        echo "ok:   $1 $2 rejected: $out"
    fi
}

expect_dpkg() {
    if dpkg --compare-versions "$1" "$2" "$3"; then
        echo "ok:   dpkg: $1 $2 $3"
    else
        echo "FAIL: dpkg: $1 $2 $3"
        failed=$((failed + 1))
    fi
}

plain="version=1.0.0
package_version=1.0.0
deb_version=1.0.0
prerelease=false"

expect "" "$plain
release_tag="
expect "refs/heads/main" "$plain
release_tag="
expect "refs/pull/45/merge" "$plain
release_tag="
expect "refs/tags/v1.0.0" "$plain
release_tag=v1.0.0"
expect "refs/tags/v.1.0.0" "$plain
release_tag=v.1.0.0"
expect "refs/tags/v1.0.0-rc.1" "version=1.0.0
package_version=1.0.0-rc.1
deb_version=1.0.0~rc.1
prerelease=true
release_tag=v1.0.0-rc.1"
expect "refs/tags/v1.0.0-beta2" "version=1.0.0
package_version=1.0.0-beta2
deb_version=1.0.0~beta2
prerelease=true
release_tag=v1.0.0-beta2"

expect_error 1.0.0 refs/tags/v1.0.1
expect_error 1.0.0 refs/tags/v1.0.1-rc.1
expect_error 1.0.0 refs/tags/v1.0
expect_error 1.0.0 refs/tags/v1.0.0-
expect_error 1.0.0 refs/tags/v1.0.0-rc-1
expect_error 1.0.0 refs/tags/v1.0.0-rc~1
expect_error 1.0.0 "refs/tags/v1.0.0-rc 1"
expect_error 1.0.0-rc.1 refs/heads/main
expect_error "" refs/heads/main

# A pre-release must sort before the final release (apt must offer 1.0.0 as an
# upgrade of 1.0.0~rc.1), and after the previous version.
expect_dpkg 1.0.0~rc.1 lt 1.0.0
expect_dpkg 1.0.0~rc.1 lt 1.0.0~rc.2
expect_dpkg 1.0.0~beta.1 lt 1.0.0~rc.1
expect_dpkg 0.9.0 lt 1.0.0~rc.1

echo "$failed failed"
[ "$failed" -eq 0 ]
