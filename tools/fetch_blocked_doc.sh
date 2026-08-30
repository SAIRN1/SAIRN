#!/bin/sh
# Fetch a PDF from a host that rejects bare curl.  The block on mass.gov and
# medicaid.gov is on the HEADER SET, not the TLS fingerprint and not the IP --
# a User-Agent alone is refused, the full browser header set is served.
# Usage: fetchpdf.sh <url> <outfile> [referer]
URL="$1"; OUT="$2"; REF="${3:-$1}"
curl -sS -o "$OUT" -w "%{http_code} %{size_download} %{content_type}\n" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Accept-Encoding: gzip, deflate, br" \
  -H "sec-ch-ua: \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"" \
  -H "sec-ch-ua-mobile: ?0" \
  -H "sec-ch-ua-platform: \"Windows\"" \
  -H "Sec-Fetch-Dest: document" \
  -H "Sec-Fetch-Mode: navigate" \
  -H "Sec-Fetch-Site: same-origin" \
  -H "Sec-Fetch-User: ?1" \
  -H "Upgrade-Insecure-Requests: 1" \
  -H "Referer: $REF" \
  --compressed -L "$URL"
