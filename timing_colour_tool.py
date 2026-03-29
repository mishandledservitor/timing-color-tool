#!/usr/bin/env python3
"""
Timing Colour Tool — Interactive Terminal UI
=============================================
A rich terminal interface that avoids tkinter entirely.
Works in any macOS Terminal with zero dependencies beyond the standard library.

Generates an HTML visual preview during dry-run so you can see every colour
change in your browser before committing.
"""

import os
import sys
import glob
import html
import subprocess
import webbrowser
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from update_project_colours import run_update, hex_to_css, text_colour_for_bg


# ── Styling helpers ──────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
CLEAR_LINE = "\033[K"


def banner():
    print()
    print(f"{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║{RESET}  {BOLD}🎨  Timing Colour Tool{RESET}                                  {CYAN}║{RESET}")
    print(f"{CYAN}║{RESET}  {DIM}Apply colour variations to child projects{RESET}                {CYAN}║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()


# ── Auto-detect database ────────────────────────────────────────────────────

def find_databases():
    """Find Timing SQLite databases on the system."""
    candidates = []

    default = os.path.expanduser(
        "~/Library/Application Support/info.eurocomp.Timing2/SQLite.db"
    )
    if os.path.exists(default):
        candidates.append(default)

    for pattern in [
        "~/Library/Application Support/info.eurocomp.Timing*/SQLite.db",
        "~/Library/Application Support/com.eurocomp.Timing*/SQLite.db",
    ]:
        for path in glob.glob(os.path.expanduser(pattern)):
            if path not in candidates:
                candidates.append(path)

    return candidates


# ── Input helpers ────────────────────────────────────────────────────────────

def ask_int(prompt, default, min_val=0, max_val=100):
    """Ask for an integer with a default value."""
    while True:
        raw = input(f"  {prompt} [{BOLD}{default}{RESET}]: ").strip()
        if raw == "":
            return default
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            print(f"  {RED}Please enter a number between {min_val} and {max_val}.{RESET}")
        except ValueError:
            print(f"  {RED}Please enter a valid number.{RESET}")


def ask_yes_no(prompt, default_yes=True):
    """Ask a yes/no question."""
    hint = "Y/n" if default_yes else "y/N"
    raw = input(f"  {prompt} [{hint}]: ").strip().lower()
    if raw == "":
        return default_yes
    return raw in ("y", "yes")


# ── HTML Preview Generator ──────────────────────────────────────────────────

def _render_tree_rows(projects, node_id, depth, is_root=False):
    """Recursively build HTML table rows for one branch of the tree."""
    proj = projects[node_id]
    title = html.escape(proj.get('title') or '(untitled)')
    original = proj.get('original_color') or '#888888'
    current = proj.get('color') or '#888888'
    changed = original != current

    orig_css = hex_to_css(original)
    new_css = hex_to_css(current)
    orig_text = text_colour_for_bg(original)
    new_text = text_colour_for_bg(current)

    indent_px = depth * 28
    folder_icon = "📁" if proj['children'] else "📄"

    if is_root:
        row_class = "root-row"
        badge = '<span class="badge root-badge">Root</span>'
        arrow_cell = f'''
            <td class="swatch-cell">
                <div class="swatch" style="background:{orig_css}; color:{orig_text};">{html.escape(orig_css.upper())}</div>
            </td>
            <td class="arrow-cell">—</td>
            <td class="swatch-cell">
                <div class="swatch unchanged" style="background:{orig_css}; color:{orig_text};">unchanged</div>
            </td>'''
    elif changed:
        row_class = "changed-row"
        badge = '<span class="badge changed-badge">Changed</span>'
        arrow_cell = f'''
            <td class="swatch-cell">
                <div class="swatch" style="background:{orig_css}; color:{orig_text};">{html.escape(orig_css.upper())}</div>
            </td>
            <td class="arrow-cell">→</td>
            <td class="swatch-cell">
                <div class="swatch new" style="background:{new_css}; color:{new_text};">{html.escape(new_css.upper())}</div>
            </td>'''
    else:
        row_class = "unchanged-row"
        badge = '<span class="badge unchanged-badge">Unchanged</span>'
        arrow_cell = f'''
            <td class="swatch-cell">
                <div class="swatch" style="background:{orig_css}; color:{orig_text};">{html.escape(orig_css.upper())}</div>
            </td>
            <td class="arrow-cell">—</td>
            <td class="swatch-cell">
                <div class="swatch unchanged" style="background:{orig_css}; color:{orig_text};">unchanged</div>
            </td>'''

    rows = f'''<tr class="{row_class}">
        <td class="name-cell" style="padding-left:{indent_px + 12}px;">
            <span class="icon">{folder_icon}</span>
            <span class="title">{title}</span>
            {badge}
        </td>
        {arrow_cell}
    </tr>\n'''

    for child_id in proj['children']:
        rows += _render_tree_rows(projects, child_id, depth + 1)

    return rows


def generate_html_preview(tree_data, output_path):
    """
    Generate a self-contained HTML file showing the full project tree
    with before/after colour swatches.
    """
    projects = tree_data['projects']
    roots = tree_data['roots']
    updates = tree_data['updates']
    variation = tree_data['variation']
    seed = tree_data.get('seed')

    total_projects = len(projects)
    changed_count = len(updates)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    seed_display = str(seed) if seed is not None else 'random'

    # Build the table rows
    table_rows = ""
    for root_id in roots:
        root = projects[root_id]
        if not root.get('color') or not root['color'].startswith('#'):
            continue
        table_rows += _render_tree_rows(projects, root_id, 0, is_root=True)

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Timing Colour Preview</title>
<style>
    :root {{
        --bg: #0e0e10;
        --surface: #1a1a1f;
        --surface2: #222228;
        --border: #2a2a32;
        --text: #e4e4e8;
        --text-dim: #8888a0;
        --accent: #6c8cff;
        --green: #4ade80;
        --amber: #fbbf24;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
    }}

    .container {{
        max-width: 960px;
        margin: 0 auto;
        padding: 40px 24px 80px;
    }}

    header {{
        margin-bottom: 36px;
    }}

    h1 {{
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 6px;
    }}
    h1 .icon {{ font-size: 26px; margin-right: 8px; }}

    .subtitle {{
        color: var(--text-dim);
        font-size: 14px;
    }}

    .stats {{
        display: flex;
        gap: 12px;
        margin: 24px 0 32px;
        flex-wrap: wrap;
    }}
    .stat {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 14px 20px;
        min-width: 140px;
    }}
    .stat .label {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--text-dim);
        margin-bottom: 4px;
    }}
    .stat .value {{
        font-size: 22px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }}
    .stat .value.accent {{ color: var(--accent); }}
    .stat .value.green  {{ color: var(--green); }}
    .stat .value.amber  {{ color: var(--amber); }}

    .filter-bar {{
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
        flex-wrap: wrap;
        align-items: center;
    }}
    .filter-btn {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 7px 14px;
        font-size: 13px;
        color: var(--text-dim);
        cursor: pointer;
        transition: all 0.15s;
        font-family: inherit;
    }}
    .filter-btn:hover {{ border-color: var(--accent); color: var(--text); }}
    .filter-btn.active {{
        background: var(--accent);
        border-color: var(--accent);
        color: #fff;
    }}
    .search-box {{
        margin-left: auto;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 7px 12px;
        font-size: 13px;
        color: var(--text);
        font-family: inherit;
        width: 200px;
        outline: none;
        transition: border-color 0.15s;
    }}
    .search-box:focus {{ border-color: var(--accent); }}
    .search-box::placeholder {{ color: var(--text-dim); }}

    .tree-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
    }}

    .tree-table thead th {{
        text-align: left;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--text-dim);
        padding: 12px 16px;
        background: var(--surface2);
        border-bottom: 1px solid var(--border);
    }}
    .tree-table thead th:first-child {{ padding-left: 16px; }}

    .tree-table tr {{
        transition: background 0.1s;
    }}
    .tree-table tr:hover {{
        background: var(--surface2);
    }}
    .tree-table tr.hidden {{
        display: none;
    }}

    .tree-table td {{
        padding: 8px 10px;
        border-bottom: 1px solid var(--border);
        vertical-align: middle;
    }}
    .tree-table tr:last-child td {{
        border-bottom: none;
    }}

    .name-cell {{
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 400px;
    }}
    .name-cell .icon {{
        margin-right: 6px;
        font-size: 14px;
    }}
    .name-cell .title {{
        font-size: 14px;
        font-weight: 500;
    }}

    .badge {{
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 2px 7px;
        border-radius: 4px;
        margin-left: 8px;
        vertical-align: middle;
    }}
    .root-badge     {{ background: #6c8cff22; color: var(--accent); }}
    .changed-badge  {{ background: #4ade8022; color: var(--green); }}
    .unchanged-badge {{ background: #88888822; color: var(--text-dim); }}

    .swatch-cell {{
        width: 120px;
    }}
    .swatch {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        font-family: "SF Mono", "Menlo", monospace;
        min-width: 90px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.08);
    }}
    .swatch.unchanged {{
        opacity: 0.5;
        font-weight: 400;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        font-style: italic;
    }}

    .arrow-cell {{
        width: 32px;
        text-align: center;
        color: var(--text-dim);
        font-size: 16px;
    }}

    .root-row td {{
        background: var(--surface2);
    }}
    .root-row .title {{
        font-weight: 700;
        font-size: 15px;
    }}

    .footer {{
        margin-top: 32px;
        text-align: center;
        color: var(--text-dim);
        font-size: 12px;
    }}

    /* Expand/collapse animation */
    .collapse-toggle {{
        cursor: pointer;
        user-select: none;
    }}
    .collapse-toggle:hover .title {{
        text-decoration: underline;
    }}

    @media (max-width: 700px) {{
        .stats {{ flex-direction: column; }}
        .search-box {{ width: 100%; margin-left: 0; margin-top: 8px; }}
        .name-cell {{ max-width: 200px; }}
    }}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1><span class="icon">🎨</span>Timing Colour Preview</h1>
        <p class="subtitle">Dry-run preview — no changes have been saved yet</p>
    </header>

    <div class="stats">
        <div class="stat">
            <div class="label">Total projects</div>
            <div class="value">{total_projects}</div>
        </div>
        <div class="stat">
            <div class="label">Would change</div>
            <div class="value green">{changed_count}</div>
        </div>
        <div class="stat">
            <div class="label">Variation</div>
            <div class="value accent">{variation}</div>
        </div>
        <div class="stat">
            <div class="label">Seed</div>
            <div class="value">{seed_display}</div>
        </div>
    </div>

    <div class="filter-bar">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="changed">Changed only</button>
        <button class="filter-btn" data-filter="roots">Roots only</button>
        <input type="text" class="search-box" placeholder="Search projects…" id="searchBox">
    </div>

    <table class="tree-table">
        <thead>
            <tr>
                <th>Project</th>
                <th>Before</th>
                <th></th>
                <th>After</th>
            </tr>
        </thead>
        <tbody id="treeBody">
            {table_rows}
        </tbody>
    </table>

    <div class="footer">
        Generated {timestamp} by Timing Colour Tool
    </div>
</div>

<script>
(function() {{
    // Filtering
    const buttons = document.querySelectorAll('.filter-btn');
    const rows = document.querySelectorAll('#treeBody tr');
    const searchBox = document.getElementById('searchBox');

    let activeFilter = 'all';

    function applyFilters() {{
        const query = searchBox.value.toLowerCase().trim();

        rows.forEach(row => {{
            let showByFilter = true;
            if (activeFilter === 'changed') {{
                showByFilter = row.classList.contains('changed-row');
            }} else if (activeFilter === 'roots') {{
                showByFilter = row.classList.contains('root-row');
            }}

            let showBySearch = true;
            if (query) {{
                const title = row.querySelector('.title');
                showBySearch = title && title.textContent.toLowerCase().includes(query);
            }}

            row.classList.toggle('hidden', !(showByFilter && showBySearch));
        }});
    }}

    buttons.forEach(btn => {{
        btn.addEventListener('click', () => {{
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFilter = btn.dataset.filter;
            applyFilters();
        }});
    }});

    searchBox.addEventListener('input', applyFilters);
}})();
</script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(page)


def open_html_preview(file_path):
    """Open the HTML file in the default browser on macOS."""
    abs_path = os.path.abspath(file_path)
    url = 'file://' + abs_path

    try:
        subprocess.run(['open', url], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False


# ── Main interactive flow ───────────────────────────────────────────────────

def interactive():
    banner()

    # ── Step 1: Find database ────────────────────────────────────────────
    print(f"  {BOLD}Step 1:{RESET} Locate the Timing database\n")

    databases = find_databases()

    if databases:
        if len(databases) == 1:
            db_path = databases[0]
            print(f"  {GREEN}✓{RESET} Found database:")
            print(f"    {DIM}{db_path}{RESET}\n")
            if not ask_yes_no("Use this database?", default_yes=True):
                db_path = input(f"\n  Enter path to SQLite.db: ").strip()
        else:
            print(f"  {GREEN}✓{RESET} Found {len(databases)} databases:\n")
            for i, p in enumerate(databases, 1):
                print(f"    {BOLD}{i}{RESET}. {DIM}{p}{RESET}")
            print(f"    {BOLD}{len(databases)+1}{RESET}. Enter a custom path\n")

            while True:
                raw = input(f"  Choose [1]: ").strip()
                if raw == "":
                    db_path = databases[0]
                    break
                try:
                    choice = int(raw)
                    if 1 <= choice <= len(databases):
                        db_path = databases[choice - 1]
                        break
                    elif choice == len(databases) + 1:
                        db_path = input(f"\n  Enter path to SQLite.db: ").strip()
                        break
                except ValueError:
                    pass
                print(f"  {RED}Invalid choice.{RESET}")
    else:
        print(f"  {YELLOW}⚠{RESET}  No Timing database found in the default location.\n")
        db_path = input(f"  Enter full path to SQLite.db: ").strip()

    # Expand ~ and clean
    db_path = os.path.expanduser(db_path.strip('"').strip("'"))

    if not os.path.exists(db_path):
        print(f"\n  {RED}✗ File not found:{RESET} {db_path}")
        print(f"  {DIM}Check the path and try again.{RESET}\n")
        sys.exit(1)

    print(f"\n  {GREEN}✓{RESET} Database: {DIM}{db_path}{RESET}")

    # ── Step 2: Options ──────────────────────────────────────────────────
    print(f"\n  {BOLD}Step 2:{RESET} Configure options\n")

    print(f"  {DIM}Variation strength — how different child colours are from parents{RESET}")
    print(f"  {DIM}  10 = subtle  |  35 = recommended  |  60+ = extreme{RESET}\n")
    variation = ask_int("Variation strength (5-80)", default=35, min_val=5, max_val=80)

    print()
    seed_str = input(f"  Seed for reproducible results (blank = random) [{BOLD}random{RESET}]: ").strip()
    seed = int(seed_str) if seed_str.isdigit() else None

    # ── Step 3: Dry run + HTML preview ───────────────────────────────────
    print(f"\n  {BOLD}Step 3:{RESET} Preview changes\n")

    print(f"{'─' * 60}")
    print(f"  {CYAN}DRY RUN — no changes will be saved{RESET}")
    print(f"{'─' * 60}\n")

    success, message, count, tree_data = run_update(
        db_path=db_path,
        dry_run=True,
        variation=variation,
        seed=seed,
        log_callback=lambda msg: print(f"  {msg}")
    )

    print(f"\n{'─' * 60}")

    if not success:
        print(f"\n  {RED}✗ {message}{RESET}\n")
        sys.exit(1)

    if count == 0:
        print(f"\n  {YELLOW}No child projects found to update.{RESET}\n")
        sys.exit(0)

    print(f"\n  {GREEN}Preview complete:{RESET} {count} projects would be updated.\n")

    # Generate HTML preview
    if tree_data:
        preview_path = os.path.join(SCRIPT_DIR, 'colour_preview.html')
        generate_html_preview(tree_data, preview_path)

        print(f"  {CYAN}📄 Visual preview generated:{RESET}")
        print(f"    {DIM}{preview_path}{RESET}\n")

        if open_html_preview(preview_path):
            print(f"  {GREEN}✓{RESET} Opened in your browser. Take a look, then come back here.\n")
        else:
            print(f"  {YELLOW}⚠{RESET}  Couldn't open browser automatically.")
            print(f"    Open the file above in any browser to see the preview.\n")

    if not ask_yes_no("Happy with the colours? Apply for real?", default_yes=True):
        print(f"\n  {DIM}Cancelled. No changes were made.{RESET}\n")
        sys.exit(0)

    # ── Step 4: Apply ────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  {MAGENTA}APPLYING CHANGES{RESET}")
    print(f"{'─' * 60}\n")

    # Re-seed to get the same colours as the preview
    success, message, count, _ = run_update(
        db_path=db_path,
        dry_run=False,
        variation=variation,
        seed=seed,
        log_callback=lambda msg: print(f"  {msg}")
    )

    print(f"\n{'─' * 60}")

    if success:
        print(f"\n  {GREEN}✓ {message}{RESET}")
        print(f"  {DIM}Restart the Timing app to see the new colours.{RESET}")
        print(f"  {DIM}A backup was created — restore it if you're unhappy with the result.{RESET}\n")
    else:
        print(f"\n  {RED}✗ {message}{RESET}\n")
        sys.exit(1)


# ── CLI passthrough ──────────────────────────────────────────────────────────

def main():
    """If called with arguments, behave like the original CLI. Otherwise interactive."""
    if len(sys.argv) > 1:
        from update_project_colours import main as cli_main
        cli_main()
    else:
        try:
            interactive()
        except KeyboardInterrupt:
            print(f"\n\n  {DIM}Cancelled.{RESET}\n")
            sys.exit(0)


if __name__ == '__main__':
    main()
