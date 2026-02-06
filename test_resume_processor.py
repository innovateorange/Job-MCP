"""
Test script for resume processor
"""
import json
from resume_processor import process_resume

def test_with_sample():
    """Test with a sample resume file"""
    
    # Test with your resume file
    test_file = "sample_resume.pdf"  # Change this to your test file
    
    print("Testing resume processor...")
    result = process_resume(test_file)
    
    if "error" in result:
        print(f"Test failed: {result['error']}")
        return False
    
    print(f"\n✓ Successfully processed: {result['file_name']}")
    print(f"✓ Extracted {result['text_length']} characters")
    print(f"✓ Found {result['total_skills_found']} skills")
    print(f"\nSkills: {', '.join(result['skills_detected'][:10])}...")
    
    return True

if __name__ == "__main__":
    test_with_sample()