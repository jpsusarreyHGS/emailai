# functions/prompts/ocr.py
EXTRACT_RECEIPT_PROMPT = """
Analyze this receipt image and extract the following information. Look carefully at the text and extract what you can see.

Extract these fields:
- merchant: The business/store name (usually at the top, just the name)
- date: The transaction date (look for dates like MM/DD/YYYY)
- total: The final total amount (look for "Total" or "Balance Due" - this is usually the largest amount at the bottom)
- model: Any product model numbers or SKUs (if visible)
- store_number: Store address or location info

IMPORTANT: For the total, look for the final amount that appears after all the line items, taxes, and subtotals. This is usually the last "Total" amount shown on the receipt.

Return your findings as a JSON object with these exact keys:
{
  "merchant": "business name here or null if not found",
  "date": "date here or null if not found",
  "total": "total amount here or null if not found",
  "model": "model/SKU here or null if not found", 
  "store_number": "store address here or null if not found",
  "confidence_score": 85,
  "duplication_score": 0
}

Example for a receipt that shows "Amici Conyers" as merchant, "06/10/2018" as date, and "33.75" as total:
{
  "merchant": "Amici Conyers",
  "date": "06/10/2018", 
  "total": "33.75",
  "model": null,
  "store_number": "1805 Parker RD Suite C110",
  "confidence_score": 90,
  "duplication_score": 0
}

Please examine the receipt carefully and extract what you can see. Return only the JSON object.
"""
