"""GitHub Actions entrypoint — reads INPUT_* env vars and calls wrapper.run()."""

import asyncio
import os
import sys

# Force line-buffered output so hooks-streaming-ui print() calls appear
# in GH Actions logs in real-time instead of all dumping at once when
# the child session completes (Python buffers stdout when not a tty).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[union-attr]

from amplifier_app_actions import wrapper


def main() -> None:
    """Read INPUT_* env vars and dispatch to wrapper.run() via asyncio.run()."""
    returncode = asyncio.run(
        wrapper.run(
            prompt=os.getenv("INPUT_PROMPT", ""),
            prompt_source=os.getenv("INPUT_PROMPT_SOURCE", ""),
            recipe_source=os.getenv("INPUT_RECIPE_SOURCE", ""),
            attractor_source=os.getenv("INPUT_ATTRACTOR_SOURCE", ""),
            provider=os.getenv("INPUT_PROVIDER", "anthropic"),
            model=os.getenv("INPUT_MODEL", ""),
            bundle=os.getenv("INPUT_BUNDLE", "github-tools"),
            github_token=os.getenv("INPUT_GITHUB_TOKEN", os.getenv("GITHUB_TOKEN", "")),
            event_path=os.getenv("GITHUB_EVENT_PATH", ""),
            enable_reproduction=os.getenv("INPUT_ENABLE_REPRODUCTION", "").lower()
            == "true",
            target_dir=os.getenv("INPUT_TARGET_DIR", ""),
        )
    )
    sys.exit(returncode)


if __name__ == "__main__":
    main()
