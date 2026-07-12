#!/usr/bin/env python3
"""
myvcs.py - Engine for a minimal local version control system.
Built by Sarthi.

Handles object storage, commit history, revert, diff and status.
The Bash script (myvcs.sh) is just a thin CLI wrapper around this file.
"""

import os
import sys
import json
import hashlib
import shutil
import time
import difflib

VCS_DIR = ".myvcs"
OBJECTS_DIR = os.path.join(VCS_DIR, "objects")
COMMITS_FILE = os.path.join(VCS_DIR, "commits.json")

IGNORE = {VCS_DIR, ".git", "__pycache__"}

# The config file always lives next to this script, NOT inside the
# monitored project. This is what lets myvcs.py / myvcs.sh sit in one
# folder while tracking a completely different folder.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, ".myvcs_config.json")


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)

    # Migrate the old single-project config format transparently.
    if "target_dir" in cfg and "projects" not in cfg:
        cfg = {"current": "default", "projects": {"default": cfg["target_dir"]}}
        save_config(cfg)
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def prompt_for_target_dir():
    while True:
        raw = input("Enter the full path of the directory you want myvcs to monitor: ").strip()
        path = os.path.abspath(os.path.expanduser(raw))
        if os.path.isdir(path):
            return path
        create = input(f"'{path}' doesn't exist. Create it? [y/N]: ").strip().lower()
        if create == "y":
            os.makedirs(path)
            return path
        print("Please enter a valid, existing directory (or let me create it).")


def get_target_dir(project_name=None):
    """
    Resolve which folder to operate on.
    - If project_name is given (via -p/--project), use that registered project.
    - Otherwise use the 'current' project.
    - If nothing is configured at all, prompt for a first project (interactive setup).
    """
    cfg = load_config()
    projects = cfg.get("projects", {})

    if project_name:
        if project_name not in projects:
            print(f"No such project: '{project_name}'. Configured projects: "
                  f"{', '.join(projects) if projects else '(none)'}")
            print(f"Add it with: myvcs setup {project_name} <path>")
            sys.exit(1)
        target_dir = projects[project_name]

    elif projects:
        current = cfg.get("current")
        if not current or current not in projects:
            print("No current project selected. Use 'myvcs use <name>' or pass -p <name>.")
            print(f"Configured projects: {', '.join(projects)}")
            sys.exit(1)
        target_dir = projects[current]

    else:
        # Nothing configured yet at all - first-time setup.
        print("myvcs isn't set up yet - let's add your first project to monitor.")
        name = input("Give this project a short name (e.g. 'myapp'): ").strip() or "default"
        target_dir = prompt_for_target_dir()
        cfg["projects"] = {name: target_dir}
        cfg["current"] = name
        save_config(cfg)
        print(f"Added project '{name}' -> {target_dir} (set as current)")

    if not os.path.isdir(target_dir):
        print(f"Configured directory '{target_dir}' no longer exists on disk.")
        sys.exit(1)

    return target_dir


def cmd_setup(name=None, path=None):
    """Register a new project (or update an existing one) and make it current."""
    if not name:
        name = input("Give this project a short name (e.g. 'myapp'): ").strip()
    if not name:
        print("A project name is required.")
        sys.exit(1)

    if path:
        target_dir = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(target_dir):
            create = input(f"'{target_dir}' doesn't exist. Create it? [y/N]: ").strip().lower()
            if create == "y":
                os.makedirs(target_dir)
            else:
                print("Aborted: target directory does not exist.")
                sys.exit(1)
    else:
        target_dir = prompt_for_target_dir()

    cfg = load_config()
    projects = cfg.setdefault("projects", {})
    projects[name] = target_dir
    cfg["current"] = name
    save_config(cfg)
    print(f"Project '{name}' -> {target_dir} (set as current)")

    os.chdir(target_dir)
    if not os.path.isdir(VCS_DIR):
        cmd_init()


def cmd_use(name):
    cfg = load_config()
    projects = cfg.get("projects", {})
    if name not in projects:
        print(f"No such project: '{name}'. Configured projects: "
              f"{', '.join(projects) if projects else '(none)'}")
        sys.exit(1)
    cfg["current"] = name
    save_config(cfg)
    print(f"Switched current project to '{name}' ({projects[name]})")


def cmd_list():
    cfg = load_config()
    projects = cfg.get("projects", {})
    current = cfg.get("current")
    if not projects:
        print("No projects configured yet. Run 'myvcs setup <name> <path>'.")
        return
    for name, path in projects.items():
        marker = "*" if name == current else " "
        missing = "" if os.path.isdir(path) else "  (missing!)"
        print(f"{marker} {name:<15} {path}{missing}")


def cmd_where():
    cfg = load_config()
    projects = cfg.get("projects", {})
    current = cfg.get("current")
    if not projects or not current:
        print("myvcs is not configured yet. Run 'myvcs setup <name> <path>'.")
        return
    path = projects.get(current, "?")
    status = "" if os.path.isdir(path) else "  (missing!)"
    print(f"Current project: {current} -> {path}{status}")


def cmd_remove(name):
    cfg = load_config()
    projects = cfg.get("projects", {})
    if name not in projects:
        print(f"No such project: '{name}'")
        sys.exit(1)
    del projects[name]
    if cfg.get("current") == name:
        cfg["current"] = next(iter(projects), None)
    save_config(cfg)
    print(f"Removed project '{name}' from myvcs (files on disk were left untouched).")


def parse_project_flag(args):
    """Pull an optional -p/--project <name> out of an args list."""
    remaining = []
    project = None
    i = 0
    while i < len(args):
        if args[i] in ("-p", "--project"):
            if i + 1 >= len(args):
                print("Error: -p/--project requires a project name")
                sys.exit(1)
            project = args[i + 1]
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return project, remaining


def ensure_repo():
    if not os.path.isdir(VCS_DIR):
        print("Not a myvcs repository. Run 'myvcs init' first.")
        sys.exit(1)


def load_commits():
    if not os.path.exists(COMMITS_FILE):
        return []
    with open(COMMITS_FILE, "r") as f:
        return json.load(f)


def save_commits(commits):
    with open(COMMITS_FILE, "w") as f:
        json.dump(commits, f, indent=2)


def sha1_of_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_files(root="."):
    file_list = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE]
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            if rel.split(os.sep)[0] in IGNORE:
                continue
            file_list.append(rel)
    return file_list


def cmd_init():
    if os.path.isdir(VCS_DIR):
        print("Repository already initialized.")
        return
    os.makedirs(OBJECTS_DIR)
    save_commits([])
    print(f"Initialized empty myvcs repository in {os.path.abspath(VCS_DIR)}")


def store_object(path):
    """Copy a file's content into the object store, keyed by its hash."""
    file_hash = sha1_of_file(path)
    obj_path = os.path.join(OBJECTS_DIR, file_hash)
    if not os.path.exists(obj_path):
        shutil.copy2(path, obj_path)
    return file_hash


def current_snapshot():
    return {rel: sha1_of_file(rel) for rel in walk_files(".")}


def cmd_commit(message):
    ensure_repo()
    commits = load_commits()
    last_files = commits[-1]["files"] if commits else {}

    snapshot = current_snapshot()
    if snapshot == last_files:
        print("Nothing to commit, working directory is unchanged.")
        return

    files_map = {}
    for rel in snapshot:
        files_map[rel] = store_object(rel)

    commit_id = f"c{len(commits) + 1}"
    entry = {
        "id": commit_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
        "files": files_map,
    }
    commits.append(entry)
    save_commits(commits)
    print(f"[{commit_id}] {message}")
    print(f"{len(files_map)} file(s) tracked.")


def cmd_log():
    ensure_repo()
    commits = load_commits()
    if not commits:
        print("No commits yet.")
        return
    for entry in reversed(commits):
        print(f"commit {entry['id']}")
        print(f"Date:    {entry['timestamp']}")
        print(f"Message: {entry['message']}")
        print(f"Files:   {len(entry['files'])}")
        print("-" * 40)


def find_commit(commits, commit_id):
    for entry in commits:
        if entry["id"] == commit_id:
            return entry
    return None


def cmd_revert(commit_id):
    ensure_repo()
    commits = load_commits()
    entry = find_commit(commits, commit_id)
    if not entry:
        print(f"No such commit: {commit_id}")
        sys.exit(1)

    for rel, file_hash in entry["files"].items():
        obj_path = os.path.join(OBJECTS_DIR, file_hash)
        dest_dir = os.path.dirname(rel)
        if dest_dir and not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)
        shutil.copy2(obj_path, rel)

    print(f"Reverted working directory to commit {commit_id} ({entry['message']}).")


def cmd_status():
    ensure_repo()
    commits = load_commits()
    last_files = commits[-1]["files"] if commits else {}
    snapshot = current_snapshot()

    added = [f for f in snapshot if f not in last_files]
    removed = [f for f in last_files if f not in snapshot]
    modified = [f for f in snapshot if f in last_files and snapshot[f] != last_files[f]]

    if not (added or removed or modified):
        print("Working directory clean, nothing to commit.")
        return

    if modified:
        print("Modified files:")
        for f in modified:
            print(f"  M  {f}")
    if added:
        print("New files:")
        for f in added:
            print(f"  A  {f}")
    if removed:
        print("Removed files:")
        for f in removed:
            print(f"  D  {f}")


def cmd_diff(target_file):
    ensure_repo()
    commits = load_commits()
    last_files = commits[-1]["files"] if commits else {}

    if target_file not in last_files:
        print(f"No committed version of '{target_file}' to diff against.")
        return

    obj_path = os.path.join(OBJECTS_DIR, last_files[target_file])
    with open(obj_path, "r", errors="replace") as f:
        old_lines = f.readlines()
    with open(target_file, "r", errors="replace") as f:
        new_lines = f.readlines()

    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{target_file}", tofile=f"b/{target_file}",
    )
    sys.stdout.writelines(diff)


def main():
    if len(sys.argv) < 2:
        print("Usage: myvcs.py <setup|use|list|remove|where|init|commit|log|status|diff|revert> [args]")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "setup":
        name = args[0] if len(args) >= 1 else None
        path = args[1] if len(args) >= 2 else None
        cmd_setup(name, path)
        return
    if cmd == "use":
        if not args:
            print("Usage: myvcs.py use <project_name>")
            sys.exit(1)
        cmd_use(args[0])
        return
    if cmd == "list":
        cmd_list()
        return
    if cmd == "remove":
        if not args:
            print("Usage: myvcs.py remove <project_name>")
            sys.exit(1)
        cmd_remove(args[0])
        return
    if cmd == "where":
        cmd_where()
        return

    # Every other command operates on a monitored project directory.
    # An optional -p/--project <name> picks a specific one; otherwise
    # the 'current' project is used.
    project_name, args = parse_project_flag(args)
    target_dir = get_target_dir(project_name)
    os.chdir(target_dir)

    if cmd == "init":
        cmd_init()
    elif cmd == "commit":
        message = args[0] if args else "No message"
        cmd_commit(message)
    elif cmd == "log":
        cmd_log()
    elif cmd == "revert":
        if not args:
            print("Usage: myvcs.py revert <commit_id> [-p project]")
            sys.exit(1)
        cmd_revert(args[0])
    elif cmd == "status":
        cmd_status()
    elif cmd == "diff":
        if not args:
            print("Usage: myvcs.py diff <file> [-p project]")
            sys.exit(1)
        cmd_diff(args[0])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
