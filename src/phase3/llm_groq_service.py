# src/phase3/llm_groq_service.py - AUTO-DETECT available models

import json
import time
import os
from typing import List, Dict, Optional

try:
    from groq import Groq
except ImportError:
    print("❌ groq not installed: pip install groq")
    raise


class GroqLLMService:
    """
    LLM Analysis using Groq API - AUTO-DETECT models
    
    Automatically tries available models - no manual updates needed!
    """
    
    # Try these models in order (most reliable first)
    AVAILABLE_MODELS = [
        "mixtral-8x7b-32768",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.2-90b-vision-preview",
        "llama-3.3-70b-versatile",
        "llama2-70b-4096",
        "gemma2-9b-it",
    ]
    
    def __init__(self, api_key: Optional[str] = None, model: str = "groq/compound"):
        """
        Initialize Groq LLM service - auto-detects available model
        
        Args:
            api_key: Groq API key (or use GROQ_API_KEY env var)
            model: Specific model to use (auto-detects if not provided)
        """
        
        if api_key is None:
            api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            raise ValueError(
                "❌ Groq API key not provided!\n"
                "   Set GROQ_API_KEY environment variable"
            )
        
        self.client = Groq(api_key=api_key)
        self.max_retries = 3
        self.retry_delay = 1
        
        # Auto-detect model if not provided
        if model:
            self.model = model
            print(f"⚡ Groq LLM Service (specified model)")
            print(f"   Model: {self.model}")
        else:
            print(f"⚡ Groq LLM Service (auto-detecting model...)")
            self.model = self._find_available_model()
            print(f"   Model: {self.model} ✅")
        
        self._test_connection()
    
    def _find_available_model(self) -> str:
        """Try models until one works"""
        
        for model_name in self.AVAILABLE_MODELS:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5,
                    temperature=0.1
                )
                print(f"   Found: {model_name}")
                return model_name
            except Exception as e:
                error_str = str(e)
                if "decommissioned" in error_str or "does not exist" in error_str:
                    continue
                else:
                    # Other error, might be rate limit - try anyway
                    try:
                        return model_name
                    except:
                        continue
        
        # Fallback - user's last working model
        print(f"   ⚠️  Using fallback model")
        return "llama-3.1-8b-instant"
    
    def _test_connection(self):
        """Test Groq connection"""
        try:
            print(f"🧪 Testing connection...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Respond: OK"}],
                max_tokens=10,
                temperature=0.1
            )
            
            if response.choices[0].message.content:
                print(f"✅ Groq connection verified")
            else:
                raise Exception("Empty response")
        
        except Exception as e:
            print(f"❌ Groq connection failed: {e}")
            raise
    
    def analyze_covenant(self,
                        covenant: Dict,
                        matched_chunks: List[Dict],
                        max_retries: Optional[int] = None) -> Dict:
        """Analyze a single covenant using Groq"""
        
        if max_retries is None:
            max_retries = self.max_retries
        
        covenant_id = covenant.get('id', '')
        covenant_name = covenant.get('name', '')
        covenant_desc = covenant.get('description', '')
        covenant_type = covenant.get('type', '')
        
        if matched_chunks:
            best_chunk = matched_chunks[0]
            matched_text = f"Similarity: {best_chunk['similarity_score']}\n{best_chunk['text'][:400]}"
        else:
            matched_text = "No matching text found"
        
        # SIMPLE, CLEAR PROMPT
        prompt = f"""Analyze this bond covenant. Return ONLY valid JSON.

Covenant: {covenant_name}
Type: {covenant_type}
Requirement: {covenant_desc}
Bond text: {matched_text}

Respond with JSON (nothing else):
{{"compliant": "Yes|No|Partial", "is_positive": true|false, "confidence": 85, "risk_level": "High|Medium|Low", "investor_impact": "text"}}"""
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.1
                )
                
                response_text = response.choices[0].message.content.strip()
                
                if not response_text:
                    raise Exception("Empty response")
                
                # Extract JSON
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start == -1:
                    raise Exception("No JSON found")
                
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                
                if 'compliant' not in result:
                    raise Exception("Missing compliant field")
                
                result['covenant_id'] = covenant_id
                result['covenant_name'] = covenant_name
                result['matched_chunks'] = matched_chunks
                result['model'] = self.model
                
                return result
            
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return {
                        "covenant_id": covenant_id,
                        "covenant_name": covenant_name,
                        "error": "JSON parse failed",
                        "compliant": "Unknown",
                        "confidence": 0,
                        "matched_chunks": matched_chunks
                    }
            
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return {
                        "covenant_id": covenant_id,
                        "covenant_name": covenant_name,
                        "error": str(e)[:100],
                        "compliant": "Unknown",
                        "confidence": 0,
                        "matched_chunks": matched_chunks
                    }
    
    def analyze_all_covenants(self,
                             retrieval_results: Dict,
                             progress_interval: int = 10) -> List[Dict]:
        """Analyze all covenants using Groq"""
        
        total = len(retrieval_results)
        
        print(f"\n⚡ Analyzing {total} covenants with Groq...")
        print(f"   Model: {self.model}")
        print(f"   Expected time: 8-12 minutes")
        
        analysis_results = []
        errors = 0
        
        for i, (covenant_id, retrieval_data) in enumerate(retrieval_results.items()):
            covenant = retrieval_data['covenant']
            matched_chunks = retrieval_data['matched_chunks']
            
            result = self.analyze_covenant(covenant, matched_chunks)
            analysis_results.append(result)
            
            if 'error' in result:
                errors += 1
            
            if (i + 1) % progress_interval == 0:
                completed = i + 1
                success = completed - errors
                print(f"  ✓ {completed}/{total} analyzed ({success} success, {errors} errors)")
            
            time.sleep(0.2)
        
        print(f"✅ Analysis complete: {len(analysis_results)} covenants")
        if errors > 0:
            print(f"   ⚠️  {errors} errors")
        
        return analysis_results
    
    def get_analysis_stats(self, analysis_results: List[Dict]) -> Dict:
        """Calculate statistics"""
        
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