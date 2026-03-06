"""
Unit tests for Cover Letter Generator
Issue #7: Test T5 and BERT models for cover letter generation
"""

import pytest
from cover_letter_generator import (
    CoverLetterInput,
    T5CoverLetterGenerator,
    BERTCoverLetterGenerator,
    CoverLetterComparator,
    GenerationResult,
)


# Test fixtures
@pytest.fixture
def sample_input():
    return CoverLetterInput(
        resume_summary="Software developer with 3 years experience in web development.",
        skills=["Python", "JavaScript", "React", "SQL", "AWS"],
        job_description="Looking for a backend developer with Python and AWS experience.",
        company_name="TestCorp",
        job_title="Backend Developer"
    )


@pytest.fixture
def t5_generator():
    return T5CoverLetterGenerator("t5-small")


@pytest.fixture
def bert_generator():
    return BERTCoverLetterGenerator("bert-base-uncased")


@pytest.fixture
def comparator():
    return CoverLetterComparator()


# --- Input Format Tests ---
class TestCoverLetterInput:
    def test_input_creation(self, sample_input):
        assert sample_input.resume_summary is not None
        assert len(sample_input.skills) == 5
        assert sample_input.company_name == "TestCorp"
    
    def test_default_values(self):
        minimal_input = CoverLetterInput(
            resume_summary="Test summary",
            skills=["Python"],
            job_description="Test job"
        )
        assert minimal_input.company_name == "the company"
        assert minimal_input.job_title == "the position"


# --- T5 Generator Tests ---
class TestT5Generator:
    def test_model_loads(self, t5_generator):
        assert t5_generator.model is not None
        assert t5_generator.tokenizer is not None
        assert t5_generator.model_name == "t5-small"
    
    def test_prepare_input(self, t5_generator, sample_input):
        prompt = t5_generator._prepare_input(sample_input)
        assert "Backend Developer" in prompt
        assert "TestCorp" in prompt
        assert "Python" in prompt
        assert sample_input.resume_summary in prompt
    
    def test_generate_returns_result(self, t5_generator, sample_input):
        result = t5_generator.generate(sample_input, max_length=100)
        assert isinstance(result, GenerationResult)
        assert result.model_name == "t5-small"
        assert len(result.cover_letter) > 0
        assert "max_length" in result.metadata
    
    def test_generate_respects_params(self, t5_generator, sample_input):
        result = t5_generator.generate(
            sample_input,
            max_length=50,
            num_beams=2,
            temperature=0.5
        )
        assert result.metadata["max_length"] == 50
        assert result.metadata["num_beams"] == 2
        assert result.metadata["temperature"] == 0.5


# --- BERT Generator Tests ---
class TestBERTGenerator:
    def test_model_loads(self, bert_generator):
        assert bert_generator.model is not None
        assert bert_generator.tokenizer is not None
        assert bert_generator.model_name == "bert-base-uncased"
    
    def test_get_embedding_shape(self, bert_generator):
        embedding = bert_generator._get_embedding("test text")
        assert embedding.shape == (1, 768)  # BERT base hidden size
    
    def test_skill_matching(self, bert_generator, sample_input):
        matched = bert_generator._match_skills_to_job(
            sample_input.skills,
            sample_input.job_description,
            top_k=3
        )
        assert len(matched) == 3
        assert all(isinstance(s[1], float) for s in matched)
        # Python and AWS should rank high for this job description
        top_skills = [s[0] for s in matched]
        assert "Python" in top_skills or "AWS" in top_skills
    
    def test_generate_returns_result(self, bert_generator, sample_input):
        result = bert_generator.generate(sample_input)
        assert isinstance(result, GenerationResult)
        assert result.model_name == "bert-base-uncased"
        assert len(result.cover_letter) > 0
        assert "matched_skills" in result.metadata
    
    def test_generate_includes_company(self, bert_generator, sample_input):
        result = bert_generator.generate(sample_input)
        assert "TestCorp" in result.cover_letter
        assert "Backend Developer" in result.cover_letter


# --- Comparator Tests ---
class TestComparator:
    def test_alignment_score_range(self, comparator):
        score = comparator.evaluate_alignment(
            "I am a Python developer with AWS experience.",
            "Looking for Python developer with cloud skills."
        )
        assert 0 <= score <= 1
    
    def test_length_metrics(self, comparator):
        text = "This is a test. It has two sentences."
        metrics = comparator.evaluate_length(text)
        assert metrics["word_count"] == 8
        assert metrics["sentence_count"] == 2
    
    def test_compare_multiple_results(self, comparator, sample_input):
        result1 = GenerationResult(
            model_name="model_a",
            cover_letter="I am skilled in Python and AWS.",
            metadata={}
        )
        result2 = GenerationResult(
            model_name="model_b",
            cover_letter="I have experience with backend development.",
            metadata={}
        )
        
        comparison = comparator.compare(
            [result1, result2],
            sample_input.job_description
        )
        
        assert "model_a" in comparison
        assert "model_b" in comparison
        assert "recommendation" in comparison
        assert "best_model" in comparison["recommendation"]


# --- Integration Tests ---
class TestIntegration:
    def test_full_pipeline(self, t5_generator, bert_generator, comparator, sample_input):
        """Test the complete generation and comparison pipeline."""
        
        # Generate with both models
        t5_result = t5_generator.generate(sample_input, max_length=100)
        bert_result = bert_generator.generate(sample_input)
        
        # Compare results
        comparison = comparator.compare(
            [t5_result, bert_result],
            sample_input.job_description
        )
        
        # Verify comparison structure
        assert t5_generator.model_name in comparison
        assert bert_generator.model_name in comparison
        assert comparison["recommendation"]["best_model"] in [
            t5_generator.model_name,
            bert_generator.model_name
        ]


# --- Edge Case Tests ---
class TestEdgeCases:
    def test_single_skill(self, bert_generator):
        single_skill_input = CoverLetterInput(
            resume_summary="Developer",
            skills=["Python"],
            job_description="Need Python developer"
        )
        result = bert_generator.generate(single_skill_input, top_skills=1)
        assert "Python" in result.cover_letter
    
    def test_empty_resume_summary(self, t5_generator):
        empty_resume_input = CoverLetterInput(
            resume_summary="",
            skills=["Python", "Java"],
            job_description="Software engineer needed"
        )
        result = t5_generator.generate(empty_resume_input, max_length=50)
        assert isinstance(result.cover_letter, str)
    
    def test_long_job_description(self, bert_generator):
        long_jd = "Software engineer " * 100  # Very long description
        long_input = CoverLetterInput(
            resume_summary="Experienced developer",
            skills=["Python"],
            job_description=long_jd
        )
        # Should not raise error, handles truncation
        result = bert_generator.generate(long_input)
        assert isinstance(result.cover_letter, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])