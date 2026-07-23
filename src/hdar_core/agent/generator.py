import os
import sys
import json
import subprocess
from pathlib import Path


class BaseGenerator:
    """Interface for pluggable intelligence/execution backends."""
    def generate(self, prompt: str, context: dict) -> dict:
        raise NotImplementedError("Subclasses must implement generate")


class GeminiGenerator(BaseGenerator):
    """Invokes Google Gemini models for code and data generation tasks."""
    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: str | None = None):
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def generate(self, prompt: str, context: dict) -> dict:
        if not self.api_key:
            # Fallback mock for offline execution when no API key is set
            return {
                "status": "success",
                "backend": f"Gemini ({self.model_name}) - Offline Fallback",
                "text": f"Simulated output for prompt: '{prompt}'",
                "estimated_tokens": len(prompt) * 2
            }

        # Attempt to import google-genai or fall back to an HTTP API request
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return {
                "status": "success",
                "backend": f"Gemini ({self.model_name}) - SDK Live",
                "text": response.text,
            }
        except ImportError:
            # Fallback to direct HTTP request via urllib to avoid strict sdk dependency
            import urllib.request
            import urllib.error

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    body = json.loads(res.read().decode("utf-8"))
                    text = body["candidates"][0]["content"]["parts"][0]["text"]
                    return {
                        "status": "success",
                        "backend": f"Gemini ({self.model_name}) - HTTP Live",
                        "text": text
                    }
            except Exception as e:
                raise RuntimeError(f"Gemini API request failed: {e}")


class LocalScriptGenerator(BaseGenerator):
    """Executes a local Python script or subprocess CLI command to generate output."""
    def __init__(self, script_path: Path | None = None, command_args: list[str] | None = None):
        self.script_path = script_path
        self.command_args = command_args

    def generate(self, prompt: str, context: dict) -> dict:
        if self.script_path and self.script_path.exists():
            cmd = [sys.executable, str(self.script_path)]
            if self.command_args:
                cmd.extend(self.command_args)
        elif self.command_args:
            cmd = self.command_args
        else:
            # Default fallback command: run a simple python statement
            cmd = [sys.executable, "-c", "import json; print(json.dumps({'local_execution': 'completed'}))"]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output_data = json.loads(res.stdout.strip())
            return {
                "status": "success",
                "backend": "Local Script/Subprocess",
                "output": output_data,
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            return {
                "status": "failed",
                "backend": "Local Script/Subprocess",
                "error": str(e)
            }


class MockGenerator(BaseGenerator):
    """Returns static preconfigured mock output for fast, zero-dependency testing."""
    def __init__(self, predefined_response: dict | None = None):
        self.predefined_response = predefined_response or {
            "status": "success",
            "backend": "Mock Static",
            "text": "Hello from mock intelligence generator!"
        }

    def generate(self, prompt: str, context: dict) -> dict:
        return self.predefined_response
