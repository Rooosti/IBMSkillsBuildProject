set -a
source .env
set +a

RESP=$(curl -sS -X POST "https://iam.cloud.ibm.com/identity/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=urn:ibm:params:oauth:grant-type:apikey" \
  --data-urlencode "apikey=$WATSONX_API_KEY")

echo "$RESP" | python -m json.tool

echo "$RESP" | python - <<'PY'
import json, sys
data = json.load(sys.stdin)
token = data.get("access_token")
if not token:
    raise SystemExit(f"Token request failed: {data}")
print("TOKEN_OK")
print(token[:30] + "...")
PY
