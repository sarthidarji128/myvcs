# myvcs - A Minimal Local Version Control System

`myvcs` is a lightweight, fully local version control system designed for simplicity and offline usability. It's built with a Python engine (`myvcs.py`) and a Bash command-line interface (`myvcs.sh`), providing essential VCS functionalities without relying on external servers or network connectivity.

## What it Solves in Offline Environments

Traditional version control systems like Git often require network access for cloning repositories, pushing/pulling changes, and sometimes even for certain operations if remote tracking is heavily integrated. This can be a significant limitation in environments with:

- **No Internet Access:** Development on isolated networks, air-gapped systems, or during travel without connectivity.
- **Unreliable Network:** Intermittent or slow network connections that make frequent remote VCS operations cumbersome or impossible.
- **Local-Only Projects:** For personal projects, scripts, or configurations where a full-blown distributed VCS might be overkill, and only local history management is needed.

`myvcs` addresses these challenges by:

- **Purely Local Operations:** All object storage, commit history, and version tracking happen exclusively on your local machine within a hidden `.myvcs/` directory inside your monitored project. No remote repositories, no network calls.
- **Zero External Dependencies (Beyond Python/Bash):** It leverages standard Python libraries and Bash, making it highly portable and easy to set up in environments where installing complex software or network access is restricted.
- **Simple Project Management:** Allows you to manage multiple independent projects, each with its own version history, from a single `myvcs` installation. You can easily switch between monitoring different local directories.

## Features

- **Project Setup & Management:** Easily register, switch, list, and remove projects being monitored.
- **Initialization:** Sets up the `.myvcs/` repository in a target directory.
- **Commit:** Create snapshots of changes with a custom message.
- **Log:** View the commit history for a project.
- **Status:** See which files have been added, modified, or removed since the last commit.
- **Diff:** View line-by-line changes for a specific file against its last committed version.
- **Revert:** Restore the working directory to a specific commit.
- **Object Storage:** Stores file contents efficiently, similar to Git's object model.

## How to Use

### First-Time Setup

Simply run any `myvcs` command, and it will guide you through setting up your first project.

```bash
./myvcs.sh commit "Initial commit"
```

Alternatively, you can manually set up a project:

```bash
./myvcs.sh setup myproject /path/to/your/project
```

### Basic Workflow

1.  **Switch to a project** (if you have multiple):
    ```bash
    ./myvcs.sh use myproject
    ```

2.  **Make changes** to your files in `/path/to/your/project`.

3.  **Check status:**
    ```bash
    ./myvcs.sh status
    ```

4.  **View differences** for a specific file:
    ```bash
    ./myvcs.sh diff my_file.txt
    ```

5.  **Commit changes:**
    ```bash
    ./myvcs.sh commit "Description of changes"
    ```

6.  **View commit log:**
    ```bash
    ./myvcs.sh log
    ```

7.  **Revert to a past commit** (use `log` to find commit IDs):
    ```bash
    ./myvcs.sh revert c1
    ```

## Project Structure

-   `myvcs.py`: The core Python engine handling VCS logic.
-   `myvcs.sh`: The Bash script providing the command-line interface.
-   `.myvcs_config.json`: (Generated) Stores configurations for monitored projects.
-   `.myvcs/`: (Generated in each monitored project) The repository directory containing:
    -   `objects/`: Stores file contents (objects) identified by their SHA-1 hashes.
    -   `commits.json`: Stores commit metadata and snapshots.

## Installation

`myvcs` is designed to be run directly from its source. No special installation steps are required beyond cloning the repository and ensuring you have Python 3 and Bash installed on your system (which are typically pre-installed on most Linux/macOS systems).

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sarthidarji128/myvcs.git
    cd myvcs

2.  **Ensure executability:**
    The `myvcs.sh` script should already be executable. If not, you might need to run:
    ```bash
    chmod +x myvcs.sh
    ```

You can then run `myvcs` commands using `./myvcs.sh <command>`.

## Author

Sarthi
