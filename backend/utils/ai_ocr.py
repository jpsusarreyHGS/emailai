import os
import tempfile

class OCRClient:
    """AIHub (Azure OpenAI) ONLY; writes image to a local temp file and passes its path."""
    def __init__(self):
        self.endpoint   = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_key    = os.environ.get("AZURE_OPENAI_API_KEY")
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        self.api_version= os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        if not all([self.endpoint, self.api_key, self.deployment]):
            raise RuntimeError("Missing AIHub/AOAI env vars: endpoint/key/deployment.")

        from aihub.providers.azure_openai import AzureOpenAIClient  # type: ignore
        self.client = AzureOpenAIClient(
            endpoint=self.endpoint,
            api_key=self.api_key,
            deployment=self.deployment,
            api_version=self.api_version,
        )
        self.system_prompt = (
            "You are an OCR engine. Return ONLY the exact readable text from the image. "
            "No commentary, no extra words. Preserve natural line breaks."
        )

    def extract_text_from_image_bytes(self, image_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".png") as tmp:
            tmp.write(image_bytes)
            tmp.flush()
            resp = self.client.chat(
                system=self.system_prompt,
                messages=[{"role":"user","content":[
                    {"type":"input_text","text":"Extract the exact text from this image."},
                    {"type":"input_image","image_path": tmp.name}
                ]}],
                temperature=0,
                max_tokens=3000,
            )
            return resp if isinstance(resp, str) else str(resp)
