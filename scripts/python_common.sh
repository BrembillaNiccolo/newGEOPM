#!/usr/bin/env bash

aurora_geopm_python() {
    if [[ -n "${AURORA_GEOPM_PYTHON:-}" ]]; then
        command -v "${AURORA_GEOPM_PYTHON}"
        return
    fi

    for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            command -v "${candidate}"
            return
        fi
    done

    return 1
}
