#!/usr/bin/env python3
"""Compose a silent 1080p demo video from the live terminal output and screenshots."""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "video/build/work"
CLIPS = WORK / "clips"
FRAMES_OUT = ROOT / "video/frames"
FINAL = ROOT / "video/tripwire-otari-demo.mp4"
ASSETS = Path("/cursor/stores/user/grok-bot/agents/53022d1b-191f-4756-9d2d-343465f99dd6/assets")

W, H, FPS = 1920, 1080, 30
CAP_H = 168
TOKEN_RE = re.compile(r"otk_[A-Za-z0-9_\-]+|tk-[A-Za-z0-9_\-]{8,}|Bearer\s+\S+")

BG = (15, 20, 25)
CARD = (26, 34, 44)
INK = (232, 238, 244)
MUTED = (147, 160, 174)
ACCENT = (110, 168, 255)
ALLOW = (61, 186, 139)
HOLD = (227, 179, 65)
DENY = (224, 92, 92)
LINE = (42, 53, 66)

FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/sand-box/google/IBM Plex Mono/IBMPlexMono-Regular.ttf"
FONT_MONO_BOLD = "/usr/share/fonts/truetype/sand-box/google/IBM Plex Mono/IBMPlexMono-Bold.ttf"

OTARI_SHOTS = {
    "overview": ASSETS / "93f4490386b35504da209bf632c066dd07aa2c00211d1a5871d739161ec48f6a.png",
    "policies": ASSETS / "c8bb281ec6a6c925c2846720985236ab870b382f2772946ca1224d687bb20569.png",
    "tools": ASSETS / "94d106ec76feb509294b79b385c69205081cabf0dc5f9a3876b6315eb80cefe9.png",
}

FIRST_COMMIT = "https://github.com/Cubiczan/tripwire-otari/commit/121db2d06617c267eb3b8c9c34ccce6b47cb28d2"
REPO = "https://github.com/Cubiczan/tripwire-otari"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def scan_text(text: str, label: str) -> None:
    if TOKEN_RE.search(text):
        raise SystemExit(f"token-like string found in {label}")


def scan_file(path: Path) -> None:
    raw = path.read_bytes()
    # Avoid matching random binary that happens to look like 'tk-' in compressed PNG.
    # Check extracted strings of length >= 8 after the prefix, and utf-8 decodable runs.
    text = raw.decode("utf-8", "ignore")
    if TOKEN_RE.search(text):
        # Confirm it's not a false positive inside compressed data by also checking latin-1 strings of printable runs
        printable = "".join(chr(b) if 32 <= b < 127 else "\n" for b in raw)
        if TOKEN_RE.search(printable):
            raise SystemExit(f"token-like string found in {path}")


def canvas(color=BG) -> Image.Image:
    return Image.new("RGB", (W, H), color)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_caption(img: Image.Image, kicker: str, body: str) -> None:
    draw = ImageDraw.ImageDraw(img)
    top = H - CAP_H
    overlay = Image.new("RGB", (W, CAP_H), (10, 14, 18))
    img.paste(overlay, (0, top))
    draw.line([(0, top), (W, top)], fill=ACCENT, width=3)
    kfont = font(FONT_SANS_BOLD, 22)
    bfont = font(FONT_SANS, 28)
    draw.text((48, top + 14), kicker.upper(), fill=ACCENT, font=kfont)
    lines = wrap_text(draw, body, bfont, W - 96)
    y = top + 46
    for line in lines[:3]:
        draw.text((48, y), line, fill=INK, font=bfont)
        y += 36


def fit_shot(path: Path, kicker: str, body: str) -> Image.Image:
    scan_file(path)
    src = Image.open(path).convert("RGB")
    area_h = H - CAP_H
    fitted = ImageOps.contain(src, (W, area_h), Image.Resampling.LANCZOS)
    img = canvas()
    x = (W - fitted.width) // 2
    y = (area_h - fitted.height) // 2
    img.paste(fitted, (x, y))
    draw_caption(img, kicker, body)
    return img


def title_card() -> Image.Image:
    img = canvas()
    draw = ImageDraw.ImageDraw(img)
    # left accent bar
    draw.rectangle([0, 0, 12, H], fill=ACCENT)
    tfont = font(FONT_SANS_BOLD, 96)
    sfont = font(FONT_SANS, 36)
    mfont = font(FONT_SANS, 28)
    sm = font(FONT_SANS, 22)
    draw.text((80, 220), "Tripwire", fill=INK, font=tfont)
    draw.text((80, 350), "A guardrail layer for AI-agent actions", fill=ACCENT, font=sfont)
    lines = [
        "Every model call goes through hosted Otari.ai.",
        "Tripwire then allows, holds, or denies the action",
        "before money can move or a live system is touched.",
        "",
        "Mozilla Otari Hackathon  ·  Developers Wilding",
        "github.com/Cubiczan/tripwire-otari   ·   branch devs-wilding",
    ]
    y = 460
    for i, line in enumerate(lines):
        f = mfont if i < 3 else sm
        color = INK if i < 3 else MUTED
        draw.text((80, y), line, fill=color, font=f)
        y += 44 if i < 3 else 36
    draw.text((80, 980), "Silent picture — voiceover to be added.  Sample vendors are invented.  ALLOW does not move money.", fill=MUTED, font=font(FONT_SANS, 20))
    return img


def end_card() -> Image.Image:
    img = canvas()
    draw = ImageDraw.ImageDraw(img)
    draw.rectangle([0, 0, 12, H], fill=ALLOW)
    draw.text((80, 240), "Tripwire", fill=INK, font=font(FONT_SANS_BOLD, 96))
    draw.text((80, 370), "Public repository", fill=ACCENT, font=font(FONT_SANS, 32))
    draw.text((80, 430), REPO, fill=INK, font=font(FONT_SANS, 36))
    draw.text((80, 500), "Branch: devs-wilding", fill=INK, font=font(FONT_SANS, 32))
    draw.text((80, 600), "First Otari commit", fill=ACCENT, font=font(FONT_SANS, 28))
    draw.text((80, 648), FIRST_COMMIT, fill=INK, font=font(FONT_MONO, 22))
    draw.text((80, 820), "Every decision is in a hash-chained audit log.", fill=MUTED, font=font(FONT_SANS, 28))
    draw.text((80, 870), "Thanks.", fill=INK, font=font(FONT_SANS_BOLD, 40))
    return img


def terminal_base() -> tuple[Image.Image, int, int, int]:
    """Return a chrome terminal background and the text origin + row height + cols width."""
    img = canvas((13, 17, 23))
    draw = ImageDraw.ImageDraw(img)
    # title bar
    draw.rectangle([0, 0, W, 48], fill=(30, 36, 44))
    for i, color in enumerate([(224, 81, 81), (227, 179, 65), (61, 186, 139)]):
        draw.ellipse([18 + i * 22, 16, 32 + i * 22, 30], fill=color)
    tf = font(FONT_SANS, 18)
    title = "tripwire-otari  —  OTARI_MODE=live python scripts/demo.py"
    draw.text((100, 13), title, fill=MUTED, font=tf)
    return img, 28, 68, 28  # left, top, row_h


def color_for_line(line: str) -> tuple[int, int, int]:
    if " allow " in f" {line} " or line.strip().endswith(" yes    ok") or "[yes]" in line:
        if "allow    allow    yes" in line or line.startswith("allow_routine") or line.startswith("fallback_routing"):
            return ALLOW
    if " hold " in f" {line.lower()} " or "  hold " in line or line.startswith("hold_") or "soft" in line[:60]:
        if line[:24].strip() in {"hold_over_threshold", "line_total_mismatch", "unknown_vendor", "budget_exhausted", "guardrail_block"}:
            return HOLD
    if line.startswith("deny_") or "  deny " in f" {line} ":
        return DENY
    if line.startswith("  [yes]"):
        return ALLOW
    if line.startswith("  [ no]"):
        return MUTED
    if "LIVE" in line or "Key budget" in line or "Usage after" in line:
        return ACCENT
    if line.startswith("Honesty") or line.startswith("- "):
        return MUTED
    return INK


def caption_for_progress(shown: str) -> tuple[str, str]:
    if "Honesty notes:" in shown or "Otari catalog guardrails" in shown:
        return (
            "Honest gaps",
            "Web search was not used (no search provider). Otari catalog guardrails need an outside vendor key, so Tripwire’s own policy gate is the guardrail layer. No second-key budget is attached.",
        )
    if "Otari features exercised" in shown:
        return (
            "Otari features in this run",
            "Used live: two open-weight models, the tripwire-analyst routing policy, web fetch, code execution, and the $1.00 key budget. Not claimed: web search, catalog guardrails, or per-user budgets.",
        )
    if "fallback_routing" in shown and "budget_exhausted" in shown:
        return (
            "Soft gaps and routing",
            "The west-agent budget and catalog-guardrail cases stay documented soft holds. Analyst chats still went through the tripwire-analyst policy; Otari served the primary model.",
        )
    if "deny_country" in shown and "ofac_fetch" in shown:
        return (
            "Blocked-country deny + OFAC fetch",
            "A blocked-country payee is denied by the policy gate. One official OFAC page fetch corroborates the North Korea sanctions program. Page content is treated as untrusted evidence.",
        )
    if "allow_routine" in shown and "hold_over_threshold" in shown:
        return (
            "Live decisions",
            "A $185 carton invoice is allowed after Otari code execution re-sums the lines. A $2,400 fixture invoice is held over the review threshold; the verifier may only tighten.",
        )
    if "Key budget" in shown or "Usage after" in shown:
        return (
            "Spend and key budget",
            "Code execution and web fetch are the main costs, at $0.01 a call, so the demo runs each once. The tripwire-otari key’s $1.00 monthly ceiling is read back from GET /key/budget.",
        )
    return (
        "Fresh live run on hosted Otari.ai",
        "OTARI_MODE=live python scripts/demo.py. Two open-weight models in distinct roles. Analyst chats go through the tripwire-analyst Fallback policy.",
    )


def render_terminal_clip(log_text: str, dest: Path, target_secs: float = 58.0) -> None:
    scan_text(log_text, "demo log")
    lines = log_text.splitlines()
    # Build a list of visible-line-count states. Reveal one line at a time,
    # with longer holds on key lines.
    events: list[tuple[int, int]] = []  # (n_lines_visible, frames)
    for i, line in enumerate(lines, start=1):
        hold = 4  # default ~133ms
        if i <= 12:
            hold = 7
        if line.startswith("Scenario") or line.startswith("-----"):
            hold = 10
        if line[:24].strip() in {
            "allow_routine",
            "hold_over_threshold",
            "deny_country",
            "deny_over_max",
            "line_total_mismatch",
            "unknown_vendor",
            "budget_exhausted",
            "guardrail_block",
            "fallback_routing",
        }:
            hold = 22
        if line.startswith("  models:") or line.startswith("  ofac_fetch:") or line.startswith("  note:"):
            hold = 16
        if "Key budget" in line or "Usage after" in line or "Routing policy" in line:
            hold = 20
        if line.startswith("Otari features") or line.startswith("  [yes]") or line.startswith("  [ no]"):
            hold = 8
        if line.startswith("Honesty") or line.startswith("- "):
            hold = 10
        if line.startswith("Finished") or line.startswith("Audit chain"):
            hold = 18
        events.append((i, hold))

    total_frames = sum(fr for _, fr in events)
    # If too short/long, scale holds so the clip lands near target_secs.
    desired = int(target_secs * FPS)
    # Leave a 2s dwell on the final frame.
    scale = max(0.6, min(1.7, (desired - 2 * FPS) / max(total_frames, 1)))
    events = [(n, max(2, int(round(fr * scale)))) for n, fr in events]
    # final dwell
    events.append((len(lines), 2 * FPS))

    row_count = 24
    mono = font(FONT_MONO, 20)
    # Measure character width
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    char_w = probe.textlength("M", font=mono)

    raw = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            str(dest),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert raw.stdin is not None

    def frame_for(n: int) -> Image.Image:
        visible = lines[:n]
        start = max(0, len(visible) - row_count)
        window = visible[start:]
        base, left, top, row_h = terminal_base()
        img = base
        draw = ImageDraw.ImageDraw(img)
        y = top
        max_chars = int((W - left * 2) / max(char_w, 1))
        for line in window:
            # hard wrap just in case
            chunks = [line[i : i + max_chars] for i in range(0, max(len(line), 1), max_chars)] or [""]
            color = color_for_line(line)
            for chunk in chunks:
                draw.text((left, y), chunk, fill=color, font=mono)
                y += row_h
        shown = "\n".join(visible)
        kicker, body = caption_for_progress(shown)
        draw_caption(img, kicker, body)
        return img

    try:
        last_n = None
        last_bytes = None
        for n, frames in events:
            if n != last_n:
                img = frame_for(n)
                last_bytes = img.tobytes()
                last_n = n
            for _ in range(frames):
                raw.stdin.write(last_bytes)
        raw.stdin.close()
        err = raw.stderr.read()
        code = raw.wait()
        if code != 0:
            sys.stderr.write(err.decode("utf-8", "replace")[-2000:])
            raise SystemExit(f"ffmpeg terminal clip failed: {code}")
    finally:
        if raw.stdin and not raw.stdin.closed:
            raw.stdin.close()


def still_clip(img: Image.Image, dest: Path, seconds: float) -> None:
    png = dest.with_suffix(".png")
    img.save(png, "PNG")
    scan_file(png)
    frames = max(1, int(round(seconds * FPS)))
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(png),
            "-t",
            f"{frames / FPS:.3f}",
            "-r",
            str(FPS),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-vf",
            f"scale={W}:{H}:flags=lanczos,fps={FPS}",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def concat_and_audio(clips: list[Path], dest: Path) -> None:
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    silent = WORK / "silent.mp4"
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-movflags",
            "+faststart",
            str(silent),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def extract_samples(video: Path) -> None:
    FRAMES_OUT.mkdir(parents=True, exist_ok=True)
    # duration
    info = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=width,height,codec_type,codec_name,sample_rate,channels",
            "-of",
            "json",
            str(video),
        ]
    )
    data = json.loads(info)
    duration = float(data["format"]["duration"])
    # four evenly spaced frames in the body of the video
    times = [duration * x for x in (0.08, 0.32, 0.58, 0.84)]
    for i, t in enumerate(times, start=1):
        out = FRAMES_OUT / f"frame_{i:02d}.png"
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{t:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(out),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        scan_file(out)
    print(json.dumps({"duration": duration, "probe": data}, indent=2))


def main() -> None:
    CLIPS.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "docs/demo_run_live.txt"
    log_text = log_path.read_text()
    scan_text(log_text, str(log_path))

    clips: list[Path] = []

    # 1. Title
    p = CLIPS / "01_title.mp4"
    still_clip(title_card(), p, 9.0)
    clips.append(p)

    # 2. Dashboard live banner + decisions
    p = CLIPS / "02_dashboard.mp4"
    still_clip(
        fit_shot(
            WORK / "dashboard/overview.png",
            "Tripwire dashboard — LIVE",
            "The local dashboard is in LIVE mode. Every model call goes to hosted Otari.ai. ALLOW records intent only — no payment rail is connected.",
        ),
        p,
        11.0,
    )
    clips.append(p)

    # 3. Terminal live run
    p = CLIPS / "03_terminal.mp4"
    render_terminal_clip(log_text, p, target_secs=62.0)
    clips.append(p)

    # 4. Otari overview
    p = CLIPS / "04_otari_overview.mp4"
    still_clip(
        fit_shot(
            OTARI_SHOTS["overview"],
            "Otari workspace Overview",
            "Default workspace on hosted Otari.ai. This Overview capture was taken before usage appeared in the filters. Live spend and the $1.00 key budget are in the demo output.",
        ),
        p,
        11.0,
    )
    clips.append(p)

    # 5. Policies
    p = CLIPS / "05_otari_policies.mp4"
    still_clip(
        fit_shot(
            OTARI_SHOTS["policies"],
            "Otari Fallback policy — tripwire-analyst",
            "Main model: Xiaomi MiMo V2.6 Flash. Backup: GLM-5.3-Flash. All live analyst chats use this policy name. The client still retries on the named analyst model if the policy request fails.",
        ),
        p,
        14.0,
    )
    clips.append(p)

    # 6. Tools
    p = CLIPS / "06_otari_tools.mp4"
    still_clip(
        fit_shot(
            OTARI_SHOTS["tools"],
            "Otari web tools",
            "Workspace web access is on. This run used builtin_fetch once on the blocked-country invoice. Web search is listed available, but no search provider key is configured, so search was not used.",
        ),
        p,
        13.0,
    )
    clips.append(p)

    # 7. Routine allow (dashboard still — same overview, different caption)
    p = CLIPS / "07_allow.mp4"
    still_clip(
        fit_shot(
            WORK / "dashboard/overview.png",
            "Routine allow + code execution",
            "A $185 carton invoice from an allowlisted vendor. The books tools find a matching open bill. Otari code execution re-sums the lines. Analyst and verifier both allow it.",
        ),
        p,
        13.0,
    )
    clips.append(p)

    # 8. Hold + approve
    hold_src = WORK / "dashboard/holds_open.png"
    if not hold_src.exists():
        hold_src = WORK / "dashboard/overview.png"
    p = CLIPS / "08_hold.mp4"
    still_clip(
        fit_shot(
            hold_src,
            "Hold over threshold",
            "A $2,400 fixture invoice is over the review threshold, so it is held. Approving a hold records intent only — nothing is paid.",
        ),
        p,
        13.0,
    )
    clips.append(p)

    approved = WORK / "dashboard/holds_approved.png"
    if approved.exists():
        p = CLIPS / "08b_approved.mp4"
        still_clip(
            fit_shot(
                approved,
                "Approval records intent only",
                "The hold is resolved in the audit trail. No payment rail is connected, so an approval does not move money.",
            ),
            p,
            8.0,
        )
        clips.append(p)

    # 9. Deny / OFAC — reuse terminal end? Use dashboard overview with deny rows visible (top of table).
    p = CLIPS / "09_deny.mp4"
    still_clip(
        fit_shot(
            WORK / "dashboard/overview.png",
            "Country deny, OFAC fetch, and hard cap",
            "A blocked-country payee is denied, corroborated by one official OFAC page fetch. A $12,000 invoice is over the hard cap and is denied without extra model calls.",
        ),
        p,
        13.0,
    )
    clips.append(p)

    # 10. Features / honest gaps
    feat = WORK / "dashboard/features.png"
    if not feat.exists():
        feat = WORK / "dashboard/overview.png"
    p = CLIPS / "10_gaps.mp4"
    still_clip(
        fit_shot(
            feat,
            "Honest gaps",
            "Not claimed in this run: web search, Otari catalog guardrails (every option needs a vendor key; Tripwire’s policy gate is the guardrail layer), and a per-user / second-key budget.",
        ),
        p,
        16.0,
    )
    clips.append(p)

    # 11. Audit
    audit = WORK / "dashboard/audit.png"
    if not audit.exists():
        audit = WORK / "dashboard/overview.png"
    p = CLIPS / "11_audit.mp4"
    still_clip(
        fit_shot(
            audit,
            "Hash-chained audit log",
            "Every decision is written to a hash-chained audit log. Verifying the chain on the dashboard returns OK.",
        ),
        p,
        10.0,
    )
    clips.append(p)

    # 12. GitHub
    p = CLIPS / "12_github.mp4"
    still_clip(
        fit_shot(
            WORK / "github_repo.png",
            "Public repository",
            "github.com/Cubiczan/tripwire-otari, default branch devs-wilding. The first Otari commit on this branch is 121db2d.",
        ),
        p,
        12.0,
    )
    clips.append(p)

    # 13. End card
    p = CLIPS / "13_end.mp4"
    still_clip(end_card(), p, 10.0)
    clips.append(p)

    FINAL.parent.mkdir(parents=True, exist_ok=True)
    concat_and_audio(clips, FINAL)
    scan_file(FINAL)
    extract_samples(FINAL)
    print(f"Wrote {FINAL}")


if __name__ == "__main__":
    main()
