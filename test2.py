import requests
import json
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Configuration (replace with your own API keys)
OCR_SPACE_API_KEY = 'K82385935688957'  # Your OCR.Space API key
GEMINI_API_KEY = 'AIzaSyAJ3uU_eH5sPsRkadJl2Fg1k6nEglQA34o'  # Your Gemini API key

def ocr_space_extract(image_path, api_key=OCR_SPACE_API_KEY, language='eng'):
    try:
        payload = {
            'isOverlayRequired': True,
            'apikey': api_key,
            'language': language,
            'OCREngine': 2,
            'isTable': True,
            'scale': True,
            'detectOrientation': True
        }
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={image_path: f},
                data=payload
            )
        result = json.loads(response.content.decode())

        if result.get('IsErroredOnProcessing', True):
            error_msg = result.get('ErrorMessage', ['Unknown error'])[0]
            return {'text': '', 'error': f"OCR.Space error: {error_msg}"}

        parsed_results = result.get('ParsedResults', [])
        if not parsed_results:
            return {'text': '', 'error': 'No parsed results from OCR.Space'}

        extracted_text = parsed_results[0].get('ParsedText', '')
        return {'text': extracted_text, 'error': ''}

    except Exception as e:
        return {'text': '', 'error': f"Extraction failed: {str(e)}"}

def gemini_extract_details(raw_text, gemini_api_key=GEMINI_API_KEY):
    """
    Extracts structured details from raw text using Gemini-2.0-Flash.
    
    Args:
        raw_text (str): Combined raw text from bill and warranty images.
        gemini_api_key (str): Gemini API key.
    
    Returns:
        dict: Extracted structured data or {'error': message} on failure.
    """
    try:
        if not genai:
            return {'error': 'Gemini API is not available.'}
        
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = (
            "Try to extract the following details from the provided text:\n"
            "- Shop Name (e.g., store name)\n"
            "- Contact Number (e.g., phone number)\n"
            "- Bill Date (format: YYYY-MM-DD)\n"
            "- Total Amount (numeric, e.g., 123.45; look for 'Total', 'Max Retail Price', 'MRP', or '₹')\n"
            "- Items (list of item names as a comma-separated string, e.g., 'Laptop, Charger')\n"
            "- Warranty Year (numeric, e.g., 1 for '1 Year')\n"
            "Return the result as a JSON object. If a field is missing, use empty string, 0.0, or 0.\n"
            f"Text:\n{raw_text}"
        )
        
        response = model.generate_content(prompt)
        response_text = response.text.strip() if response.text else ""
        
        # Handle JSON parsing more robustly
        if '```json' in response_text:
            json_str = response_text.split('```json')[1].split('```')[0].strip()
            extracted = json.loads(json_str)
        else:
            extracted = json.loads(response_text)
            
        return extracted

    except Exception as e:
        return {'error': f"Gemini API failed: {str(e)}"}

def extract_complete_data(bill_image_path, warranty_image_path=None, ocr_api_key=OCR_SPACE_API_KEY, gemini_api_key=GEMINI_API_KEY):
    try:
        complete_data = ""
        
        # Step 1: Extract text from bill image
        bill_result = ocr_space_extract(bill_image_path, ocr_api_key)
        if bill_result['error']:
            return {'structured_data': {}, 'error': bill_result['error']}
        
        complete_data += f"Bill Text:\n{bill_result['text']}\n\n"

        # Step 2: Extract text from warranty image if provided
        if warranty_image_path:
            warranty_result = ocr_space_extract(warranty_image_path, ocr_api_key)
            if warranty_result['error']:
                return {'structured_data': {}, 'error': warranty_result['error']}
            complete_data += f"Warranty Text:\n{warranty_result['text']}"

        # Step 3: Use Gemini API to extract structured data
        structured_data = gemini_extract_details(complete_data, gemini_api_key)
        if 'error' in structured_data:
            return {'structured_data': {}, 'error': structured_data['error']}

        return {'structured_data': structured_data, 'error': ''}

    except Exception as e:
        error = f"Extraction failed: {str(e)}"
        return {'structured_data': {}, 'error': error}

if __name__ == "__main__":
    print("Welcome to the Bill and Warranty Extraction Tool!")
    
    # Initialize Tkinter root window (hidden)
    root = tk.Tk()
    root.withdraw()
    
    # Prompt user to upload bill image
    print("Please select your bill image...")
    bill_image_path = filedialog.askopenfilename(title="Select Bill Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
    if not bill_image_path:
        print("No bill image selected. Exiting.")
        exit()
    
    # Ask if user wants to upload warranty card
    include_warranty = input("Do you want to upload a warranty card image? (yes/no): ").strip().lower()
    warranty_image_path = None
    if include_warranty == "yes":
        print("Please select your warranty image...")
        warranty_image_path = filedialog.askopenfilename(title="Select Warranty Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if not warranty_image_path:
            print("No warranty image selected.")
    
    # Perform extraction
    result = extract_complete_data(bill_image_path, warranty_image_path)
    
    # Display results
    print("\nExtraction Results:")
    if result['error']:
        print(f"Error: {result['error']}")
    else:
        print(json.dumps(result['structured_data'], indent=2))