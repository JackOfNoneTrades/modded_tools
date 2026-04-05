#!/usr/bin/env bash

VERSION="$1"

if [ -z "$VERSION" ]; then
  read -p "Enter version name (default: testerino): " VERSION
  VERSION=${VERSION:-testerino}
fi

VERSION="$VERSION" ./gradlew build

