# src/phase3/llm_colab_service.py - FINAL FIX with query parameter

import json
import time
import requests
from typing import List, Dict, Optional

class ColobLLMService:
    """
    LLM Analysis using Ollama on Google Colab
    
    FINAL FIX: Query parameter + headers + connection verification
    """
    
    def __init__(self, colab_url: str, model: str = "mistral", timeout: int = 60):
        """
        Initialize Colab LLM service
        
        Args:
            colab_url: ngrok URL from Colab (e.g., https://xyz.ngrok-free.dev)
            model: Model name (mistral, llama2, neural-chat)
            timeout: Request timeout in seconds
        """
        # CRITICAL: Add query parameter to URL
        self.colab_url = colab_url.rstrip('/')
        if '?' not in self.colab_url:
            self.colab_url = f"{self.colab_url}?ngrok-skip-browser-warning=true"
        
        self.model = model
        self.timeout = timeout
        self.max_retries = 3
        self.retry_delay = 2
        
        # ngrok free tier requires these headers
        self.headers = {
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "Bond-Covenant-Analysis/1.0"
        }
        
        print(f"🔗 Colab Ollama Service")
        print(f"   URL: {self.colab_url}")
        print(f"   Model: {self.model}")
        
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to Colab Ollama server"""
        print(f"🧪 Testing connection...")
        
        try:
            # Build URL for API endpoint
            url = f"{self.colab_url}/api/generate"
            
            print(f"   Testing URL: {url}")
            
            response = requests.post(
                url,
                json={
                    "model": self.model,
                    "prompt": "OK",
                    "stream": False
                },
                headers=self.headers,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                print(f"✅ Colab connection verified")
            elif response.status_code == 403:
                print(f"⚠️  HTTP 403 - ngrok might need restart")
                print(f"   Try:")
                print(f"   1. In Colab: ngrok.kill()")
                print(f"   2. Re-run Colab Step 4")
                print(f"   3. Get new URL and try again")
                raise Exception(f"HTTP {response.status_code}: ngrok auth issue")
            else:
                print(f"⚠️  HTTP {response.status_code}: {response.text[:100]}")
                raise Exception(f"HTTP {response.status_code}")
        
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Cannot connect")
            print(f"   Check:")
            print(f"   1. Colab Step 8 is STILL RUNNING")
            print(f"   2. ngrok URL is: {self.colab_url}")
            print(f"   3. Colab has internet access")
            print(f"   4. Try ngrok.kill() and restart in Colab")
            raise
        
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise
    
    def analyze_covenant(self, 
                        covenant: Dict, 
                        matched_chunks: List[Dict],
                        max_retries: Optional[int] = None) -> Dict:
        """
        Analyze a single covenant's compliance using Colab Ollama
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
{{
  "compliant": "Yes/No/Partial",
  "is_positive": true/false,
  "confidence": 0-100,
  "risk_level": "High/Medium/Low",
  "investor_impact": "1-2 sentences"
}}"""
        
        for attempt in range(max_retries):
            try:
                url = f"{self.colab_url}/api/generate"
                
                response = requests.post(
                    url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": 200,
                            "temperature": 0.3
                        }
                    },
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")
                
                response_text = response.json().get('response', '').strip()
                
                if not response_text:
                    raise Exception("Empty response")
                
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
        """Analyze all covenants using Colab Ollama"""
        
        total = len(retrieval_results)
        
        print(f"\n🔬 Analyzing {total} covenants with Colab Ollama...")
        print(f"   Model: {self.model}")
        print(f"   Timeout: {self.timeout}s")
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