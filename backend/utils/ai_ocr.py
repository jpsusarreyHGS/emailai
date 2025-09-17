import os
import tempfile
from aihub import LLMInterface


class OCRClient:
    """OCR client using AIHub's Azure OpenAI integration via LLMInterface."""

    def __init__(self):
        self.system_prompt = (
            "You are an OCR engine. Return ONLY the exact readable text from the image. "
            "No commentary, no extra words. Preserve natural line breaks."
        )

        self.llm = LLMInterface.create(
            provider_name="azure-openai",
            system_prompt=self.system_prompt
        )

    def extract_text_from_image_bytes(self, image_bytes: bytes) -> str:
        """
        Save bytes to a temporary file and run OCR using LLMInterface.
        """
        with tempfile.NamedTemporaryFile(delete=True, suffix=".png") as tmp:
            tmp.write(image_bytes)
            tmp.flush()

            prompt = (
                "Extract the exact text from the following image. "
                f"Image path: {tmp.name}"
            )

            response = self.llm.generate(prompt=prompt)

            return response if isinstance(response, str) else str(response)
