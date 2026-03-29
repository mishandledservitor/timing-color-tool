#!/usr/bin/env python3
"""
Timing App - Project Colour Inheritance Script
===============================================
Applies random hue variations of parent project colours to all child projects,
up to 5 levels deep. Parent colours remain unchanged.

Usage:
    python3 update_project_colours.py /path/to/SQLite.db
    python3 update_project_colours.py /path/to/SQLite.db --dry-run
    python3 update_project_colours.py /path/to/SQLite.db --variation 35
    python3 update_project_colours.py /path/to/SQLite.db --variation 35 --seed 42
"""

import sqlite3
import colorsys
import random
import argparse
import shutil
import os
from datetime import datetime


def hex_to_rgb(hex_color):
    """Convert #RRGGBBFF hex to (r, g, b) floats 0-1."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return r, g, b


def rgb_to_hex(r, g, b, alpha='FF'):
    """Convert (r, g, b) floats 0-1 back to #RRGGBBFF hex."""
    return '#{:02X}{:02X}{:02X}{}'.format(
        round(r * 255),
        round(g * 255),
        round(b * 255),
        alpha
    )


def hex_to_css(hex_color):
    """Convert #RRGGBBFF to a CSS-safe #RRGGBB (strip alpha)."""
    if hex_color and len(hex_color) >= 7:
        return hex_color[:7]
    return hex_color or '#888888'


def text_colour_for_bg(hex_color):
    """Return '#000' or '#fff' for readable text on the given background."""
    try:
        r, g, b = hex_to_rgb(hex_color)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return '#000' if luminance > 0.45 else '#fff'
    except Exception:
        return '#000'


def vary_colour(hex_color, variation_strength=15):
    """
    Generate a random variation of the given colour within the same hue family.

    variation_strength: 0-100, how much to vary (default 15 = subtle)
    """
    hex_color = hex_color.strip()
    alpha = hex_color[7:9] if len(hex_color) >= 9 else 'FF'

    r, g, b = hex_to_rgb(hex_color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    strength = variation_strength / 100.0

    hue_shift = random.uniform(-0.08, 0.08) * strength
    h = (h + hue_shift) % 1.0

    sat_shift = random.uniform(-strength * 0.7, strength * 0.7)
    s = max(0.1, min(1.0, s + sat_shift))

    val_shift = random.uniform(-strength * 0.1, strength * 0.1)
    v = max(0.15, min(1.0, v + val_shift))

    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return rgb_to_hex(r2, g2, b2, alpha)


def get_projects(conn):
    """Fetch all projects with their id, title, color, and parent."""
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    project_table = None
    for candidate in ['TMProject', 'Project', 'project', 'projects']:
        if candidate in tables:
            project_table = candidate
            break

    if not project_table:
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            if 'color' in cols or 'colour' in cols:
                project_table = table
                break

    if not project_table:
        raise RuntimeError(f"Could not find a projects table. Tables available: {tables}")

    cursor.execute(f"PRAGMA table_info({project_table})")
    columns = {row[1]: row[0] for row in cursor.fetchall()}

    color_col = next((c for c in columns if 'color' in c.lower() or 'colour' in c.lower()), None)
    parent_col = next((c for c in columns if 'parent' in c.lower()), None)
    title_col = next((c for c in columns if c.lower() in ('title', 'name', 'projectname')), None)
    id_col = next((c for c in columns if c.lower() in ('z_pk', 'id', 'pk', 'projectid')), None)

    if not all([color_col, id_col]):
        raise RuntimeError(f"Could not identify required columns. Found: {list(columns.keys())}")

    cursor.execute(f"SELECT {id_col}, {title_col or 'NULL'}, {color_col}, {parent_col or 'NULL'} FROM {project_table}")
    rows = cursor.fetchall()

    projects = {}
    for row in rows:
        pid, title, color, parent = row
        projects[pid] = {
            'id': pid,
            'title': title,
            'color': color,
            'original_color': color,
            'parent': parent,
            'children': []
        }

    roots = []
    for pid, proj in projects.items():
        parent_id = proj['parent']
        if parent_id and parent_id in projects:
            projects[parent_id]['children'].append(pid)
        elif not parent_id:
            roots.append(pid)

    return projects, roots, project_table, id_col, color_col


def assign_child_colours(projects, node_id, parent_colour, depth, variation_strength, updates, dry_run, log_callback=None):
    """Recursively assign colour variations to children."""
    if depth > 20:
        return

    proj = projects[node_id]

    for child_id in proj['children']:
        child = projects[child_id]
        new_colour = vary_colour(parent_colour, variation_strength)

        action = "WOULD UPDATE" if dry_run else "UPDATE"
        msg = f"{'  ' * depth}{action}: '{child['title']}' | {child['color']} -> {new_colour}"
        if log_callback:
            log_callback(msg)
        else:
            print(f"  {msg}")

        updates[child_id] = new_colour
        child['color'] = new_colour

        assign_child_colours(projects, child_id, new_colour, depth + 1, variation_strength, updates, dry_run, log_callback)


def run_update(db_path, dry_run=False, variation=15, seed=None, log_callback=None):
    """
    Main logic — used by both CLI and GUI.
    Returns (success, message, update_count, tree_data).

    tree_data contains 'projects' and 'roots' so the caller can build an HTML preview.
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    if seed is not None:
        random.seed(seed)

    if not os.path.exists(db_path):
        return False, f"File not found: {db_path}", 0, None

    if not dry_run:
        backup_path = db_path + '.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(db_path, backup_path)
        log(f"Backup created: {backup_path}\n")

    conn = sqlite3.connect(db_path)

    try:
        projects, roots, project_table, id_col, color_col = get_projects(conn)
        log(f"Found {len(projects)} projects, {len(roots)} top-level folders\n")

        updates = {}

        for root_id in roots:
            root = projects[root_id]
            parent_colour = root['color']

            if not parent_colour or not parent_colour.startswith('#'):
                log(f"Skipping '{root['title']}' -- no valid colour set")
                continue

            log(f"[Root] '{root['title']}' | colour: {parent_colour} (unchanged)")
            assign_child_colours(projects, root_id, parent_colour, 1, variation, updates, dry_run, log)
            log("")

        mode = 'Would update' if dry_run else 'Updating'
        log(f"{mode} {len(updates)} child projects...")

        tree_data = {
            'projects': projects,
            'roots': roots,
            'updates': updates,
            'variation': variation,
            'seed': seed,
        }

        if not dry_run and updates:
            cursor = conn.cursor()
            for pid, new_colour in updates.items():
                cursor.execute(
                    f"UPDATE {project_table} SET {color_col} = ? WHERE {id_col} = ?",
                    (new_colour, pid)
                )
            conn.commit()
            msg = f"Done! {len(updates)} projects updated."
            log(msg)
            log("\nTip: Restart the Timing app to see the changes.")
            return True, msg, len(updates), tree_data
        elif dry_run:
            msg = f"Dry run complete. {len(updates)} projects would be updated."
            log(f"\n(Dry run -- no changes saved.)")
            return True, msg, len(updates), tree_data
        else:
            return True, "No child projects found to update.", 0, tree_data

    except Exception as e:
        return False, f"Error: {str(e)}", 0, None
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Apply hue variations to child projects in Timing app.')
    parser.add_argument('db_path', help='Path to SQLite.db')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')
    parser.add_argument('--variation', type=int, default=15, help='Variation strength 0-100 (default: 15)')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    args = parser.parse_args()

    success, message, count, _ = run_update(
        db_path=args.db_path,
        dry_run=args.dry_run,
        variation=args.variation,
        seed=args.seed
    )

    if not success:
        print(f"\nError: {message}")


if __name__ == '__main__':
    main()
