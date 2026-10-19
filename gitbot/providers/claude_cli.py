import json
import uuid

from .base import Provider, ProviderError
from .cli_support import (
    AUTH_TIMEOUT_SECONDS,
    clear_session_id,
    find_binary,
    get_session_dir,
    get_session_id,
    require_success,
    run_cli,
    save_session_id,
)


class ClaudeCLIProvider(Provider):
    """Generates messages with `claude -p` — headless Claude Code using the
    logged-in subscription (no API key billing). Reuses a single persistent
    session across all models."""

    name = "claude-cli"
    binary = "claude"

    def generate_commit_message(self, prompt: str, model: str) -> str:
        binary = find_binary(self.binary)
        cwd = str(get_session_dir())
        status = run_cli([binary, "auth", "status"], cwd=cwd, timeout=AUTH_TIMEOUT_SECONDS)
        try:
            auth = json.loads(status.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError("could not check Claude subscription login") from exc
        if (status.returncode != 0 or not isinstance(auth, dict)
                or not auth.get("loggedIn")
                or auth.get("authMethod") not in ("claude.ai", "oauth_token")):
            raise ProviderError("Claude subscription is not signed in — run `claude auth login`")

        session_id = get_session_id(self.name)
        result = None
        if session_id:
            result = run_cli(
                [binary, "-p", "--resume", session_id, "--model", model,
                 "--output-format", "text", "--tools", "", "--safe-mode"],
                prompt=prompt, cwd=cwd,
            )
            if result.returncode != 0:
                clear_session_id(self.name)
                session_id = None

        if not session_id:
            session_id = str(uuid.uuid4())
            result = run_cli(
                [binary, "-p", "--session-id", session_id, "--model", model,
                 "--output-format", "text", "--tools", "", "--safe-mode"],
                prompt=prompt, cwd=cwd,
            )
            if result.returncode == 0:
                save_session_id(self.name, session_id)

        require_success(result, "claude -p")


        output = result.stdout.strip()
        if not output:
            raise ProviderError("claude -p returned empty output")
        return output

