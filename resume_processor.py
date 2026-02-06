"""
Resume Processor - Job-MCP Project
Extracts text and skills from resume files (PDF/images) using OCR and T5 LLM
Author: Armani
Date: February 2026
"""

from paddleocr import PaddleOCR
import PyPDF2
import json
import re
import sys
from transformers import T5Tokenizer, T5ForConditionalGeneration
from pathlib import Path

# Initialize OCR with English language support
print("Initializing PaddleOCR...")
ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

# Initialize T5 model for skill extraction
print("Loading T5 model (this may take a moment on first run)...")
tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")
print("Model loaded successfully!\n")

def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            print(f"Processing PDF with {num_pages} page(s)...")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"  - Extracted page {page_num}/{num_pages}")
                
    except FileNotFoundError:
        print(f"Error: File not found at {pdf_path}")
        return None
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
    
    return text

def extract_text_from_image(image_path):
    """
    Extract text from an image using OCR.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        str: Extracted text content
    """
    try:
        print(f"Running OCR on image...")
        result = ocr.ocr(image_path, cls=True)
        
        if not result or not result[0]:
            print("Warning: No text detected in image")
            return ""
        
        text = ""
        for line in result[0]:
            # Each line is a tuple: (bbox, (text, confidence))
            text += line[1][0] + " "
            
        print(f"  - Extracted {len(result[0])} text lines from image")
        return text
        
    except FileNotFoundError:
        print(f"Error: File not found at {image_path}")
        return None
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def clean_text(text):
    """
    Clean and normalize extracted text.
    
    Args:
        text (str): Raw extracted text
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep important punctuation
    text = re.sub(r'[^\w\s.,;:()\-@#+/]', '', text)
    
    # Remove multiple consecutive periods or commas
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r',{2,}', ',', text)
    
    return text.strip()

def extract_skills_with_keyword_matching(text):
    """
    Extract skills using keyword matching against a predefined list.
    
    Args:
        text (str): Resume text content
        
    Returns:
        list: List of detected skills
    """
    # Comprehensive skill keywords list
    skill_keywords = [
        # Programming Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 
        'php', 'swift', 'kotlin', 'go', 'rust', 'scala', 'r', 'matlab',
        
        # Web Technologies
        'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express',
        'django', 'flask', 'spring', 'asp.net', 'jquery', 'bootstrap',
        'tailwind', 'sass', 'webpack',
        
        # Databases
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle',
        'sqlite', 'dynamodb', 'cassandra', 'neo4j',
        
        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
        'terraform', 'ansible', 'ci/cd', 'github actions', 'gitlab',
        
        # Data Science & ML
        'machine learning', 'deep learning', 'data analysis', 'data science',
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
        'jupyter', 'tableau', 'power bi', 'spark', 'hadoop',
        
        # Tools & Frameworks
        'git', 'jira', 'confluence', 'slack', 'trello', 'figma',
        'adobe', 'photoshop', 'illustrator',
        
        # Methodologies
        'agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd',
        
        # Soft Skills
        'leadership', 'communication', 'teamwork', 'problem solving',
        'project management', 'time management', 'critical thinking',
        'analytical', 'presentation', 'collaboration',
        
        # Office & Business
        'excel', 'powerpoint', 'word', 'google sheets', 'salesforce'
    ]
    
    text_lower = text.lower()
    detected_skills = []
    
    for skill in skill_keywords:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            detected_skills.append(skill)
    
    return detected_skills

def extract_skills_with_t5(text, max_skills=20):
    """
    Extract skills using T5 language model.
    
    Args:
        text (str): Resume text content
        max_skills (int): Maximum number of skills to extract
        
    Returns:
        list: List of detected skills
    """
    try:
        # Truncate text if too long (T5 has token limits)
        max_length = 450
        if len(text) > max_length:
            text = text[:max_length]
        
        # Create a clear prompt for T5
        prompt = f"Extract technical skills, programming languages, and tools from this resume text. List them separated by commas: {text}"
        
        # Tokenize input
        input_ids = tokenizer(
            prompt, 
            return_tensors="pt", 
            max_length=512, 
            truncation=True
        ).input_ids
        
        # Generate output
        outputs = model.generate(
            input_ids,
            max_length=150,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=2,
            temperature=0.7
        )
        
        # Decode the output
        skills_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Parse skills from comma-separated output
        skills = [
            skill.strip().lower() 
            for skill in skills_text.split(',') 
            if skill.strip() and len(skill.strip()) > 2
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in skills:
            if skill not in seen:
                seen.add(skill)
                unique_skills.append(skill)
        
        return unique_skills[:max_skills]
        
    except Exception as e:
        print(f"Warning: T5 extraction failed: {e}")
        return []

def extract_contact_info(text):
    """
    Extract basic contact information from resume text.
    
    Args:
        text (str): Resume text content
        
    Returns:
        dict: Dictionary with email and phone if found
    """
    contact_info = {}
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        contact_info['email'] = emails[0]
    
    # Phone pattern (various formats)
    phone_pattern = r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
    phones = re.findall(phone_pattern, text)
    if phones:
        contact_info['phone'] = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"
    
    return contact_info

def process_resume(file_path):
    """
    Main function to process a resume file and extract relevant information.
    
    Args:
        file_path (str): Path to the resume file (PDF or image)
        
    Returns:
        dict: JSON-formatted results with full text and detected skills
    """
    print(f"\n{'='*60}")
    print(f"Processing Resume: {Path(file_path).name}")
    print(f"{'='*60}\n")
    
    # Validate file exists
    if not Path(file_path).exists():
        return {
            "error": "File not found",
            "file_path": file_path
        }
    
    # Step 1: Extract text based on file type
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension == '.pdf':
        text = extract_text_from_pdf(file_path)
    elif file_extension in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
        text = extract_text_from_image(file_path)
    else:
        return {
            "error": "Unsupported file format",
            "supported_formats": [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"],
            "file_path": file_path
        }
    
    # Check if text extraction was successful
    if text is None or len(text.strip()) == 0:
        return {
            "error": "Failed to extract text from file",
            "file_path": file_path
        }
    
    # Step 2: Clean the text
    print("\nCleaning extracted text...")
    cleaned_text = clean_text(text)
    
    print(f"Extracted {len(cleaned_text)} characters of text\n")
    
    # Step 3: Extract skills using both methods
    print("Extracting skills using keyword matching...")
    skills_keyword = extract_skills_with_keyword_matching(cleaned_text)
    print(f"  - Found {len(skills_keyword)} skills via keyword matching")
    
    print("\nExtracting skills using T5 model...")
    skills_t5 = extract_skills_with_t5(cleaned_text)
    print(f"  - Found {len(skills_t5)} skills via T5 model")
    
    # Combine and deduplicate skills
    all_skills = list(set(skills_keyword + skills_t5))
    all_skills.sort()  # Sort alphabetically for consistency
    
    # Step 4: Extract contact information
    print("\nExtracting contact information...")
    contact_info = extract_contact_info(cleaned_text)
    
    # Step 5: Generate output JSON
    result = {
        "file_name": Path(file_path).name,
        "file_type": file_extension,
        "full_text": cleaned_text,
        "skills_detected": all_skills,
        "total_skills_found": len(all_skills),
        "extraction_methods": {
            "keyword_matching": skills_keyword,
            "t5_model": skills_t5
        },
        "contact_info": contact_info if contact_info else None,
        "text_length": len(cleaned_text),
        "processing_status": "success"
    }
    
    print(f"\n{'='*60}")
    print(f"Processing Complete!")
    print(f"Total Skills Detected: {len(all_skills)}")
    print(f"{'='*60}\n")
    
    return result

def main():
    """
    Main entry point for the resume processor.
    Handles command-line arguments and file processing.
    """
    print("\n" + "="*60)
    print("Resume Processor - Job-MCP Project")
    print("="*60 + "\n")
    
    # Check for command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python resume_processor.py <path_to_resume_file>")
        print("\nExample:")
        print("  python resume_processor.py resume.pdf")
        print("  python resume_processor.py resume_image.jpg")
        print("\nSupported formats: PDF, PNG, JPG, JPEG, BMP, TIFF")
        sys.exit(1)
    
    resume_file_path = sys.argv[1]
    
    # Process the resume
    result = process_resume(resume_file_path)
    
    # Display results
    if "error" in result:
        print(f"\nERROR: {result['error']}")
        if "supported_formats" in result:
            print(f"Supported formats: {', '.join(result['supported_formats'])}")
        sys.exit(1)
    
    # Pretty print the JSON output
    print("\n" + "="*60)
    print("JSON OUTPUT:")
    print("="*60)
    output_json = json.dumps(result, indent=2)
    print(output_json)
    
    # Save to file
    output_filename = f"{Path(resume_file_path).stem}_analysis.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {output_filename}")
    print("\n" + "="*60)
    print("Processing completed successfully!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()