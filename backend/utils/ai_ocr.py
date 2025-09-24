#backend\utils\ai_ocr.py
from aihub import LLMInterface
from functions.prompts.ocr import EXTRACT_RECEIPT_PROMPT
import json, logging, os, tempfile, time

class OCRClient:
    def __init__(self):
        self.system_prompt = (
            "You are an OCR engine. Return ONLY the exact readable text from the image. "
            "No commentary, no extra words. Preserve natural line breaks."
        )
        self.llm = LLMInterface.create(
            provider_name="azure-openai",
            system_prompt=self.system_prompt
        )
        self.llm_structured = LLMInterface.create(
            provider_name="azure-openai",
            system_prompt=EXTRACT_RECEIPT_PROMPT
        )

    def _safe_generate(self, llm, prompt, images):
        """Call LLM.generate with optional parameters in a backwards-compatible way."""
        try:
            return llm.generate(prompt=prompt, images=images, temperature=0.1)
        except TypeError:
            # If temperature not supported, call without it
            return llm.generate(prompt=prompt, images=images)

    def extract_text_from_image_bytes(self, image_bytes: bytes, prompt_override: str = None) -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        try:
            tmp.write(image_bytes)
            tmp.flush()
            tmp.close()

            # Choose LLM based on whether a structured prompt is provided
            llm_to_use = self.llm
            if prompt_override:
                # Create a one-off client with the provided system prompt
                llm_to_use = LLMInterface.create(
                    provider_name="azure-openai",
                    system_prompt=prompt_override
                )

            prompt = f"Extract the exact text from the following image. Image path: {tmp.name}"

            # Retry strategy: up to 3 attempts, prefer low temperature
            last_response = None
            for attempt in range(3):
                try:
                    response = self._safe_generate(llm_to_use, prompt, images=[tmp.name])
                    text = response if isinstance(response, str) else str(response)
                    # Clean common wrappers
                    if isinstance(text, str) and text.startswith("content="):
                        text = text.replace("content=", "").strip("'\"")
                    # Basic sanity: must have at least a few characters
                    if text and len(text.strip()) >= 5:
                        return text
                    last_response = text
                except Exception as e:
                    logging.warning(f"OCR generate attempt {attempt+1} failed: {e}")
                    last_response = None
                time.sleep(0.2)
            # Return best-effort response
            return last_response or ""
        finally:
            try:
                os.remove(tmp.name)
            except Exception:
                pass

    def extract_structured(self, raw_text: str, multiple_attachments: bool) -> dict:
        response = self.llm_structured.generate(prompt="OCR Text:\n" + raw_text)

        try:
            # Ensure we always get a string
            if isinstance(response, str):
                text = response
            elif hasattr(response, "content"):
                text = response.content
            else:
                text = str(response)

            data = json.loads(text)
        except Exception:
            logging.error("Invalid structured OCR response", exc_info=True)
            data = {
                "merchant": None,
                "date": None,
                "total": None,
                "model_store_number": None,
                "confidence_score": 0,
                "duplication_score": 0
            }

        if not multiple_attachments:
            data["duplication_score"] = 0

        return data
