#!/usr/bin/env bash
# calm_fetch: fetches a URL raw into the workspace's scratchpad/fetched/, and reports it in one line.
# It reads the server's headers first, and a file over the limit is not fetched.
# Usage: calm_fetch.sh <url> [limit_in_megabytes]

default_limit_megabytes=5
fetch_timeout_seconds=120

url=$1
limit_megabytes=${2:-$default_limit_megabytes}
workspace_location=$(pwd -W 2>/dev/null || pwd)
fetched_location="$workspace_location/scratchpad/fetched"
part_location="$fetched_location/calm_fetch_$$.part"

set -e

describe_size() {
  if (( $1 < 1024 )); then
    echo '<1 KB'
  elif (( $1 < 1048576 )); then
    echo "$(( ($1 + 1023) / 1024 )) KB"
  else
    local tenths=$(( ($1 * 10 + 524288) / 1048576 ))
    echo "$(( tenths / 10 )).$(( tenths % 10 )) MB"
  fi
}

read_announcement() {
  # With redirects, every hop sends its own headers; the last hop's count.
  local line
  announced_type=''
  announced_length=''
  while IFS= read -r line; do
    line=${line%$'\r'}
    case ${line,,} in
      http/*) announced_type=''; announced_length='' ;;
      content-type:*) read -r announced_type <<< "${line#*:}"; announced_type=${announced_type%%;*} ;;
      content-length:*) read -r announced_length <<< "${line#*:}" ;;
    esac
  done < <(curl --silent --location --head --max-time "$fetch_timeout_seconds" "$url" || true)
  [[ $announced_length =~ ^[0-9]+$ ]] || announced_length=''
}

choose_file_name() {
  local address=${url#*://} last_part extension='' stem number=1
  address=${address%%[?#]*}
  if [[ $address != */* ]]; then address+=/; fi
  if [[ $address == */ ]]; then address+=index; fi
  last_part=${address##*/}
  if [[ $last_part == *.* ]]; then
    extension=.${last_part##*.}
    address=${address%.*}
  else
    case $1 in
      text/html) extension=.html ;;
      text/plain) extension=.txt ;;
      application/json) extension=.json ;;
      application/pdf) extension=.pdf ;;
    esac
  fi
  # The whole path names the file, and without slashes no URL can place it outside the folder.
  stem=${address//\//_}
  stem=${stem//[^A-Za-z0-9._-]/_}
  extension=${extension//[^A-Za-z0-9.]/_}
  file_name=$stem$extension
  # A fetched file is never overwritten; the next fetch of the same name gets a number.
  while [[ -e $fetched_location/$file_name ]]; do
    number=$((number + 1))
    file_name=${stem}_$number$extension
  done
}

case $url in
  http://*|https://*) ;;
  *) echo 'A URL starts with http:// or https://.'; exit 1 ;;
esac
case $limit_megabytes in
  ''|*[!0-9]*) echo 'The limit is a whole number of megabytes.'; exit 1 ;;
esac
limit_bytes=$(( limit_megabytes * 1048576 ))

read_announcement
if [[ -n $announced_length ]] && (( announced_length > limit_bytes )); then
  echo "${announced_type:-unknown type}, $(describe_size "$announced_length"): over the limit of $limit_megabytes MB, not fetched"
  exit 1
fi

mkdir -p "$fetched_location"
trap 'rm -f "$part_location" "$part_location.error"' EXIT
curl_exit=0
fetch_result=$(curl --silent --show-error --location --fail --max-time "$fetch_timeout_seconds" --max-filesize "$limit_bytes" \
  --output "$part_location" --write-out '%{http_code} %{content_type}' "$url" 2> "$part_location.error") || curl_exit=$?
fetched_type=${fetch_result#* }
fetched_type=${fetched_type%%;*}
case $curl_exit in
  0) ;;
  63) echo "${announced_type:-unknown type}: over the limit of $limit_megabytes MB, not fetched"; exit 1 ;;
  22) echo "${fetch_result%% *} from the server, not fetched"; exit 1 ;;
  *) head -n 1 "$part_location.error"; exit 1 ;;
esac

# Without an announced size, the limit can only be checked after the fetch.
fetched_size=$(stat -c %s "$part_location")
if (( fetched_size > limit_bytes )); then
  echo "${fetched_type:-unknown type}, $(describe_size "$fetched_size"): over the limit of $limit_megabytes MB, not kept"
  exit 1
fi

choose_file_name "$fetched_type"
mv "$part_location" "$fetched_location/$file_name"
echo "${fetched_type:-unknown type}, $(describe_size "$fetched_size") -> $fetched_location/$file_name"
