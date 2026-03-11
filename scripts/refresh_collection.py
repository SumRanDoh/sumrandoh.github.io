#!/usr/bin/env python3
"""
Refresh the website's Collection sections from the Prismatics game repo.
Run when you want to sync game piece images and metadata (titles, rules).

Usage: python scripts/refresh_collection.py

Copies images from: /Users/caleb/Prismatics/prismatics/assets/images/
Writes to: assets/images/collection/
"""

import os
import re
import json
import shutil
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

GAME_REPO = Path("/Users/caleb/Prismatics/prismatics")
WEBSITE = Path(__file__).resolve().parent.parent

# Category order matches collection.gd CATEGORY_TO_VARIANTS_KEY and tscn button order
CATEGORIES = [
    ("Components", "Component"),
    ("Component Upgrades", "ComponentUpgrade"),
    ("Workers", "Worker"),
    ("Worker Upgrades", "WorkerUpgrade"),
    ("Operations", "Operation"),
    ("Challenges", "Challenge"),
]

# Variant keys and image mapping per category (from parameters.gd + collection.gd _get_variant_keys)
CHALLENGE_VARIANTS = ["Backorder", "Flooding", "FloorHazard", "ForcedUpdate", "Renovations", "Sinkhole", "StrangeStench"]
COMPONENT_VARIANTS = [
    ("common", "Conveyor"), ("common", "Packager"),
    ("uncommon", "Fabricator"),
    ("rare", "Divider"), ("rare", "Launcher"),
    ("legendary", "Attractor"),
]
COMPONENT_COLORS = ["red", "blue", "green", "yellow"]
COMP_UPGRADE_VARIANTS = [
    ("SelfBuff", "boost"), ("RowBuff", "horiz"), ("ColumnBuff", "vert"), ("AdjacentBuff", "adjacent"),
]
RARITIES = ["common", "uncommon", "rare", "legendary"]

# Game palette hex (parameters.gd): rarities + version 1.0 (green for website) and money
PALETTE_HEX = {
    "common": "ffa500",
    "uncommon": "b353fc",
    "rare": "00f0f0",
    "legendary": "f03cf0",
    "version_1_0": "25bf17",  # green for version numbers (game uses gray at 1.0; site uses green)
    "money": "ffd147",
}
OPERATION_VARIANTS = [
    ("common", "Redshift", "Blueshift", "Greenshift", "Yellowshift", "Clockwise", "Blockwise"),
    ("uncommon", "Fabricatorize", "MeltDown"),
    ("rare", "CarbonCopy", "Dividerize", "Launcherize"),
    ("legendary", "Attractorize"),
]
WORKER_VARIANTS = [
    ("common", ["Accountant", "Janitor", "Maintenance", "Marketer", "RedMechanic", "BlueMechanic", "GreenMechanic", "YellowMechanic", "UpLineworker", "DownLineworker", "LeftLineworker", "RightLineworker", "CapacityManager", "DistributionManager", "LogisticsManager", "UpperLevelManager", "LowerLevelManager", "WeldingManager", "TransportManager"]),
    ("uncommon", ["Headhunter", "Receptionist", "Recruiter", "ComponentDeveloper", "OperationDeveloper", "VerticalDirector", "HorizontalDirector", "DivisionOverseer", "SectionOverseer", "ReceivingSupervisor", "SafetySupervisor"]),
    ("rare", ["RedResearcher", "GreenResearcher", "BlueResearcher", "YellowResearcher", "Assembler", "GraphicDesigner", "InventoryClerk", "LoadPlanner", "PackagingSpecialist", "LiquidationDeveloper", "IndustrialEngineer", "MechanicalEngineer", "ChemicalEngineer", "AutomationTechnician", "InstrumentationTechnician", "MechatronicsTechnician"]),
    ("legendary", ["Chef", "ChiefExecutiveOfficer", "DataScientist", "FabricationSpecialist", "ProcurementAgent", "ReplicationDeveloper", "RoboticsExpert"]),
]
WORKER_UPGRADE_VARIANTS = [
    ("common", "Commendation", "PriorityUplink", "PriorityDownlink", "PriorityLeftlink", "PriorityRightlink"),
    ("uncommon", "AdaptiveCache", "FreshInstall", "RotationalLink"),
    ("rare", "BackupPower", "IterativeCalibration"),
    ("legendary", "SatelliteLink"),
]


def to_snake(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


def to_title(s: str) -> str:
    """Convert CamelCase or snake_case to Title Case."""
    s = re.sub(r"(?<!^)(?=[A-Z])", " ", s)
    return s.replace("_", " ").title()


def strip_bbcode(text: str) -> str:
    """Remove Godot BBcode tags for HTML display."""
    text = re.sub(r"\[color=[^\]]+\]", "", text)
    text = re.sub(r"\[/color\]", "", text)
    text = re.sub(r"\[font_size=\d+\]", "", text)
    text = re.sub(r"\[/font_size\]", "", text)
    text = re.sub(r"\[/font\]", "", text)
    return text.strip()


def _parse_gd_format_args(array_str: str) -> list:
    """Parse GDScript format array after ' % [' for 1.0 non-upgraded Worker. Returns list of values."""
    # Split by comma, respecting nested brackets
    parts = []
    depth = 0
    current = []
    for c in array_str.strip():
        if c in "([{":
            depth += 1
            current.append(c)
        elif c in ")]}":
            depth -= 1
            current.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(c)
    if current:
        parts.append("".join(current).strip())

    values = []
    for p in parts:
        p = p.strip()
        if "version_color" in p:
            values.append(PALETTE_HEX["version_1_0"])
        elif "actual.n * 10" in p or "n * 10" in p:
            values.append(10)
        elif "n + 1" in p or "n+1" in p:
            values.append(2)  # n+1 for n=1
        elif "actual.n" in p or (re.match(r"^\s*n\s*[,\]\)]", p) or p.strip() == "n"):
            values.append(1)
        elif "adjusted" in p:
            values.append(1)
        elif "plrl" in p:
            values.append("")  # n=1 -> no plural
        elif "money" in p and "palette" in p:
            values.append(PALETTE_HEX["money"])
        elif "uncommon" in p and "palette" in p:
            values.append(PALETTE_HEX["uncommon"])
        elif "rare" in p and "palette" in p and "legendary" not in p:
            values.append(PALETTE_HEX["rare"])
        elif "legendary" in p and "palette" in p:
            values.append(PALETTE_HEX["legendary"])
        elif "copied.variant" in p or "set_rules" in p:
            values.append("—")  # placeholder for copy workers; use fallback
        else:
            values.append(1)  # default for %d / %0.0f
    return values


def bbcode_color_to_html(text: str) -> str:
    """Convert [color=#hex]...[/color] to <span style="color:#hex">...</span>; escape rest; strip other BBcode."""
    text = re.sub(r"\[font_size=\d+\]", "", text)
    text = re.sub(r"\[/font_size\]", "", text)
    text = re.sub(r"\[/font\]", "", text)
    text = re.sub(r"\[center\]", "", text)
    text = re.sub(r"\[/center\]", "", text)
    parts = re.split(r"(\[color=#([a-fA-F0-9]+)\](.*?)\[/color\])", text, flags=re.DOTALL)
    result = []
    for i in range(len(parts)):
        if i % 4 == 0:
            result.append(html_escape(parts[i]))
        elif i % 4 == 2:
            hex_val = parts[i]
            inner = parts[i + 1]
            result.append(f'<span style="color:#{hex_val}">{html_escape(inner)}</span>')
    return "".join(result).strip()


def extract_reminders_from_worker_class(class_path: Path) -> list:
    """Extract reminders.push_back('...') templates; return list of strings with version_color substituted."""
    if not class_path.exists():
        return []
    content = class_path.read_text()
    reminders = []
    # Group 1: string content (no double quotes in GDScript single-quoted string); group 2: optional % [...]
    for m in re.finditer(
        r"reminders\.push_back\s*\(\s*'((?:[^'\\]|\\.)*)'\s*(?:%\s*\[([^\]]+)\])?\s*\)", content
    ):
        template = m.group(1).replace("\\n", "\n").replace("%%", "%")
        args_str = m.group(2) if m.lastindex >= 2 and m.group(2) else ""
        if args_str and "version_color" in args_str:
            template = template.replace("%s", PALETTE_HEX["version_1_0"], 1)
        if "%d" in template and "hard_cap" in args_str:
            template = re.sub(r"%d", "10", template)
        if "%s" in template and "version_color" not in args_str:
            template = template.replace("%s", PALETTE_HEX["version_1_0"])
        reminders.append(template)
    return reminders


def build_worker_rules_and_reminders(cls_path: Path, variant: str) -> str:
    """Build full_rules_text + '\\n' + full_reminders_text for 1.0 non-upgraded Worker, with version numbers in green (HTML)."""
    content = cls_path.read_text() if cls_path.exists() else ""

    # Recruiter: built from st (version-colored n) + rarity-colored words; no single format line
    if variant == "Recruiter":
        v = PALETTE_HEX["version_1_0"]
        u, r, l = PALETTE_HEX["uncommon"], PALETTE_HEX["rare"], PALETTE_HEX["legendary"]
        st = f"[color=#{v}]1[/color]"
        rules_text = (
            f"Add {st} [color=#{u}]uncommon[/color], {st} [color=#{r}]rare[/color], & {st} [color=#{l}]legendary[/color] pip "
            "to each pack distribution"
        )
        rules_text = bbcode_color_to_html(rules_text)
        reminders = extract_reminders_from_worker_class(cls_path)
        reminder_parts = [bbcode_color_to_html(r) if "[color=#" in r else html_escape(r) for r in reminders]
        full = rules_text + ("\n" + "\n".join(reminder_parts) if reminder_parts else "")
        return full

    # Two-part: var ret = '...' or "..." then ret += '...' % [...] (Horizontal Director, MechatronicsTechnician, Maintenance, etc.)
    two_part = re.search(
        r"(?:var ret = '([^']*)'|var ret = \"([^\"]*)\")\s+"
        r"ret \+= '([^']*(?:\\.[^']*)*)'\s*\\?\s*%\s*\[(.*?)\]\s*(?=\)|\n)",
        content,
        re.DOTALL,
    )
    if two_part:
        part1 = (two_part.group(1) or two_part.group(2) or "").replace("\\n", "\n")
        part2_template = two_part.group(3).replace("\\n", "\n")
        format_args_str = two_part.group(4).strip().replace("\n", " ")
        if "set_rules" not in format_args_str and "copied.variant" not in format_args_str:
            try:
                values = _parse_gd_format_args(format_args_str)
                part2_template_safe = part2_template.replace("%%", "\x00")
                part2 = part2_template_safe % tuple(values)
                part2 = part2.replace("\x00", "%")
                rules_text = part1 + part2
                rules_text = polish_rules_for_website(rules_text, variant, "Worker")
                if "[color=#" in rules_text:
                    rules_text = bbcode_color_to_html(rules_text)
                reminders = extract_reminders_from_worker_class(cls_path)
                reminder_parts = [bbcode_color_to_html(r) if "[color=#" in r else html_escape(r) for r in reminders]
                full = rules_text + ("\n" + "\n".join(reminder_parts) if reminder_parts else "")
                return full
            except (TypeError, ValueError):
                pass

    # Get main rules string: var ret = '...' % [...] or ret += '...' % [...]
    rules_template = None
    format_args_str = None
    # Allow optional backslash + newline (GDScript line continuation) between string and % [
    # Args array may contain ] e.g. in palette['rare'].to_html(); capture until ] then ) or newline
    for pattern in [
        r"var ret = '([^']*(?:\\.[^']*)*)'\s*\\?\s*%\s*\[(.*?)\]\s*(?=\)|\n)",
        r'var ret = "([^"]*(?:\\.[^"]*)*)"\s*\\?\s*%\s*\[(.*?)\]\s*(?=\)|\n)',
    ]:
        m = re.search(pattern, content)
        if m:
            rules_template = m.group(1).replace("\\n", "\n")
            format_args_str = m.group(2)
            break
    if not rules_template:
        m = re.search(
            r"(?:var )?ret \+= '([^']*(?:\\.[^']*)*)'\s*\\?\s*%\s*\[(.*?)\]\s*(?=\)|\n)",
            content,
        )
        if m:
            rules_template = m.group(1).replace("\\n", "\n")
            format_args_str = m.group(2)
    if not rules_template:
        for m in re.finditer(r"(?:var )?ret = '([^']*(?:\\.[^']*)*)'", content):
            if len(m.group(1)) > 10 and "%" in m.group(1):
                rules_template = m.group(1).replace("\\n", "\n")
                break

    use_format_args = (
        rules_template
        and format_args_str
        and "set_rules" not in format_args_str
        and "copied.variant" not in format_args_str
    )
    if use_format_args:
        try:
            values = _parse_gd_format_args(format_args_str)
            rules_template_safe = rules_template.replace("%%", "\x00")
            rules_text = rules_template_safe % tuple(values)
            rules_text = rules_text.replace("\x00", "%")
        except (TypeError, ValueError):
            raw = extract_rules_from_class(cls_path)
            rules_text = apply_rules_defaults(raw, "Worker", variant=variant)
    else:
        raw = extract_rules_from_class(cls_path)
        rules_text = apply_rules_defaults(raw, "Worker", variant=variant)

    rules_text = polish_rules_for_website(rules_text, variant, "Worker")
    if use_format_args and "[color=#" in rules_text:
        rules_text = bbcode_color_to_html(rules_text)
    # Plain-text rules are escaped when output in generate_collection_html

    reminders = extract_reminders_from_worker_class(cls_path)
    reminder_parts = []
    for r in reminders:
        r = bbcode_color_to_html(r) if "[color=#" in r else html_escape(r)
        reminder_parts.append(r)
    reminder_text = "\n".join(reminder_parts)

    full = rules_text.strip()
    if reminder_text:
        full = full + "\n" + reminder_text
    return full


def apply_rules_defaults(text: str, category: str, variant: str = "", color: str = "", rarity: str = "") -> str:
    """Fill in nice-looking defaults for %d, %s, %0.0f etc. like the game does in-game."""
    text = text.replace("\\n", " ").replace("  ", " ")
    color = color or "red"
    direction = "rightward"
    direction_from = "the left"

    # Order matters: replace %% first to preserve literal %
    text = text.replace("%%", "\x00")
    if category == "Component":
        text = re.sub(r"%d", "1", text)
        # Replace %s in order: Conveyor (color, direction), Packager (direction_from, color, color), Fabricator (direction)
        # Launcher/Attractor: "the tile %s it" or "the two tiles %s it" -> from_dir (to the right of, above, etc)
        from_dir = "to the right of"  # default for facing right
        replacements = []
        if "the tile %s it" in text or "the two tiles %s it" in text:
            replacements = [from_dir, color, direction]  # Launcher, Attractor
        elif "from %s" in text:
            replacements = [direction_from, color, color]  # Packager with direction
        elif "into %s score multiplier" in text:
            replacements = [color, color]  # Packager (LoadPlanner variant)
        elif "moves them %s" in text:
            replacements = [color, direction]  # Conveyor
        elif "moves it %s" in text:
            replacements = [color, direction]  # Fabricator
        elif "moves them each" in text:
            replacements = []  # Fabricator (ProcurementAgent) - no %s
        else:
            replacements = [color, direction]
        for r in replacements:
            text = text.replace("%s", r, 1)
    elif category == "Challenge":
        if "corner" in text:
            text = text.replace("%s", "top left")
        elif "just" in text:
            text = text.replace("%s", "above")  # Sinkhole
        elif "tiles" in text and "%d" in text:
            text = text.replace("%d", "5")  # Floor Hazard
        elif "offices" in text:
            text = text.replace("%s", "left half")
        else:
            text = re.sub(r"%d", "1", text)
            text = re.sub(r"%s", "—", text)
    elif category == "Worker":
        text = re.sub(r"%0\.0f%%", "10%", text)  # Accountant: interest
        text = re.sub(r"%0\.0f", "1", text)
        text = re.sub(r"%d", "1", text)
        if "same %s as" in text:
            text = text.replace("%s", "row or column", 1)
        elif "cannot draw %s" in text:
            text = text.replace("%s", "one color of", 1)
        else:
            text = re.sub(r"%s", "1", text)  # version_color, plrl, n - use 1 as default
    elif category == "WorkerUpgrade":
        if "directly %s" in text:
            text = text.replace("%s", "to the right of", 1)
        elif "two offices %s" in text:
            text = text.replace("%s", "to the right of", 1)
        else:
            text = re.sub(r"%s", "—", text)
        text = re.sub(r"%d", "1", text)
        text = re.sub(r"%0\.0f", "1", text)
    else:
        text = re.sub(r"%d", "1", text)
        text = re.sub(r"%0\.0f", "1", text)
        text = re.sub(r"%s", "—", text)
    text = text.replace("\x00", "%")
    return strip_bbcode(text)


def polish_rules_for_website(rules: str, variant: str, category: str) -> str:
    """Clean up rules for website display - fix placeholders, truncation, and unclear text."""
    WORKER_FALLBACKS = {
        "Recruiter": "Add 1 uncommon, 1 rare, & 1 legendary pip to each pack distribution",
        "DivisionOverseer": "Non-upgraded corners of the Worker to the left of this one act upgraded, giving +1",
        "SectionOverseer": "Non-upgraded corners of the Worker above this one act upgraded, giving +1",
        "HorizontalDirector": "Workers to the right of this one get +1",
        "LoadPlanner": "Packagers can accept numbers from any direction",
        "Chef": "Non-upgraded corners of Workers in the top row act upgraded, giving +1",
        "ProcurementAgent": "Fabricators produce numbers out of all sides",
        "RoboticsExpert": "Duplicate workers can appear in the store or in packs",
        "ComponentDeveloper": "Can embed a component from your hand. Components cost ⚡1 less",
        "OperationDeveloper": "Can embed an operation from the store. Operations cost ⚡1 less",
        "ReplicationDeveloper": "Can embed a component from your hand. Upon entering the store, add 1 copy of the embedded component to your deck",
        "IndustrialEngineer": "Copy the worker directly above this one",
        "MechanicalEngineer": "Copy the worker directly to the left of this one",
        "ChemicalEngineer": "Copy the worker diagonally to the top left of this one",
        "LiquidationDeveloper": "Can embed a component from your hand. Upon entering the store, sell it for ⚡1",
        "Maintenance": "The first component you discard each hand pays an additional ⚡1",
        "ReceivingSupervisor": "The worker directly to the right of this one gets +1 and +1",
        "SafetySupervisor": "The worker directly below this one gets +1 and +1",
        "MechatronicsTechnician": "Whenever a number's movement direction changes, conveyors get +1 until the end of the month",
    }
    WORKER_UPGRADE_FALLBACKS = {
        "FreshInstall": "This worker gets +3. Upgrade discarded after 3 months",
    }
    if not rules or not rules.strip():
        return WORKER_FALLBACKS.get(variant, "") if category == "Worker" else (WORKER_UPGRADE_FALLBACKS.get(variant, "") if category == "WorkerUpgrade" else "")
    if category == "WorkerUpgrade" and variant in WORKER_UPGRADE_FALLBACKS and rules.strip() == "This worker gets +3":
        return WORKER_UPGRADE_FALLBACKS[variant]
    # Fix common bad patterns from placeholder substitution
    rules = re.sub(r"(\d) time1$", r"\1 time", rules)
    rules = re.sub(r"(\d) time1\.0", r"\1 time", rules)
    rules = re.sub(r"gain 1% interest", "gain 10% interest", rules)
    # Only fix mistaken "Add 1+1" from placeholder; leave "Add 3+1" etc. (Headhunter) intact
    rules = re.sub(r"Add 1\+1 rare", "Add 1 rare", rules)
    rules = re.sub(r"Add 1\+1\.0 rare", "Add 1 rare", rules)
    rules = re.sub(r"ontop", "on top", rules)
    rules = re.sub(r"max refill1", "max refill", rules)
    rules = re.sub(r"You cannot draw 1 components", "You cannot draw one color of components", rules)
    rules = re.sub(r"in the same 1 as them", "in the same row or column as them", rules)
    rules = re.sub(r"1 additional numbers", "1 additional number", rules)
    # Override bad/truncated rules even when non-empty
    if variant in WORKER_FALLBACKS and (
        rules.strip() == "+1.0" or
        len(rules.strip()) < 20 or
        "Copying the 1 " in rules or
        "1 1 of the embedded" in rules or
        (variant == "MechatronicsTechnician" and "conveyors" not in rules) or
        (variant == "ComponentDeveloper" and "Can embed" not in rules) or
        (variant == "OperationDeveloper" and "Can embed" not in rules) or
        (variant == "ReplicationDeveloper" and "Upon entering" not in rules)
    ):
        return WORKER_FALLBACKS[variant]
    return rules


def extract_rules_from_class(class_path: Path) -> str:
    """Extract rules = '...' or ret = '...' from a GDScript class file."""
    if not class_path.exists():
        return ""
    content = class_path.read_text()
    # Use backreference \1 so "can't" doesn't end the match on the apostrophe
    m = re.search(r'''^\s*rules\s*=\s*(["'])(.+?)\1''', content, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(2)
    # Workers use ret = '...' % [...] in set_rules(); find the main ret assignment
    for pattern in [
        r"var ret = '([^']*(?:\\.[^']*)*)'",
        r'var ret = "([^"]*(?:\\.[^"]*)*)"',
        r"ret = '([^']*(?:\\.[^']*)*)'",
        r"ret \+= '([^']*(?:\\.[^']*)*)'",
    ]:
        for m in re.finditer(pattern, content):
            s = m.group(1)
            if len(s) > 15 and "%" in s:  # likely the rules string
                return s
    return ""


def add_emblem_outline(img_path: Path) -> bool:
    """
    Add an outline that hugs the shape of the emblem in upgrade images.
    Draws in transparent pixels adjacent to non-transparent emblem pixels,
    using the dominant non-black color. Does not cover the emblem's black edge.
    """
    if not HAS_PIL:
        return False
    try:
        img = Image.open(img_path).convert("RGBA")
        w, h = img.size
        # Emblem is in top-left quarter
        qw, qh = w // 4, h // 4
        pixels = img.load()

        # Find non-transparent pixels in top-left quarter and collect colors
        opaque_pixels = []
        opaque_set = set()
        for y in range(qh):
            for x in range(qw):
                r, g, b, a = pixels[x, y]
                if a > 128:
                    opaque_pixels.append((x, y, (r, g, b, a)))
                    opaque_set.add((x, y))

        if not opaque_pixels:
            return False

        # Dominant non-black color (exclude near-black)
        from collections import Counter
        color_counts = Counter()
        for _x, _y, (r, g, b, _a) in opaque_pixels:
            if r + g + b > 30:  # not black
                color_counts[(r, g, b)] += 1
        if not color_counts:
            return False
        outline_color = color_counts.most_common(1)[0][0]

        # Outline = transparent pixels adjacent to emblem (hug the shape)
        # 8-neighbors (corners-included): don't cover any emblem pixels
        outline_pixels = set()
        for (x, y) in opaque_set:
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in opaque_set:
                    r, g, b, a = pixels[nx, ny]
                    if a <= 128:  # transparent
                        outline_pixels.add((nx, ny))

        for (x, y) in outline_pixels:
            if 0 <= x < w and 0 <= y < h:
                pixels[x, y] = (*outline_color, 255)

        img.save(img_path)
        return True
    except Exception as e:
        print(f"  Warning: could not add outline to {img_path.name}: {e}")
        return False


def copy_images():
    """Copy game piece images to website collection folder."""
    collection_dir = WEBSITE / "assets" / "images" / "collection"
    collection_dir.mkdir(parents=True, exist_ok=True)

    for sub in ["challenges", "components", "component_upgrades", "operations", "workers", "worker_upgrades"]:
        (collection_dir / sub).mkdir(exist_ok=True)

    game_images = GAME_REPO / "assets" / "images"

    # Challenges
    for v in CHALLENGE_VARIANTS:
        src = game_images / "challenges" / f"{to_snake(v)}.png"
        if src.exists():
            shutil.copy2(src, collection_dir / "challenges" / src.name)

    # Components: variant_color_normal.png
    for rarity, variant in COMPONENT_VARIANTS:
        for color in COMPONENT_COLORS:
            src = game_images / "components" / f"{to_snake(variant)}_{color}_normal.png"
            if src.exists():
                shutil.copy2(src, collection_dir / "components" / src.name)

    # Component upgrades: comp_upgrade_{boost|horiz|vert|adjacent}_{rarity}.png
    for variant, img_prefix in COMP_UPGRADE_VARIANTS:
        for r in RARITIES:
            src = game_images / "component_upgrades" / f"comp_upgrade_{img_prefix}_{r}.png"
            if src.exists():
                shutil.copy2(src, collection_dir / "component_upgrades" / src.name)

    # Operations
    for tup in OPERATION_VARIANTS:
        for v in tup[1:]:
            src = game_images / "operations" / f"{to_snake(v)}.png"
            if src.exists():
                shutil.copy2(src, collection_dir / "operations" / src.name)

    # Workers: use aseprite folder like the game does (res://assets/aseprite/)
    aseprite_src = GAME_REPO / "assets" / "aseprite"
    WORKER_IMG_OVERRIDES = {
        "GraphicDesigner": "graphic_designer_red",
        "InventoryClerk": "inventory_clerk_row",
    }
    for _rarity, variants in WORKER_VARIANTS:
        for v in variants:
            img_name = WORKER_IMG_OVERRIDES.get(v, to_snake(v))
            src = aseprite_src / f"{img_name}.png"
            if src.exists():
                shutil.copy2(src, collection_dir / "workers" / f"{to_snake(v)}.png")

    # Worker upgrades: variant_tl.png
    wu_src = game_images / "worker_upgrades"
    wu_map = {
        "Commendation": "commendation",
        "PriorityUplink": "priority_uplink",
        "PriorityDownlink": "priority_downlink",
        "PriorityLeftlink": "priority_leftlink",
        "PriorityRightlink": "priority_rightlink",
        "AdaptiveCache": "adaptive_cache",
        "FreshInstall": "fresh_install",
        "RotationalLink": "rotational_uplink",  # or rotational_leftlink
        "BackupPower": "backup_power",
        "IterativeCalibration": "iterative_calibration",
        "SatelliteLink": "satellite_uplink",
    }
    for variant, img_base in wu_map.items():
        for suffix in ["_tl.png", "_tr.png", "_bl.png", "_br.png"]:
            src = wu_src / f"{img_base}{suffix}"
            if src.exists():
                dst = collection_dir / "worker_upgrades" / src.name
                shutil.copy2(src, dst)
                add_emblem_outline(dst)
                break

    # Add emblem outline to component upgrades (after copy)
    for variant, img_prefix in COMP_UPGRADE_VARIANTS:
        for r in RARITIES:
            dst = collection_dir / "component_upgrades" / f"comp_upgrade_{img_prefix}_{r}.png"
            if dst.exists():
                add_emblem_outline(dst)


def build_collection_data() -> dict:
    """Build collection metadata from game classes."""
    classes_dir = GAME_REPO / "classes"
    data = {}

    # Challenges
    data["challenges"] = []
    for v in CHALLENGE_VARIANTS:
        cls = classes_dir / "challenges" / f"{v}.gd"
        raw = extract_rules_from_class(cls)
        rules = polish_rules_for_website(
            apply_rules_defaults(raw, "Challenge", variant=v), v, "Challenge")
        data["challenges"].append({
            "title": to_title(v),
            "rules": rules,
            "image": f"assets/images/collection/challenges/{to_snake(v)}.png",
        })

    # Components
    data["components"] = []
    divider_suffix = "divides them into three, moving those rightward, upward, & downward, respectively"
    for rarity, variant in COMPONENT_VARIANTS:
        for color in COMPONENT_COLORS:
            cls = classes_dir / "components" / f"{variant}.gd"
            raw = extract_rules_from_class(cls)
            if variant == "Divider" and raw and " and " in raw:
                raw = raw + " " + divider_suffix  # Divider rules are split across two lines
            rules = polish_rules_for_website(
                apply_rules_defaults(raw, "Component", variant=variant, color=color),
                variant, "Component")
            title = f"{color.capitalize()} {variant}"
            data["components"].append({
                "title": title,
                "rules": rules,
                "image": f"assets/images/collection/components/{to_snake(variant)}_{color}_normal.png",
            })

    # Component upgrades - rules include rarity bonus (+4/+6/+8/+10 for SelfBuff, +1/+2/+3/+4 for others)
    data["component_upgrades"] = []
    variant_names = {"boost": "Self Buff", "horiz": "Row Buff", "vert": "Column Buff", "adjacent": "Adjacent Buff"}
    rarity_bonus = {"common": (4, 1), "uncommon": (6, 2), "rare": (8, 3), "legendary": (10, 4)}  # SelfBuff, others
    for variant, img_prefix in COMP_UPGRADE_VARIANTS:
        cls = classes_dir / "component_upgrades" / f"{variant}.gd"
        raw = extract_rules_from_class(cls)
        base = raw if raw else "This component gets "
        for r in RARITIES:
            sb, ob = rarity_bonus[r]
            rules = base + f"+{sb}" if "This component" in base else base + f"+{ob}"
            rules = polish_rules_for_website(strip_bbcode(rules), variant, "ComponentUpgrade")
            data["component_upgrades"].append({
                "title": f"{r.capitalize()} {variant_names[img_prefix]}",
                "rules": rules,
                "image": f"assets/images/collection/component_upgrades/comp_upgrade_{img_prefix}_{r}.png",
            })

    # Operations
    data["operations"] = []
    for tup in OPERATION_VARIANTS:
        for v in tup[1:]:
            cls = classes_dir / "operations" / f"{v}.gd"
            raw = extract_rules_from_class(cls)
            rules = polish_rules_for_website(
                apply_rules_defaults(raw, "Operation"), v, "Operation")
            data["operations"].append({
                "title": to_title(v),
                "rules": rules,
                "image": f"assets/images/collection/operations/{to_snake(v)}.png",
            })

    # Workers - use explicit order from parameters; title by rarity, rules+reminders with version-colored numbers
    data["workers"] = []
    for rarity, variants in WORKER_VARIANTS:
        for v in variants:
            cls = classes_dir / "workers" / f"{v}.gd"
            rules = build_worker_rules_and_reminders(cls, v)
            img = f"assets/images/collection/workers/{to_snake(v)}.png"
            data["workers"].append({
                "title": to_title(v),
                "rarity": rarity,
                "rules": rules,
                "image": img,
            })

    # Worker upgrades
    WU_IMG = {"RotationalLink": "rotational_uplink", "SatelliteLink": "satellite_uplink"}
    data["worker_upgrades"] = []
    for tup in WORKER_UPGRADE_VARIANTS:
        for v in tup[1:]:
            cls = classes_dir / "worker_upgrades" / f"{v}.gd"
            img_base = WU_IMG.get(v, to_snake(v))
            img_path = WEBSITE / "assets" / "images" / "collection" / "worker_upgrades"
            found = None
            for suffix in ["_tl.png", "_tr.png", "_bl.png", "_br.png"]:
                p = img_path / f"{img_base}{suffix}"
                if p.exists():
                    found = f"assets/images/collection/worker_upgrades/{p.name}"
                    break
            if not found and img_path.exists():
                for f in img_path.glob(f"{img_base}*.png"):
                    found = f"assets/images/collection/worker_upgrades/{f.name}"
                    break
            raw = extract_rules_from_class(cls)
            rules = polish_rules_for_website(
                apply_rules_defaults(raw, "WorkerUpgrade"), v, "WorkerUpgrade")
            data["worker_upgrades"].append({
                "title": to_title(v),
                "rules": rules,
                "image": found or f"assets/images/collection/worker_upgrades/{img_base}_tl.png",
            })

    return data


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_collection_html(data: dict) -> str:
    """Generate HTML for the 6 collection sections."""
    sections = []
    category_titles = {
        "challenges": "Challenges",
        "components": "Components",
        "component_upgrades": "Component Upgrades",
        "workers": "Workers",
        "worker_upgrades": "Worker Upgrades",
        "operations": "Operations",
    }
    # Alternate bg: dark, secondary, dark, secondary...
    bg_classes = ["bg-dark", "bg-secondary", "bg-dark", "bg-secondary", "bg-dark", "bg-secondary"]
    order = ["components", "component_upgrades", "workers", "worker_upgrades", "operations", "challenges"]

    for i, key in enumerate(order):
        if key not in data or not data[key]:
            continue
        title = category_titles.get(key, key.replace("_", " ").title())
        section_id = key.replace("_", "-")
        bg = bg_classes[i % len(bg_classes)]
        is_upgrade = key in ("component_upgrades", "worker_upgrades")
        is_worker = key == "workers"
        items = []
        for piece in data[key]:
            img = piece.get("image", "")
            if is_worker:
                # Worker title: rarity-colored name + green "1.0" (game tooltip style)
                title_plain = piece.get("title", "")
                title_plain_esc = html_escape(title_plain)
                rarity = piece.get("rarity", "common")
                rarity_hex = PALETTE_HEX.get(rarity, PALETTE_HEX["common"])
                version_hex = PALETTE_HEX["version_1_0"]
                title_text = f'<span style="color:#{rarity_hex}">{title_plain_esc}</span> <span style="color:#{version_hex}">1.0</span>'
                title_alt = f"{title_plain} 1.0"
            else:
                title_text = html_escape(piece.get("title", ""))
                title_alt = piece.get("title", "")
            rules = piece.get("rules", "")
            if "<span" not in rules:
                rules = html_escape(rules)
            rules = rules.replace("\u26a1", '<span class="power-icon" aria-hidden="true"></span>')
            item_class = "collection-item collection-item-worker" if is_worker else "collection-item"
            if is_upgrade:
                img_html = f'<div class="collection-piece-img-upgrade"><img src="{img}" alt="{html_escape(title_alt)}" class="collection-piece-img" loading="lazy"></div>'
            else:
                img_html = f'<img src="{img}" alt="{html_escape(title_alt)}" class="collection-piece-img" loading="lazy">'
            items.append(f'''            <div class="{item_class}">
              {img_html}
              <div class="collection-piece-text">
                <div class="collection-piece-title">{title_text}</div>
                <div class="collection-piece-rules">{rules}</div>
              </div>
            </div>''')
        sections.append(f'''    <section id="collection-{section_id}" class="collection-section top-part-padding {bg}">
        <div class="container">
            <h2 class="collection-section-title">{title}</h2>
            <div class="collection-list">
{chr(10).join(items)}
            </div>
        </div>
    </section>''')

    return "\n\n".join(sections)


def update_index_html(data: dict):
    """Replace collection sections in index.html between markers."""
    index_path = WEBSITE / "index.html"
    if not index_path.exists():
        return
    content = index_path.read_text()
    start_marker = "<!-- COLLECTION_SECTIONS_START -->"
    end_marker = "<!-- COLLECTION_SECTIONS_END -->"
    if start_marker not in content or end_marker not in content:
        print("Warning: index.html missing COLLECTION_SECTIONS markers. Add them between Prismatics and Blog.")
        return
    new_html = generate_collection_html(data)
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.DOTALL
    )
    replacement = f"{start_marker}\n{new_html}\n    {end_marker}"
    new_content = pattern.sub(replacement, content)
    if new_content != content:
        index_path.write_text(new_content)
        print("Updated index.html collection sections.")
    else:
        print("index.html collection sections unchanged.")


def main():
    print("Refreshing collection from game repo...")
    copy_images()
    data = build_collection_data()
    out = WEBSITE / "assets" / "data" / "collection.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {out}")
    update_index_html(data)
    print("Done.")


if __name__ == "__main__":
    wu_map = {
        "Commendation": "commendation",
        "PriorityUplink": "priority_uplink",
        "PriorityDownlink": "priority_downlink",
        "PriorityLeftlink": "priority_leftlink",
        "PriorityRightlink": "priority_rightlink",
        "AdaptiveCache": "adaptive_cache",
        "FreshInstall": "fresh_install",
        "RotationalLink": "rotational_uplink",
        "BackupPower": "backup_power",
        "IterativeCalibration": "iterative_calibration",
        "SatelliteLink": "satellite_uplink",
    }
    main()
