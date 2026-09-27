"""Import a relay bundle: unpack <id>.ytx.zip into the listing cache and raw/.

The relay fetch runs on the user's machine (ytx_relay.bat next to their yt-dlp),
so this machine never contacts YouTube. The bundle holds the listing and the
fetched caption files; after the import every later stage runs with --offline.

Offline stage - no network. Prints the list report plus what the bundle brought.

    python -m ytx.import_bundle --out-dir DIR <bundle.ytx.zip>

Bundle layout - any other member rejects the whole bundle:
    <id>.info.json
    manual/<id>.<lang>.<fmt>
    auto/<id>.<lang>.<fmt>
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

from . import config
from .list_subs import _take_opt, relay_command, source_tracks, summarize, track_id

INFO_MEMBER = re.compile(r"(?P<id>[A-Za-z0-9_-]+)\.info\.json")
CAPTION_MEMBER = re.compile(
    r"(?P<kind>manual|auto)/(?P<id>[A-Za-z0-9_-]+)\.(?P<lang>[A-Za-z0-9_-]+)\.(?P<fmt>[a-z0-9]+)")
FOLDER_MEMBERS = {"manual/", "auto/"}
RAW_FILE = re.compile(r"(?P<lang>[A-Za-z0-9_-]+)\.(?P<kind>manual|auto)\.(?P<fmt>[a-z0-9]+)")


def reject(bundle_path, reason: str):
    raise SystemExit(f"Rejected bundle {bundle_path}: {reason}")


def parse_members(bundle_path, bundle: zipfile.ZipFile):
    """(vid, info member name, [(kind, lang, fmt, member name)]) of a valid bundle.

    Only the documented layout passes. Member names are never used as output
    paths - output paths are built from the parsed parts.
    """
    info_names, captions = [], []
    for name in bundle.namelist():
        normalized = name.replace("\\", "/")
        if normalized in FOLDER_MEMBERS:
            continue
        if match := INFO_MEMBER.fullmatch(normalized):
            info_names.append((match["id"], name))
        elif match := CAPTION_MEMBER.fullmatch(normalized):
            captions.append((match["id"], match["kind"], match["lang"], match["fmt"], name))
        else:
            reject(bundle_path, f"unexpected member {name!r}")
    if len(info_names) != 1:
        reject(bundle_path, f"expected exactly one <id>.info.json, found {len(info_names)}")
    vid, info_name = info_names[0]
    if any(caption_vid != vid for caption_vid, *_ in captions):
        reject(bundle_path, f"caption files belong to another video than {vid}")
    return vid, info_name, [(kind, lang, fmt, name) for _vid, kind, lang, fmt, name in captions]


def tracks_in_raw(vid: str) -> list[str]:
    tracks = []
    for path in sorted(config.RAW_DIR.glob(f"{vid}.*")):
        if match := RAW_FILE.fullmatch(path.name[len(vid) + 1:]):
            track = track_id(match["lang"], match["kind"])
            if track not in tracks:
                tracks.append(track)
    return tracks


def import_bundle(bundle_path: Path) -> dict:
    try:
        bundle = zipfile.ZipFile(bundle_path)
    except (OSError, zipfile.BadZipFile) as err:
        raise SystemExit(f"Cannot open bundle {bundle_path}: {err}")
    with bundle:
        vid, info_name, captions = parse_members(bundle_path, bundle)
        info = json.loads(bundle.read(info_name).decode("utf-8"))
        if info.get("id") != vid:
            reject(bundle_path, f"the listing is for {info.get('id')!r}, not {vid}")

        config.META_DIR.mkdir(parents=True, exist_ok=True)
        config.RAW_DIR.mkdir(parents=True, exist_ok=True)
        (config.META_DIR / f"{vid}.info.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        report = summarize(info)
        (config.META_DIR / f"{vid}.subs.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[import] meta/{vid}.info.json + meta/{vid}.subs.json", file=sys.stderr)

        for kind, lang, fmt, name in captions:
            out = config.RAW_DIR / f"{vid}.{lang}.{kind}.{fmt}"
            if out.exists():
                print(f"  [have ] {out.name} (kept; raw/ is download-once)", file=sys.stderr)
                continue
            data = bundle.read(name)
            out.write_bytes(data)
            print(f"  [saved] {out.name}  ({len(data):,} bytes)", file=sys.stderr)

    present = tracks_in_raw(vid)
    missing = [t["track"] for t in source_tracks(info) if t["track"] not in present]
    report["bundle"] = {
        "path": str(bundle_path),
        "yt_dlp_version": (info.get("_version") or {}).get("version"),
        "tracks_in_raw": present,
        "source_tracks_missing": missing,
        "relay_command": relay_command(vid, ["<track>", "[<track> ...]"]),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config.use_utf8_io()
    config.configure(_take_opt(argv, "--out-dir"))  # where meta/ and raw/ are filled
    if len(argv) != 1:
        print(__doc__)
        return 2
    report = import_bundle(Path(argv[0]).expanduser().resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
