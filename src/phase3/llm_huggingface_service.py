# src/phase3/llm_huggingface_service.py - FIXED for working HF model

import json
import time
import os
from typing import List, Dict, Optional

try:
    from huggingface_hub import InferenceClient
except ImportError:
    print("❌ huggingface_hub not installed")
    print("   Run: pip install huggingface_hub")
    raise


class HuggingFaceLLMService:
    """
    LLM Analysis using Hugging Face Inference API
    
    FIXED: Using model that supports text-generation on free tier
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "HuggingFaceH4/zephyr-7b-beta"):
        """
        Initialize Hugging Face LLM service
        
        Args:
            api_key: HF API key (or use HF_API_KEY env var)
            model: Model ID that supports text-generation
            
        Available models (tested on free tier):
            - HuggingFaceH4/zephyr-7b-beta (RECOMMENDED - fastest)
            - mistralai/Mistral-7B-Instruct-v0.1 (good quality)
            - meta-llama/Llama-2-7b-chat-hf (needs approval)
        """
        
        if api_key is None:
            api_key = os.getenv('HF_API_KEY')
        
        if not api_key:
            raise ValueError(
                "❌ Hugging Face API key not provided!\n"
                "   Set HF_API_KEY environment variable or pass as parameter\n"
                "   Get free key from: https://huggingface.co/settings/tokens"
            )
        
        self.client = InferenceClient(api_key=api_key)
        self.model = model
        self.max_retries = 3
        self.retry_delay = 2
        
        print(f"🤗 Hugging Face LLM Service")
        print(f"   Model: {self.model}")
        
        self._test_connection()
    
    def _test_connection(self):
        """Test HF connection"""
        try:
            print(f"🧪 Testing connection...")
            
            # Test with a simple prompt
            response = self.client.text_generation(
                "Test: respond with OK",
                model=self.model,
                max_new_tokens=10
            )
            
            if response and len(response) > 0:
                print(f"✅ Hugging Face connection verified")
            else:
                raise Exception("Empty response")
        
        except Exception as e:
            print(f"❌ Hugging Face connection failed: {e}")
            print(f"   Troubleshooting:")
            print(f"   - Check API key is correct")
            print(f"   - Try waiting a moment and running again")
            print(f"   - Model might be overloaded (try again in 5 min)")
            raise
    
    def analyze_covenant(self,
                        covenant: Dict,
                        matched_chunks: List[Dict],
                        max_retries: Optional[int] = None) -> Dict:
        """
        Analyze a single covenant using Hugging Face
        
        Args:
            covenant: Master covenant definition
            matched_chunks: List of relevant bond chunks
            max_retries: Override default retry count
        
        Returns:
            Dict with compliance analysis
        """
        
        if max_retries is None:
            max_retries = self.max_retries
        
        covenant_id = covenant.get('id', '')
        covenant_name = covenant.get('name', '')
        covenant_desc = covenant.get('description', '')
        covenant_type = covenant.get('type', '')
        
        # Prepare matched text
        if matched_chunks:
            matched_text = "\n\n".join([
                f"Match {i+1} (Similarity: {c['similarity_score']}):\n{c['text'][:300]}"
                for i, c in enumerate(matched_chunks[:2])
            ])
        else:
            matched_text = "No matching text found in bond document"
        
        # Build prompt (optimized for HF models)
        prompt = f"""You are a bond covenant analyst. Analyze this covenant compliance.

COVENANT: {covenant_name}
TYPE: {covenant_type}
REQUIREMENT: {covenant_desc}

BOND TEXT:
{matched_text}

Respond ONLY with valid JSON (no markdown, no explanation):
{{"compliant": "Yes/No/Partial", "is_positive": true/false, "confidence": 0-100, "risk_level": "High/Medium/Low", "investor_impact": "brief text"}}"""
        
        # Query with retries
        for attempt in range(max_retries):
            try:
                response = self.client.text_generation(
                    prompt,
                    model=self.model,
                    max_new_tokens=200,
                    temperature=0.3
                )
                
                if not response:
                    raise Exception("Empty response")
                
                # Extract JSON
                response_text = response.strip()
                
                if '{' in response_text and '}' in response_text:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    json_str = response_text[json_start:json_end]
                    
                    result = json.loads(json_str)
                    result['covenant_id'] = covenant_id
                    result['covenant_name'] = covenant_name
                    result['matched_chunks'] = matched_chunks
                    result['model'] = self.model
                    
                    return result
                else:
                    raise Exception("No JSON found in response")
            
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON parse error for {covenant_id}: {str(e)[:50]}")
                if attempt < max_retries - 1:
                    print(f"      Retrying ({attempt+1}/{max_retries})...")
                    time.sleep(self.retry_delay)
                else:
                    return {
                        "covenant_id": covenant_id,
                        "covenant_name": covenant_name,
                        "error": "JSON parsing failed",
                        "compliant": "Unknown",
                        "confidence": 0,
                        "matched_chunks": matched_chunks
                    }
            
            except Exception as e:
                error_str = str(e)
                print(f"   ⚠️  Error for {covenant_id}: {error_str[:80]}")
                if attempt < max_retries - 1:
                    print(f"      Retrying ({attempt+1}/{max_retries})...")
                    time.sleep(self.retry_delay)
                else:
                    return {
                        "covenant_id": covenant_id,
                        "covenant_name": covenant_name,
                        "error": str(e),
                        "compliant": "Unknown",
                        "confidence": 0,
                        "matched_chunks": matched_chunks
                    }
    
    def analyze_all_covenants(self,
                             retrieval_results: Dict,
                             progress_interval: int = 10) -> List[Dict]:
        """
        Analyze all covenants using Hugging Face
        
        Args:
            retrieval_results: Retrieved chunks per covenant
            progress_interval: Print progress every N covenants
        
        Returns:
            List of analysis results
        """
        
        total = len(retrieval_results)
        
        print(f"\n🤗 Analyzing {total} covenants with Hugging Face...")
        print(f"   Model: {self.model}")
        print(f"   Expected time: {total * 6 // 60} minutes (free tier is rate-limited)")
        
        analysis_results = []
        errors = 0
        
        for i, (covenant_id, retrieval_data) in enumerate(retrieval_results.items()):
            covenant = retrieval_data['covenant']
            matched_chunks = retrieval_data['matched_chunks']
            
            result = self.analyze_covenant(covenant, matched_chunks)
            analysis_results.append(result)
            
            if 'error' in result:
                errors += 1
            
            # Progress update
            if (i + 1) % progress_interval == 0:
                completed = i + 1
                success = completed - errors
                print(f"  ✓ {completed}/{total} analyzed ({success} success, {errors} errors)")
            
            # Rate limiting - HF free tier is slower
            time.sleep(0.5)
        
        print(f"✅ Analysis complete: {len(analysis_results)} covenants")
        if errors > 0:
            print(f"   ⚠️  {errors} errors (will use defaults)")
        
        return analysis_results
    
    def get_analysis_stats(self, analysis_results: List[Dict]) -> Dict:
        """Calculate statistics about analysis results"""
        
        total = len(analysis_results)
        
        compliant = len([r for r in analysis_results if r.get('compliant') == 'Yes'])
        non_compliant = len([r for r in analysis_results if r.get('compliant') == 'No'])
        partial = len([r for r in analysis_results if r.get('compliant') == 'Partial'])
        unknown = total - (compliant + non_compliant + partial)
        
        positive = len([r for r in analysis_results if r.get('is_positive') == True])
        negative = len([r for r in analysis_results if r.get('is_positive') == False])
        
        confidences = [r.get('confidence', 0) for r in analysis_results if 'confidence' in r and isinstance(r.get('confidence'), (int, float))]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        high_risk = len([r for r in analysis_results if r.get('risk_level') == 'High'])
        medium_risk = len([r for r in analysis_results if r.get('risk_level') == 'Medium'])
        low_risk = len([r for r in analysis_results if r.get('risk_level') == 'Low'])
        
        errors = len([r for r in analysis_results if 'error' in r])
        
        return {
            "total_analyzed": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "partial_compliance": partial,
            "unknown": unknown,
            "positive_impact": positive,
            "negative_impact": negative,
            "avg_confidence": round(avg_confidence, 1),
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "errors": errors,
            "model_used": self.model,
            "success_rate": round((total - errors) / total * 100 if total > 0 else 0, 1)
        }