from pathlib import Path

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


class CodexCLIProvider(Provider):
    """Use the Codex CLI's existing ChatGPT login, with a pinned Sol model.
    Reuses a single persistent session across requests and models."""

    name = "codex-cli"

    def generate_commit_message(self, prompt: str, model: str) -> str:
        binary = find_binary("codex")
        cwd = str(get_session_dir())
        status = run_cli([binary, "login", "status"], cwd=cwd, timeout=AUTH_TIMEOUT_SECONDS)
        if status.returncode != 0 or "chatgpt" not in (status.stdout + status.stderr).lower():
            raise ProviderError("Codex is not signed in with ChatGPT — run `codex login`")
        output_file = Path(cwd) / "message.txt"
        output_file.unlink(missing_ok=True)

        session_active = bool(get_session_id(self.name))
        result = None
        if session_active:
            result = run_cli(
                [binary, "exec", "--model", model, "--sandbox", "read-only",
                 "--ignore-user-config", "--skip-git-repo-check",
                 "-c", 'approval_policy="never"', "--color", "never",
                 "--output-last-message", str(output_file),
                 "resume", "--last", "-"],
                prompt="Respond only to the supplied text. Do not use tools.\n\n" + prompt,
                cwd=cwd,
            )
            if result.returncode != 0:
                clear_session_id(self.name)
                session_active = False

        if not session_active:
            result = run_cli(
                [binary, "exec", "--model", model, "--sandbox", "read-only",
                 "--ignore-user-config", "--skip-git-repo-check",
                 "-c", 'approval_policy="never"', "--color", "never",
                 "--output-last-message", str(output_file), "-"],
                prompt="Respond only to the supplied text. Do not use tools.\n\n" + prompt,
                cwd=cwd,
            )
            if result.returncode == 0:
                save_session_id(self.name, "active")

        require_success(result, "codex exec")


        try:
            output = output_file.read_text().strip()
        except OSError as exc:
            raise ProviderError("codex exec did not write a final response") from exc
        if not output:
            raise ProviderError("codex exec returned empty output")
        return output

