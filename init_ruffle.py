from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPOSITORY_URL = "https://github.com/ruffle-rs/ruffle.git"

SCRIPT_FILE = Path(__file__).resolve()
ROOT = SCRIPT_FILE.parent
INIT_FILE = ROOT / "AGENTS-INIT.md"

# These local bootstrap resources must survive the repository replacement.
PRESERVED_NAMES = {".agents", "AGENTS.md"}
BOOTSTRAP_NAMES = {"AGENTS-INIT.md", SCRIPT_FILE.name}


def exists(path: Path) -> bool:
    """Return whether a path exists, including dangling symlinks."""
    return path.exists() or path.is_symlink()


def remove_path(path: Path) -> None:
    """Remove a file, directory, or symlink."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def is_target_checkout() -> bool:
    """Detect a previous successful run that needs only cleanup."""
    result = subprocess.run(
        ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )

    return (
        result.returncode == 0
        and result.stdout.strip().rstrip("/") == REPOSITORY_URL.rstrip("/")
    )


def finish_bootstrap():
    """Remove bootstrap files, tolerating platforms that lock running scripts."""
    try:
        INIT_FILE.unlink(missing_ok=True)
    except OSError as error:
        return (
            False,
            f"Ruffle was installed, but {INIT_FILE.name} could not be "
            f"removed: {error}. Remove it manually; do not rerun the clone.",
        )

    try:
        SCRIPT_FILE.unlink(missing_ok=True)
    except OSError as error:
        # If the operating system will not let a running script delete
        # itself, keep it locally ignored rather than leaving Git status dirty.
        exclude_file = ROOT / ".git" / "info" / "exclude"
        exclude_line = f"/{SCRIPT_FILE.name}"

        try:
            existing = (
                exclude_file.read_text(encoding="utf-8")
                if exclude_file.exists()
                else ""
            )

            if exclude_line not in existing.splitlines():
                with exclude_file.open("a", encoding="utf-8") as stream:
                    if existing and not existing.endswith("\n"):
                        stream.write("\n")
                    stream.write(exclude_line + "\n")

            return (
                True,
                f"The script could not delete itself ({error}); "
                "it has been excluded from Git status instead.",
            )
        except OSError as exclude_error:
            return (
                True,
                f"Ruffle was installed, but the initializer remains at "
                f"{SCRIPT_FILE}. Automatic exclusion also failed: "
                f"{exclude_error}. Remove the initializer manually.",
            )

    return True, None


def main() -> int:
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError(
            "Run init_ruffle.py from its own directory, the repository root."
        )

    if is_target_checkout():
        # A previous run may have installed Ruffle but failed to remove
        # the bootstrap files. Do not clone a second time in that case.
        success, message = finish_bootstrap()
        if message:
            print(message, file=sys.stderr if not success else sys.stdout)
        if success:
            print("Ruffle is already initialized.")
            return 0
        return 1

    if not INIT_FILE.is_file():
        raise RuntimeError(
            "AGENTS-INIT.md was not found. Refusing to initialize this directory."
        )

    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8 or newer is required.")

    subprocess.run(["git", "--version"], check=True)

    # Fail before cloning or moving anything if the destination itself is
    # read-only. This also avoids trying to roll back a partially moved tree.
    with tempfile.NamedTemporaryFile(
        prefix=".ruffle-write-test-",
        dir=str(ROOT),
        delete=True,
    ):
        pass

    # Use the OS temporary directory: ROOT.parent may be read-only, and
    # shutil.move supports cross-filesystem moves when installing the checkout.
    with tempfile.TemporaryDirectory(
        prefix="ruffle-llm-bootstrap-",
    ) as temporary_directory:
        temporary = Path(temporary_directory)
        checkout = temporary / "checkout"
        backup = temporary / "original"
        backup.mkdir()

        print(f"Cloning {REPOSITORY_URL} ...", flush=True)
        subprocess.run(
            ["git", "clone", REPOSITORY_URL, str(checkout)],
            check=True,
        )

        if not (checkout / ".git").exists():
            raise RuntimeError("The clone does not contain Git metadata.")

        # These names are reserved for local bootstrap files. Fail safely
        # if upstream ever adds one of them to its root.
        upstream_names = {entry.name for entry in checkout.iterdir()}
        conflicts = upstream_names & BOOTSTRAP_NAMES
        if conflicts:
            raise RuntimeError(
                "The upstream checkout contains a reserved bootstrap path: "
                + ", ".join(sorted(conflicts))
            )

        # Preserve all local bootstrap files while moving the rest of the
        # old working tree aside. This includes the old .git metadata.
        installation_started = False
        install_names = upstream_names - PRESERVED_NAMES

        try:
            for entry in list(ROOT.iterdir()):
                if entry.name in PRESERVED_NAMES | BOOTSTRAP_NAMES:
                    continue

                shutil.move(str(entry), str(backup / entry.name))

            # Install all upstream files, including hidden files and .git.
            # The local AGENTS.md and .agents/ are deliberately retained.
            installation_started = True

            for entry in list(checkout.iterdir()):
                if entry.name in PRESERVED_NAMES:
                    continue

                destination = ROOT / entry.name
                if exists(destination):
                    raise RuntimeError(
                        f"Unexpected path conflict during installation: "
                        f"{destination}"
                    )

                shutil.move(str(entry), str(destination))

            origin = subprocess.run(
                ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            if origin.rstrip("/") != REPOSITORY_URL.rstrip("/"):
                raise RuntimeError(
                    f"Unexpected Git origin after installation: {origin}"
                )

            subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
                check=True,
                stdout=subprocess.DEVNULL,
            )

        except BaseException:
            # Restore the original working tree if installation fails.
            if installation_started:
                for name in install_names:
                    path = ROOT / name
                    if exists(path):
                        remove_path(path)

            # Files successfully moved into the backup are restored to
            # their original locations. Do not overwrite an unexpected path.
            for entry in list(backup.iterdir()):
                destination = ROOT / entry.name
                if exists(destination):
                    raise RuntimeError(
                        "Installation failed and rollback encountered a "
                        f"path conflict at {destination}. The backup remains "
                        f"at {backup}."
                    )
                shutil.move(str(entry), str(destination))

            raise

    success, message = finish_bootstrap()
    if message:
        print(message, file=sys.stderr if not success else sys.stdout)

    if not success:
        return 1

    print("Ruffle initialization completed successfully.")
    print("Follow the retained root AGENTS.md instructions.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"Ruffle initialization failed: {error}", file=sys.stderr)
        print(
            "Inspect the error before retrying. "
            "Do not assume initialization succeeded.",
            file=sys.stderr,
        )
        sys.exit(1)
