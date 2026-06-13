import io
import pdfplumber
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_text_from_pdf(pdf_source):
    if hasattr(pdf_source, "read"):
        pdf_source.seek(0)
        pdf_bytes = pdf_source.read()
        pdf_source = io.BytesIO(pdf_bytes)

    text = ""
    with pdfplumber.open(pdf_source) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_syllabus(text):
    prompt = f"""
            You are a structured data explorer.
            Extract Only syllabus unit.
            Each unit should become one JSON object.

            DO NOT create a seperate object for the list of all units.
            DO NOT treat unit names as chapters.
            The chapter field should contain only the topics listed under that unit.

            Return ONLY valid JSON. DO NOT include any additional text or markdown formatting.

            Schema:

            [
            {{
                "subject": "string",
                "unit": "string",
                "chapters": ["string"],
                "exam_date": "YYYY-MM-DD",
                "weightage": "%|null"
            }}
            ]

            syllabus text:

            {text}
        """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    return response.choices[0].message.content


def clean_json_response(raw):
    # Pull out a JSON array from a markdown code block, or just grab from the first [ to the last ].
    match = re.search(r"```(?:json)?\s*(\[.*\])\s*```", raw, re.DOTALL)
    if match:
        return match.group(1)
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in the response.")
    return raw[start:end + 1]


def extract_syllabus_from_pdf(pdf_source):
    text = extract_text_from_pdf(pdf_source)
    raw_response = extract_syllabus(text)
    cleaned_response = clean_json_response(raw_response)
    return json.loads(cleaned_response)


def main():
    text = extract_text_from_pdf("sample_syllabus.pdf")
    raw_response = extract_syllabus(text)
    cleaned_response = clean_json_response(raw_response)
    data = json.loads(cleaned_response)
    with open("extracted_syllabus.json", "w") as f:
        json.dump(data, f, indent=2)

    print("Syllabus extracted and saved to extracted_syllabus.json")


if __name__ == "__main__":
    main()
