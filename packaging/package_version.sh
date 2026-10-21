#!/usr/bin/env bash
# Compute the package version of a build from __version__.py and the git ref.
# The CI version job (.github/workflows/build.yml) runs this once and passes
# the results to the .deb and Setup.exe builds.
#
# Usage: packaging/package_version.sh VERSION [REF]
#   VERSION  __version__ from vinyl-label-printer/__version__.py (plain X.Y.Z)
#   REF      the git ref of the build, e.g. refs/heads/main, refs/pull/1/merge,
#            refs/tags/v1.0.0 or refs/tags/v1.0.0-rc.1 (default: none)
#
# Prints key=value lines (append them to $GITHUB_OUTPUT):
#   version          X.Y.Z; the app version and the numeric Windows file version
#   package_version  X.Y.Z or X.Y.Z-<suffix>; used for file names and AppVersion
#   deb_version      Debian version; "~" instead of "-", so 1.0.0~rc.1 sorts
#                    before 1.0.0
#   prerelease       true for a tag with a suffix
#   release_tag      the tag name for a v* tag, empty otherwise
#
# Branch and PR builds and plain tags vX.Y.Z build X.Y.Z. A tag vX.Y.Z-<suffix>
# builds X.Y.Z-<suffix>. The X.Y.Z of a tag must equal VERSION. The in-app
# update check and install.sh / install.ps1 never offer a tag with a suffix.

set -euo pipefail

die() { echo "::error::$*" >&2; exit 1; }

VERSION="${1:-}"
REF="${2:-}"

[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || die "__version__.py must be a plain X.Y.Z version, got '$VERSION'"

package_version="$VERSION"
prerelease=false
release_tag=""

if [[ "$REF" == refs/tags/v* ]]; then
    release_tag="${REF#refs/tags/}"
    # "v1.2.3" -> "1.2.3" (older tags look like "v.0.2.0")
    tag_version="${release_tag#v}"
    tag_version="${tag_version#.}"
    base="${tag_version%%-*}"
    if [ "$base" != "$VERSION" ]; then
        die "Tag $release_tag does not match __version__.py ($VERSION)"
    fi
    if [ "$base" != "$tag_version" ]; then
        suffix="${tag_version#*-}"
        # Letters, digits and dots only: a further "-" would turn into a Debian
        # revision, and file names must stay plain.
        [[ "$suffix" =~ ^[0-9A-Za-z]+(\.[0-9A-Za-z]+)*$ ]] \
            || die "Tag $release_tag: pre-release suffix '$suffix' may only contain" \
                   "letters, digits and dots (e.g. v$VERSION-rc.1)"
        package_version="$VERSION-$suffix"
        prerelease=true
    fi
fi

echo "version=$VERSION"
echo "package_version=$package_version"
echo "deb_version=${package_version/-/\~}"
echo "prerelease=$prerelease"
echo "release_tag=$release_tag"
