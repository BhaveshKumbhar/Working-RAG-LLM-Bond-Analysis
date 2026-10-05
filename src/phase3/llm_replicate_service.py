# src/phase3/llm_replicate_service.py - Using Replicate API (Most Reliable)

import json
import time
import os
from typing import List, Dict, Optional

try:
    import replicate
except ImportError:
    print("❌ replicate not installed")
    print("   Run: pip install replicate")
    raise


class ReplicateLLMService:
    """
    LLM Analysis using Replicate API
    
    Most reliable option - free tier + paid credits available
    """
    
    def __init__(self, api_token: Optional[str] = None, model: str = "mistralai/mistral-7b-instruct-v0.2"):
        """
        Initialize Replicate LLM service
        
        Args:
            api_token: Replicate API token (or use REPLICATE_API_TOKEN env var)
            model: Model version (Mistral 7B is fast and reliable)
        """
        
        if api_token is None:
            api_token = os.getenv('REPLICATE_API_TOKEN')
        
        if not api_token:
            raise ValueError(
                "❌ Replicate API token not provided!\n"
                "   Set REPLICATE_API_TOKEN environment variable\n"
                "   Get free token from: https://replicate.com/account/api-tokens\n"
                "   Free tier: 1000 requests/month (plenty for this!)"
            )
        
        os.environ['REPLICATE_API_TOKEN'] = api_token
        self.model = model
        self.max_retries = 3
        self.retry_delay = 2
        
        print(f"🔄 Replicate LLM Service")
        print(f"   Model: {self.model}")
        
        self._test_connection()
    
    def _test_connection(self):
        """Test Replicate connection"""
        try:
            print(f"🧪 Testing connection...")
            
            # Test with simple prompt
            output = replicate.run(
                self.model,
                input={"prompt": "Test: respond with OK", "max_tokens": 10}
            )
            
            if output:
                print(f"✅ Replicate connection verified")
            else:
                raise Exception("Empty response")
        
        except Exception as e:
            print(f"❌ Replicate connection failed: {e}")
            print(f"   Troubleshooting:")
            print(f"   - Check API token is correct")
            print(f"   - Get token from: https://replicate.com/account/api-tokens")
            print(f"   - Make sure replicate is installed: pip install replicate")
            raise
    
    def analyze_covenant(self,
                        covenant: Dict,
                        matched_chunks: List[Dict],
                        max_retries: Optional[int] = None) -> Dict:
        """
        Analyze a single covenant using Replicate
        """
        
        if max_retries is None:
            max_retries = self.max_retries
        
        covenant_id = covenant.get('id', '')
        covenant_name = covenant.get('name', '')
        covenant_desc = covenant.get('description', '')
        covenant_type = covenant.get('type', '')
        
        if matched_chunks:
            matched_text = "\n\n".join([
                f"Match {i+1} (Similarity: {c['similarity_score']}):\n{c['text'][:300]}"
                for i, c in enumerate(matched_chunks[:2])
            ])
        else:
            matched_text = "No matching text found in bond document"
        
        prompt = f"""Analyze bond covenant compliance. Be concise.

COVENANT: {covenant_name}
TYPE: {covenant_type}
REQUIREMENT: {covenant_desc}

BOND TEXT:
{matched_text}

Respond ONLY with JSON (no other text):
{{"compliant": "Yes/No/Partial", "is_positive": true/false, "confidence": 0-100, "risk_level": "High/Medium/Low", "investor_impact": "1-2 sentences"}}"""
        
        for attempt in range(max_retries):
            try:
                # Replicate returns a generator, need to join
                output = replicate.run(
                    self.model,
                    input={
                        "prompt": prompt,
                        "max_tokens": 200,
                        "temperature": 0.3,
                        "top_p": 0.95
                    }
                )
                
                # Join generator output
                response_text = "".join(output).strip()
                
                if not response_text:
                    raise Exception("Empty response")
                
                # Extract JSON
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
                    raise Exception("No JSON in response")
            
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
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
                if attempt < max_retries - 1:
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
        """Analyze all covenants using Replicate"""
        
        total = len(retrieval_results)
        
        print(f"\n🔄 Analyzing {total} covenants with Replicate...")
        print(f"   Model: {self.model}")
        print(f"   Expected time: {total * 3 // 60} minutes")
        
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
            
            time.sleep(0.3)
        
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