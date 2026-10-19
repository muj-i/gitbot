import json
from pathlib import Path

from .base import Provider, ProviderError
from .cli_support import (
    clear_session_id,
    find_binary,
    get_session_dir,
    get_session_id,
    require_success,
    run_cli,
    save_session_id,
)


class GeminiCLIProvider(Provider):
    """Use Gemini Flash through Antigravity's supported CLI and cached login.
    Reuses a single persistent conversation across requests and models."""

    name = "gemini-cli"

    def generate_commit_message(self, prompt: str, model: str) -> str:
        binary = find_binary("agy")
        cwd = str(get_session_dir())
        session_id = get_session_id(self.name)
        result = None
        if session_id:
            result = run_cli(
                [binary, "--print", "Respond only to the supplied text. Do not use tools.\n\n" + prompt,
                 "--conversation", session_id,
                 "--model", model, "--output-format", "json", "--mode", "plan",
                 "--sandbox", "--disable-slash-commands", "--print-timeout", "240s"],
                cwd=cwd,
            )
            if result.returncode != 0:
                clear_session_id(self.name)
                session_id = None

        if not session_id:
            result = run_cli(
                [binary, "--print", "Respond only to the supplied text. Do not use tools.\n\n" + prompt,
                 "--model", model, "--output-format", "json", "--mode", "plan",
                 "--sandbox", "--disable-slash-commands", "--print-timeout", "240s"],
                cwd=cwd,
            )

        require_success(result, "agy --print")

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError("Antigravity returned invalid JSON") from exc
        if not isinstance(payload, dict) or payload.get("status") != "SUCCESS":
            raise ProviderError("Antigravity did not complete the request; check login and model access")

        new_conv = payload.get("conversation_id") or payload.get("session_id")
        if new_conv:
            save_session_id(self.name, str(new_conv))


        output = payload.get("response")
        if not isinstance(output, str) or not output.strip():
            raise ProviderError("Antigravity returned empty output")
        return output.strip()

