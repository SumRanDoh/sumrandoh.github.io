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
    # Replace format placeholders with readable defaults for static display
    text = re.sub(r"%d", "1", text)
    text = re.sub(r"%s", "—", text)
    return text.strip()


def extract_rules_from_class(class_path: Path) -> str:
    """Extract rules = '...' from a GDScript class file."""
    if not class_path.exists():
        return ""
    content = class_path.read_text()
    m = re.search(r'''^\s*rules\s*=\s*['"](.+?)['"]''', content, re.MULTILINE | re.DOTALL)
    if m:
        return strip_bbcode(m.group(1).replace("\\n", " ").replace("  ", " "))
    return ""


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

    # Workers: scan parameters for Worker variants
    worker_variants = []
    params = GAME_REPO / "autoload" / "parameters.gd"
    if params.exists():
        content = params.read_text()
        in_worker = False
        for line in content.split("\n"):
            if "'Worker':" in line:
                in_worker = True
                continue
            if in_worker and "'WorkerUpgrade':" in line:
                break
            if in_worker and re.match(r"\s+'[a-z]+':\s*\{", line):
                for r in RARITIES:
                    if f"'{r}':" in line or f"'{r}':" in content[content.find(line):content.find(line)+500]:
                        pass
                # Extract variant names like 'Accountant', 'Janitor'
                for m in re.finditer(r"'([A-Za-z0-9_]+)'\s*:", line):
                    worker_variants.append(m.group(1))
    # Simpler: just copy all worker pngs
    workers_src = game_images / "workers"
    if workers_src.exists():
        for f in workers_src.glob("*.png"):
            if not f.name.startswith("_"):
                shutil.copy2(f, collection_dir / "workers" / f.name)

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
                shutil.copy2(src, collection_dir / "worker_upgrades" / src.name)
                break


def build_collection_data() -> dict:
    """Build collection metadata from game classes."""
    classes_dir = GAME_REPO / "classes"
    data = {}

    # Challenges
    data["challenges"] = []
    for v in CHALLENGE_VARIANTS:
        cls = classes_dir / "challenges" / f"{v}.gd"
        rules = extract_rules_from_class(cls)
        data["challenges"].append({
            "title": to_title(v),
            "rules": rules,
            "image": f"assets/images/collection/challenges/{to_snake(v)}.png",
        })

    # Components
    data["components"] = []
    for rarity, variant in COMPONENT_VARIANTS:
        for color in COMPONENT_COLORS:
            cls = classes_dir / "components" / f"{variant}.gd"
            rules = extract_rules_from_class(cls)
            title = f"{color.capitalize()} {variant}"
            data["components"].append({
                "title": title,
                "rules": rules,
                "image": f"assets/images/collection/components/{to_snake(variant)}_{color}_normal.png",
            })

    # Component upgrades
    data["component_upgrades"] = []
    variant_names = {"boost": "Self Buff", "horiz": "Row Buff", "vert": "Column Buff", "adjacent": "Adjacent Buff"}
    for variant, img_prefix in COMP_UPGRADE_VARIANTS:
        cls = classes_dir / "component_upgrades" / f"{variant}.gd"
        rules = extract_rules_from_class(cls)
        for r in RARITIES:
            data["component_upgrades"].append({
                "title": f"{r.capitalize()} {variant_names[img_prefix]}",
                "rules": rules,
                "image": f"assets/images/collection/component_upgrades/comp_upgrade_{img_prefix}_{r}.png",
            })

    # Operations
    data["operations"] = []
    for tup in OPERATION_VARIANTS:
        rarity = tup[0]
        for v in tup[1:]:
            cls = classes_dir / "operations" / f"{v}.gd"
            rules = extract_rules_from_class(cls)
            data["operations"].append({
                "title": to_title(v),
                "rules": rules,
                "image": f"assets/images/collection/operations/{to_snake(v)}.png",
            })

    # Workers - use explicit order from parameters
    data["workers"] = []
    for _rarity, variants in WORKER_VARIANTS:
        for v in variants:
            cls = classes_dir / "workers" / f"{v}.gd"
            rules = extract_rules_from_class(cls)
            img = f"assets/images/collection/workers/{to_snake(v)}.png"
            data["workers"].append({
                "title": to_title(v),
                "rules": rules,
                "image": img,
            })

    # Worker upgrades
    WU_IMG = {"RotationalLink": "rotational_uplink", "SatelliteLink": "satellite_uplink"}
    data["worker_upgrades"] = []
    for tup in WORKER_UPGRADE_VARIANTS:
        for v in tup[1:]:
            cls = classes_dir / "worker_upgrades" / f"{v}.gd"
            rules = extract_rules_from_class(cls)
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
    order = ["components", "component_upgrades", "workers", "worker_upgrades", "operations", "challenges"]

    for key in order:
        if key not in data or not data[key]:
            continue
        title = category_titles.get(key, key.replace("_", " ").title())
        section_id = key.replace("_", "-")
        items = []
        for piece in data[key]:
            img = piece.get("image", "")
            title_text = html_escape(piece.get("title", ""))
            rules = html_escape(piece.get("rules", ""))
            items.append(f'''            <div class="collection-item">
              <img src="{img}" alt="{title_text}" class="collection-piece-img" loading="lazy">
              <div class="collection-piece-text">
                <div class="collection-piece-title">{title_text}</div>
                <div class="collection-piece-rules">{rules}</div>
              </div>
            </div>''')
        sections.append(f'''    <section id="collection-{section_id}" class="collection-section top-part-padding bg-dark">
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
