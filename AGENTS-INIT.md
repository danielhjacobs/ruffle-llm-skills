# Initialize the Ruffle Repository

Initialize this directory as a checkout of the official Ruffle repository while preserving the local agent instructions and skills.

1. Confirm that the current working directory is the repository root containing this file and `init_ruffle.py`.

2. Ensure that Python 3 and Git are installed and available. Run the existing initializer; do not recreate it or substitute a shell-based implementation.

   - First try `python init_ruffle.py`.
   - If `python` is unavailable or is not Python 3, use `py -3 init_ruffle.py` on Windows or `python3 init_ruffle.py` on macOS or Linux, as appropriate.

3. Let the script complete. It clones `https://github.com/ruffle-rs/ruffle.git` into a temporary directory before replacing the current working tree.

4. The script preserves the existing root `AGENTS.md` and `.agents/` directory. It replaces the existing Git metadata and other working-tree contents with the upstream Ruffle checkout. Do not run it in a directory containing data that must be preserved outside those exceptions.

5. If initialization fails, read the reported error and stop the current attempt. Do not manually delete `AGENTS-INIT.md`, use an alternate cloning method, or proceed as though initialization succeeded. If Git failed during the initial clone because of DNS, network, proxy, or access restrictions, the existing working tree has not been replaced. After the underlying connectivity problem is resolved, you may rerun this same initializer; do not repeatedly retry while the same failure persists. For failures after the clone completes, follow the specific rollback or recovery message printed by the script.

6. On success, the script removes `AGENTS-INIT.md` and itself. If the script reports that either file could not be removed, follow its cleanup instructions before proceeding.

7. After initialization, follow the retained root `AGENTS.md` and any applicable nested `AGENTS.md` instructions. Do not make commits or push changes as part of initialization.
