#!/usr/bin/env bash
set -euo pipefail

# curl_login.sh - Simple login test script for J's Money Backend using curl
#
# Usage:
#   ./curl_login.sh -u <email-or-username> -p <password> \
#     [-b <base_url>] [-m <login|token>] [-t <path>] [-k] [--cacert <file>]
#
# Examples:
#   ./curl_login.sh -u admin@jsmoney.com -p admin123
#   ./curl_login.sh -u admin@jsmoney.com -p admin123 -b http://localhost:8000/api/v1 -m token
#   ./curl_login.sh -u admin@jsmoney.com -p admin123 -t /accounts
#   ./curl_login.sh -u admin@jsmoney.com -p admin123 -b https://jsfamily2.myds.me:40041 -k -t /accounts
#
# Defaults:
#   BASE_URL=http://localhost:8000/api/v1
#   MODE=login            # login: JSON body to /auth/login, token: form to /auth/token
#   TEST_PATH=/accounts   # Protected endpoint to verify the token

BASE_URL="http://localhost:8000/api/v1"
MODE="login"
TEST_PATH="/accounts"
USER=""
PASS=""
INSECURE="0"
CACERT=""

# Internal: curl options accumulator
CURL_OPTS=()

usage() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

while getopts ":b:m:t:u:p:kh-:" opt; do
  case ${opt} in
    b) BASE_URL="$OPTARG" ;;
    m) MODE="$OPTARG" ;;
    t) TEST_PATH="$OPTARG" ;;
    u) USER="$OPTARG" ;;
    p) PASS="$OPTARG" ;;
    k) INSECURE="1" ;;
    -)
      case "${OPTARG}" in
        cacert)
          CACERT="${!OPTIND}"; OPTIND=$(( OPTIND + 1 ))
          ;;
        *) echo "Unknown long option --${OPTARG}" >&2; usage; exit 1 ;;
      esac
      ;;
    h) usage; exit 0 ;;
    :) echo "Option -$OPTARG requires an argument" >&2; usage; exit 1 ;;
    \?) echo "Invalid option: -$OPTARG" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "${USER}" || -z "${PASS}" ]]; then
  echo "Missing credentials: -u <email-or-username> and -p <password> are required" >&2
  usage
  exit 1
fi

normalize_urls() {
  # Ensure BASE_URL has no trailing slash
  BASE_URL="${BASE_URL%/}"
  # Heuristic: append /api/v1 if not present
  if [[ ! "$BASE_URL" =~ /api/[^/]*$ && ! "$BASE_URL" =~ /api/[^/]+/ ]]; then
    BASE_URL="${BASE_URL}/api/v1"
  fi
  # Ensure TEST_PATH starts with '/'
  if [[ -n "$TEST_PATH" && "${TEST_PATH:0:1}" != "/" ]]; then
    TEST_PATH="/${TEST_PATH}"
  fi
}

build_curl_opts() {
  if [[ "$INSECURE" == "1" ]]; then
    CURL_OPTS+=("-k")
  fi
  if [[ -n "$CACERT" ]]; then
    CURL_OPTS+=("--cacert" "$CACERT")
  fi
}

normalize_urls
build_curl_opts

login_with_json() {
  curl -sS "${CURL_OPTS[@]}" -X POST "${BASE_URL}/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${USER}\",\"password\":\"${PASS}\"}"
}

login_with_form() {
  curl -sS "${CURL_OPTS[@]}" -X POST "${BASE_URL}/auth/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=${USER}" \
    --data-urlencode "password=${PASS}"
}

parse_token() {
  local resp="$1"
  if command -v jq >/dev/null 2>&1; then
    echo "$resp" | jq -r '.access_token // empty'
  else
    # Fallback parser if jq is unavailable
    echo "$resp" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
  fi
}

# 1) Login and extract token
RESP=""
case "${MODE}" in
  login) RESP="$(login_with_json)" ;;
  token) RESP="$(login_with_form)" ;;
  *) echo "Invalid MODE: ${MODE} (use: login|token)" >&2; exit 1 ;;
esac

TOKEN="$(parse_token "$RESP")"
if [[ -z "$TOKEN" ]]; then
  echo "Failed to obtain access token. Raw response:" >&2
  echo "$RESP" >&2
  exit 1
fi

echo "[OK] Access token obtained (${#TOKEN} chars)"

# 2) Test a protected endpoint
TMP_BODY="$(mktemp)"
HTTP_CODE=$(curl -sS "${CURL_OPTS[@]}" -w '%{http_code}' -o "$TMP_BODY" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${BASE_URL}${TEST_PATH}") || { rm -f "$TMP_BODY"; exit 1; }

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "[OK] Protected GET ${TEST_PATH} -> HTTP 200"
else
  echo "[WARN] Protected GET ${TEST_PATH} -> HTTP ${HTTP_CODE}"
fi

# Print a compact preview of the response
if command -v jq >/dev/null 2>&1; then
  echo "--- Response preview ---"
  jq 'del(.access_token, .token) | .'
else
  echo "--- Response (first 400 chars) ---"
  head -c 400 "$TMP_BODY" || true
  echo
fi < "$TMP_BODY"

rm -f "$TMP_BODY"

echo "Done."
