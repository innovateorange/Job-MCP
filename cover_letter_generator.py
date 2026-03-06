"""
Cover Letter Generator - Job-MCP Project
Issue #7: Generate cover letters using resume, skills, and job description

Architecture designed for easy model swapping:
- Currently implements: T5, BERT
- Future: Drop in your custom Llama model

Author: Job-MCP Team
Date: March 2026
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ResumeData:
    """
    Standard input format for cover letter generation.
    Compatible with resume_processor.py output.
    """
    full_text: str
    skills: List[str]
    contact_info: Optional[Dict[str, str]] = None
    
    # Optional fields for richer generation
    summary: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    
    @classmethod
    def from_resume_processor(cls, processor_output: Dict) -> "ResumeData":
        """
        Create ResumeData from resume_processor.py output.
        
        Args:
            processor_output: JSON output from process_resume()
            
        Returns:
            ResumeData instance
        """
        return cls(
            full_text=processor_output.get("full_text", ""),
            skills=processor_output.get("skills_detected", []),
            contact_info=processor_output.get("contact_info"),
            summary=processor_output.get("summary"),
        )


@dataclass
class JobDescription:
    """Job posting information."""
    description: str
    title: Optional[str] = None
    company: Optional[str] = None
    requirements: Optional[List[str]] = None
    
    @classmethod
    def from_text(cls, text: str, title: str = None, company: str = None) -> "JobDescription":
        """Create from raw job description text."""
        return cls(
            description=text,
            title=title or "the position",
            company=company or "your company"
        )


@dataclass
class CoverLetterResult:
    """Output from cover letter generation."""
    cover_letter: str
    model_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "cover_letter": self.cover_letter,
            "model_used": self.model_used,
            "metadata": self.metadata
        }


class ModelType(Enum):
    """Available model types."""
    T5 = "t5"
    BERT = "bert"
    LLAMA = "llama"  # Future
    CUSTOM = "custom"  # For any custom model


# =============================================================================
# ABSTRACT BASE CLASS - Extend this for new models
# =============================================================================

class BaseCoverLetterGenerator(ABC):
    """
    Abstract base class for cover letter generators.
    
    To add a new model (e.g., your Llama model):
    1. Create a new class that inherits from this
    2. Implement the abstract methods
    3. Register it in CoverLetterFactory
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
    
    @abstractmethod
    def load_model(self) -> None:
        """Load the model and tokenizer. Called once on initialization."""
        pass
    
    @abstractmethod
    def generate(
        self,
        resume: ResumeData,
        job: JobDescription,
        **kwargs
    ) -> CoverLetterResult:
        """
        Generate a cover letter.
        
        Args:
            resume: Parsed resume data
            job: Job description data
            **kwargs: Model-specific parameters
            
        Returns:
            CoverLetterResult with generated cover letter
        """
        pass
    
    def prepare_prompt(self, resume: ResumeData, job: JobDescription) -> str:
        """
        Prepare the input prompt. Override for custom formatting.
        
        Default implementation creates a structured prompt.
        """
        skills_str = ", ".join(resume.skills[:15])  # Limit skills
        resume_text = resume.summary or resume.full_text[:500]
        
        prompt = f"""Write a professional cover letter for:

Position: {job.title}
Company: {job.company}

Job Description:
{job.description[:800]}

Candidate Skills: {skills_str}

Candidate Background:
{resume_text}

Cover Letter:"""
        
        return prompt


# =============================================================================
# T5 IMPLEMENTATION
# =============================================================================

class T5CoverLetterGenerator(BaseCoverLetterGenerator):
    """
    T5-based cover letter generator.
    Uses text-to-text generation.
    """
    
    def __init__(self, model_name: str = "t5-small"):
        super().__init__(model_name)
        self.load_model()
    
    def load_model(self) -> None:
        """Load T5 model and tokenizer."""
        from transformers import T5Tokenizer, T5ForConditionalGeneration
        
        print(f"Loading T5 model: {self.model_name}...")
        self._tokenizer = T5Tokenizer.from_pretrained(self.model_name)
        self._model = T5ForConditionalGeneration.from_pretrained(self.model_name)
        self._model.eval()
        print("T5 model loaded.")
    
    def generate(
        self,
        resume: ResumeData,
        job: JobDescription,
        max_length: int = 300,
        num_beams: int = 4,
        temperature: float = 0.8,
        **kwargs
    ) -> CoverLetterResult:
        """Generate cover letter using T5."""
        import torch
        
        prompt = self.prepare_prompt(resume, job)
        
        inputs = self._tokenizer.encode(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True
        )
        
        with torch.no_grad():
            outputs = self._model.generate(
                inputs,
                max_length=max_length,
                num_beams=num_beams,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )
        
        cover_letter = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return CoverLetterResult(
            cover_letter=cover_letter,
            model_used=self.model_name,
            metadata={
                "max_length": max_length,
                "num_beams": num_beams,
                "temperature": temperature,
                "input_tokens": len(inputs[0]),
                "output_tokens": len(outputs[0]),
            }
        )


# =============================================================================
# BERT IMPLEMENTATION
# =============================================================================

class BERTCoverLetterGenerator(BaseCoverLetterGenerator):
    """
    BERT-based cover letter generator.
    
    Note: BERT is an encoder, not a generator. This implementation:
    1. Uses BERT embeddings to match skills to job requirements
    2. Generates cover letter using intelligent template filling
    """
    
    def __init__(self, model_name: str = "bert-base-uncased"):
        super().__init__(model_name)
        self.load_model()
    
    def load_model(self) -> None:
        """Load BERT model and tokenizer."""
        from transformers import BertTokenizer, BertModel
        
        print(f"Loading BERT model: {self.model_name}...")
        self._tokenizer = BertTokenizer.from_pretrained(self.model_name)
        self._model = BertModel.from_pretrained(self.model_name)
        self._model.eval()
        print("BERT model loaded.")
    
    def _get_embedding(self, text: str):
        """Get BERT [CLS] embedding for text."""
        import torch
        import numpy as np
        
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )
        
        with torch.no_grad():
            outputs = self._model(**inputs)
            return outputs.last_hidden_state[:, 0, :].numpy()
    
    def _match_skills_to_job(
        self,
        skills: List[str],
        job_description: str,
        top_k: int = 5
    ) -> List[tuple]:
        """Find skills most relevant to job using semantic similarity."""
        from sklearn.metrics.pairwise import cosine_similarity
        
        if not skills:
            return []
        
        job_embedding = self._get_embedding(job_description)
        
        skill_scores = []
        for skill in skills:
            skill_embedding = self._get_embedding(skill)
            similarity = cosine_similarity(job_embedding, skill_embedding)[0][0]
            skill_scores.append((skill, float(similarity)))
        
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        return skill_scores[:top_k]
    
    def generate(
        self,
        resume: ResumeData,
        job: JobDescription,
        top_skills: int = 5,
        **kwargs
    ) -> CoverLetterResult:
        """Generate cover letter using BERT skill matching + template."""
        
        # Match skills to job
        matched_skills = self._match_skills_to_job(
            resume.skills,
            job.description,
            top_k=top_skills
        )
        
        # Format skills for letter
        skill_names = [s[0] for s in matched_skills]
        if len(skill_names) > 1:
            skills_str = ", ".join(skill_names[:-1]) + f", and {skill_names[-1]}"
        elif skill_names:
            skills_str = skill_names[0]
        else:
            skills_str = "relevant skills"
        
        # Get resume summary
        background = resume.summary or resume.full_text[:300]
        
        # Generate with template
        cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job.title} position at {job.company}. After reviewing the job description, I am confident that my background and skills make me an excellent candidate for this role.

{background}

I am particularly excited about this opportunity because my expertise in {skills_str} aligns well with your requirements. I am eager to bring my skills to your team and contribute to {job.company}'s continued success.

Thank you for considering my application. I look forward to the opportunity to discuss how my experience and skills can benefit your team.

Sincerely,
[Your Name]"""
        
        return CoverLetterResult(
            cover_letter=cover_letter,
            model_used=self.model_name,
            metadata={
                "matched_skills": matched_skills,
                "top_skills_used": skill_names,
                "approach": "semantic_matching_template",
            }
        )


# =============================================================================
# LLAMA PLACEHOLDER - Ready for your custom model
# =============================================================================

class LlamaCoverLetterGenerator(BaseCoverLetterGenerator):
    """
    Placeholder for your custom Llama model.
    
    TODO: Implement when Llama model is trained
    
    To implement:
    1. Update load_model() with your model loading logic
    2. Update generate() with your inference logic
    3. Optionally override prepare_prompt() for custom prompting
    """
    
    def __init__(self, model_path: str = None, model_name: str = "llama-custom"):
        self.model_path = model_path
        super().__init__(model_name)
    
    def load_model(self) -> None:
        """
        Load your custom Llama model.
        
        Example implementation:
        ```
        from transformers import LlamaForCausalLM, LlamaTokenizer
        
        self._tokenizer = LlamaTokenizer.from_pretrained(self.model_path)
        self._model = LlamaForCausalLM.from_pretrained(self.model_path)
        self._model.eval()
        ```
        """
        raise NotImplementedError(
            "Llama model not yet implemented. "
            "Update this class with your trained model."
        )
    
    def generate(
        self,
        resume: ResumeData,
        job: JobDescription,
        max_length: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> CoverLetterResult:
        """
        Generate cover letter using Llama.
        
        Example implementation:
        ```
        prompt = self.prepare_prompt(resume, job)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        
        outputs = self._model.generate(
            **inputs,
            max_length=max_length,
            temperature=temperature,
            do_sample=True,
        )
        
        cover_letter = self._tokenizer.decode(outputs[0])
        return CoverLetterResult(cover_letter=cover_letter, model_used=self.model_name)
        ```
        """
        raise NotImplementedError(
            "Llama model not yet implemented. "
            "Update this class with your trained model."
        )
    
    def prepare_prompt(self, resume: ResumeData, job: JobDescription) -> str:
        """
        Custom prompt format for Llama.
        Override this based on how you fine-tuned your model.
        """
        # Example Llama-style prompt format
        return f"""<s>[INST] Write a professional cover letter.

Job Title: {job.title}
Company: {job.company}
Job Description: {job.description[:600]}

Candidate Skills: {', '.join(resume.skills[:10])}
Background: {resume.summary or resume.full_text[:400]}

Write a concise, tailored cover letter: [/INST]"""


# =============================================================================
# FACTORY - Easy model selection
# =============================================================================

class CoverLetterFactory:
    """
    Factory for creating cover letter generators.
    Use this to easily switch between models.
    """
    
    _generators = {
        ModelType.T5: T5CoverLetterGenerator,
        ModelType.BERT: BERTCoverLetterGenerator,
        ModelType.LLAMA: LlamaCoverLetterGenerator,
    }
    
    @classmethod
    def create(
        cls,
        model_type: ModelType,
        **kwargs
    ) -> BaseCoverLetterGenerator:
        """
        Create a cover letter generator.
        
        Args:
            model_type: Which model to use
            **kwargs: Model-specific arguments
            
        Returns:
            Configured generator instance
        """
        if model_type not in cls._generators:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return cls._generators[model_type](**kwargs)
    
    @classmethod
    def register(
        cls,
        model_type: ModelType,
        generator_class: type
    ) -> None:
        """
        Register a new generator class.
        Use this to add your custom models.
        
        Example:
            CoverLetterFactory.register(ModelType.CUSTOM, MyCustomGenerator)
        """
        cls._generators[model_type] = generator_class


# =============================================================================
# COMPARATOR - Compare model outputs
# =============================================================================

class CoverLetterComparator:
    """Compare cover letters from different models."""
    
    def __init__(self):
        from transformers import BertTokenizer, BertModel
        self._tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        self._model = BertModel.from_pretrained("bert-base-uncased")
        self._model.eval()
    
    def _get_embedding(self, text: str):
        import torch
        inputs = self._tokenizer(
            text, return_tensors="pt", max_length=512, truncation=True, padding=True
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
            return outputs.last_hidden_state[:, 0, :].numpy()
    
    def evaluate_alignment(self, cover_letter: str, job_description: str) -> float:
        """Measure semantic alignment (0-1)."""
        from sklearn.metrics.pairwise import cosine_similarity
        cl_emb = self._get_embedding(cover_letter)
        jd_emb = self._get_embedding(job_description)
        return float(cosine_similarity(cl_emb, jd_emb)[0][0])
    
    def evaluate_length(self, cover_letter: str) -> Dict:
        """Get length metrics."""
        words = cover_letter.split()
        sentences = [s for s in cover_letter.split('.') if s.strip()]
        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_words_per_sentence": len(words) / max(len(sentences), 1),
        }
    
    def compare(
        self,
        results: List[CoverLetterResult],
        job_description: str
    ) -> Dict:
        """Compare multiple generation results."""
        comparison = {}
        
        for result in results:
            alignment = self.evaluate_alignment(result.cover_letter, job_description)
            length = self.evaluate_length(result.cover_letter)
            
            comparison[result.model_used] = {
                "alignment_score": round(alignment, 4),
                "length_metrics": length,
                "metadata": result.metadata,
            }
        
        # Pick best
        best = max(comparison.keys(), key=lambda k: comparison[k]["alignment_score"])
        comparison["recommendation"] = {
            "best_model": best,
            "reason": f"Highest alignment ({comparison[best]['alignment_score']})"
        }
        
        return comparison


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_cover_letter(
    resume_data: Dict,
    job_description: str,
    job_title: str = None,
    company: str = None,
    model: ModelType = ModelType.T5,
    **kwargs
) -> CoverLetterResult:
    """
    One-liner convenience function.
    
    Args:
        resume_data: Output from resume_processor.py
        job_description: Job posting text
        job_title: Position title
        company: Company name
        model: Which model to use
        
    Returns:
        CoverLetterResult
    """
    resume = ResumeData.from_resume_processor(resume_data)
    job = JobDescription.from_text(job_description, job_title, company)
    
    generator = CoverLetterFactory.create(model)
    return generator.generate(resume, job, **kwargs)


def compare_models(
    resume_data: Dict,
    job_description: str,
    job_title: str = None,
    company: str = None,
    models: List[ModelType] = None
) -> Dict:
    """
    Generate and compare cover letters from multiple models.
    
    Args:
        resume_data: Output from resume_processor.py
        job_description: Job posting text
        job_title: Position title
        company: Company name
        models: Models to compare (default: T5 and BERT)
        
    Returns:
        Comparison results with recommendation
    """
    if models is None:
        models = [ModelType.T5, ModelType.BERT]
    
    resume = ResumeData.from_resume_processor(resume_data)
    job = JobDescription.from_text(job_description, job_title, company)
    
    results = []
    for model_type in models:
        try:
            generator = CoverLetterFactory.create(model_type)
            result = generator.generate(resume, job)
            results.append(result)
            print(f"✓ Generated with {model_type.value}")
        except NotImplementedError as e:
            print(f"✗ Skipped {model_type.value}: {e}")
    
    comparator = CoverLetterComparator()
    return {
        "results": {r.model_used: r.to_dict() for r in results},
        "comparison": comparator.compare(results, job_description)
    }


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    # Simulate resume_processor.py output
    sample_resume_data = {
        "file_name": "resume.pdf",
        "full_text": """Software developer with 3 years of experience building 
        web applications. Worked at TechStartup Inc developing React frontends 
        and Python backends. Strong problem-solving skills and team collaboration.
        BS in Computer Science from State University.""",
        "skills_detected": [
            "python", "javascript", "react", "sql", "git",
            "problem solving", "teamwork", "communication"
        ],
        "contact_info": {"email": "dev@example.com"},
        "processing_status": "success"
    }
    
    sample_job = """
    We are hiring a Full Stack Developer to join our growing team.
    
    Requirements:
    - 2+ years experience with Python and JavaScript
    - Experience with React or similar frontend framework
    - Database experience (SQL preferred)
    - Strong communication skills
    - Ability to work in an agile environment
    
    Nice to have:
    - AWS experience
    - CI/CD knowledge
    """
    
    print("="*60)
    print("COVER LETTER GENERATOR - Demo")
    print("="*60)
    
    # Test comparison
    comparison = compare_models(
        resume_data=sample_resume_data,
        job_description=sample_job,
        job_title="Full Stack Developer",
        company="GrowthTech Inc."
    )
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    for model_name, result in comparison["results"].items():
        print(f"\n>>> {model_name.upper()} <<<")
        print("-"*40)
        print(result["cover_letter"])
    
    print("\n>>> COMPARISON <<<")
    print("-"*40)
    rec = comparison["comparison"]["recommendation"]
    print(f"Best Model: {rec['best_model']}")
    print(f"Reason: {rec['reason']}")