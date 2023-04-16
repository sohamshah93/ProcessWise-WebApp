import openai
import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
import tempfile
import PyPDF2
import re
import io
import sqlite3
from datetime import datetime


# Set up the OpenAI API key
openai.api_key = "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"


def pdf_to_images(pdf_path):
    """
    Convert a PDF file to a list of Pillow Image objects.

    Parameters:
    pdf_path (str): The path to the PDF file.

    Returns:
    A list of Pillow Image objects representing each page of the PDF.
    """

    images = convert_from_path(pdf_path,500, poppler_path=r'C:\poppler-0.68.0\bin')
    return images


def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                # Extract the text from the page
                page = pdf_reader.pages[page_num]
                text += page.extract_text()

                # Convert the page to an image and use OCR to extract any additional text
                #with tempfile.TemporaryDirectory() as tmpdir:
                 #   image_path = os.path.join(tmpdir, f"page{page_num}.jpg")
                  #  with open(image_path, "wb") as image_file:
                   #     page_image = page.getPixmap().getImage()
                    #    page_image.writePNG(image_file)

                    #additional_text = pytesseract.image_to_string(Image.open(image_path))
                    #text += additional_text

        return text
    except Exception as e:
        print("Error in extract_text_from_pdf:", str(e))
        raise e


def extract_invoice_information(text, simple_fields, column_fields):
    try:
        # Create a list of prompts for simple fields
        simple_field_prompts = [f"Extract the {field}" for field in simple_fields]

        # Create the prompt for item table extraction
        table_extraction_prompt = f"""Extract a table with the following columns from the text: {', '.join(column_fields)}. The table might have variations, such as the presence or absence of a Discount field. Make sure to correctly identify the Unit Price and not confuse it with any other price or discount information. If a Discount field is present, extract it along with the other columns."""

        # Combine simple field prompts and table extraction prompt
        combined_prompts = simple_field_prompts + [table_extraction_prompt]

        # Format the combined prompts for GPT-3.5-turbo
        prompt = "\n".join(combined_prompts)

        initial_message = {
            "role": "system",
            "content": f"I have the following invoice information:\n\n{text}",
        }

        messages = [initial_message, {"role": "user", "content": prompt}]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            n=1,
            temperature=0.2,
        )

        result = response.choices[0].message.content

        # Add this line to print the GPT-3.5-turbo response
        print("GPT-3.5-turbo response:", result)
        token_usage = response['usage']['total_tokens']

        return result, token_usage

        #return result
    except Exception as e:
        print("Error in extract_invoice_information:", str(e))
        raise e


def save_to_excel(excel_filepath, invoice_info, simple_fields, column_fields):
    try:
        # Split the invoice info into separate lines
        lines = invoice_info.split('\n')

        # Extract simple field values
        simple_field_values = []
        table_lines = []
        for line in lines:
            if line.startswith('Table:'):
                continue
            if not line.strip():  # Skip empty lines
                continue
            if ':' in line:
                value = line.split(': ')[1]
                simple_field_values.append(value)
            else:
                table_lines.append(line)

        # Create a table DataFrame from the extracted table lines
        table_string = "\n".join(table_lines)
        table_df = pd.read_csv(io.StringIO(table_string), sep='\s*\|\s*', engine='python')

        # Save simple fields to the first sheet of the Excel file
        simple_df = pd.DataFrame(columns=simple_fields)
        if os.path.exists(excel_filepath):
            simple_df = pd.read_excel(excel_filepath, sheet_name='Simple Fields')
        simple_df = simple_df.append(pd.Series(simple_field_values, index=simple_fields), ignore_index=True)

        with pd.ExcelWriter(excel_filepath) as writer:
            simple_df.to_excel(writer, index=False, sheet_name='Simple Fields')

            # Save the item table to a separate sheet in the Excel file
            table_df.to_excel(writer, index=False, sheet_name='Item Table')

    except Exception as e:
        print("Error in save_to_excel:", str(e))
        raise e
def initialize_db():
    conn = sqlite3.connect("document_processing.db")
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT NOT NULL,
            processed_at TIMESTAMP NOT NULL,
            tokens_used INTEGER NOT NULL
        );
    """)
    conn.commit()
    return conn


def save_to_db(conn, document_name, token_usage):
    cursor = conn.cursor()
    processed_at = datetime.now()
    cursor.execute("""
        INSERT INTO document_data (document_name, processed_at, tokens_used)
        VALUES (?, ?, ?);
    """, (document_name, processed_at, token_usage))
    conn.commit()
"""
def process_file(file_path):
    try:
        text = extract_text_from_pdf(file_path)
        invoice_info = extract_invoice_information(text)
        save_to_excel(invoice_info)

        return invoice_info
    except Exception as e:
        print("Error in process_file:", str(e))
        raise e
"""
