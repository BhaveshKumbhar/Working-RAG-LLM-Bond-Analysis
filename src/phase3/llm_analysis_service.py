# src/phase3/llm_analysis_service.py - FIXED: Use new google.genai package

import json
import os
import time
from typing import List, Dict, Optional

try:
    #import google.genai as genai
    from google import genai
    USING_NEW_PACKAGE = True
except ImportError:
    print("⚠️  google.genai not found. Trying deprecated google.generativeai...")
    # try:
    #     import google.generativeai as genai
    #     USING_NEW_PACKAGE = False
    # except ImportError:
    #     print("❌ Neither google.genai nor google.generativeai installed")
    #     print("   Run: pip install google-genai")
    #     raise

class LLMAnalysisService:
    """Analyze covenant compliance using Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini API (using new google.genai package)
        
        Args:
            api_key: Gemini API key (or use GEMINI_API_KEY env var)
        """
        
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError(
                "❌ Gemini API key not provided!\n"
                "   Set GEMINI_API_KEY environment variable or pass as parameter\n"
                "   Get free key from: https://makersuite.google.com/app/apikey"
            )
        
        #genai.configure(api_key=api_key)
        self.client = genai.Client(api_key=api_key)
        # Use available model
        # Try models in order of preference
        self.model_name = None
        self.model = None
        
        # models_to_try = [
        #     'gemini-2.5-flash',
        #     'gemini-2.0-flash',          # Latest (if available)
        #     'gemini-1.5-pro',            # Stable alternative
        #     'gemini-pro',                # Fallback
        # ]
        
        # for model_name in models_to_try:
        #     try:
        #         self.model = genai.GenerativeModel(model_name)
        #         self.model_name = model_name
        #         print(f"🤖 Gemini API initialized (using {model_name})")
        #         break
        #     except Exception as e:
        #         print(f"   ⚠️  Model {model_name} not available: {e}")
        #         continue
        
        # if not self.model:
        #     raise Exception("❌ No supported Gemini model available")

        # Modern way to list and validate supported models
        try:
            available_models = [model.name for model in self.client.models.list()]
            
            # The SDK returns model names like 'gemini-2.5-flash' or 'models/gemini-2.5-flash'
            # Let's check for the recommended production model
            target_model = "gemini-3.6-flash"
            
            if any(target_model in name for name in available_models):
                self.model_name = target_model
            else:
                # Fallback to the first available model if gemini-2.5-flash isn't explicitly found
                if available_models:
                    self.model_name = available_models[0].split('/')[-1]
                else:
                    raise Exception("❌ No supported Gemini model available")
                    
        except Exception as e:
            # If the API call fails entirely, default to the production model rather than breaking the pipeline
            print(f"Warning: Model validation failed ({e}). Defaulting to gemini-3.6-flash.")
            self.model_name = "gemini-3.6-flash"
        
        self._test_connection()
    
    # def _test_connection(self):
    #     """Test Gemini API connection"""
    #     try:
    #         response = self.model.generate_content("Test: respond with 'OK'")
    #         if response.text:
    #             print(f"✅ Gemini API connection verified")
    #         else:
    #             raise Exception("Empty response")
    #     except Exception as e:
    #         print(f"❌ Gemini API connection failed: {e}")
    #         raise
    def _test_connection(self):
        """Tests the connection to the Gemini API using the modern SDK."""
        try:
            # Modern syntax uses client.models.generate_content instead of model.generate_content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Test: respond with 'OK'"
            )
            
            # Verify we got a valid response
            if response and response.text:
                print("✅ Gemini API connection test successful.")
            else:
                raise Exception("Received empty response from Gemini API.")
                
        except Exception as e:
            print(f"❌ Gemini API connection failed: {e}")
            raise e

    
    def analyze_covenant(self,
                        covenant: Dict,
                        matched_chunks: List[Dict],
                        max_retries: int = 3) -> Dict:
        """
        Analyze a single covenant's compliance
        
        Args:
            covenant: Master covenant definition
            matched_chunks: List of relevant bond chunks
            max_retries: Retry attempts if API fails
        
        Returns:
            Dict with compliance analysis
        """
        
        covenant_id = covenant.get('id', '')
        covenant_name = covenant.get('name', '')
        covenant_desc = covenant.get('description', '')
        covenant_type = covenant.get('type', '')
        
        # Prepare matched text
        if matched_chunks:
            matched_text = "\n\n".join([
                f"Match {i+1} (Similarity: {c['similarity_score']}, Page {c['page']}):\n{c['text']}"
                for i, c in enumerate(matched_chunks[:3])
            ])
        else:
            matched_text = "No matching text found in bond document"
        
        # Build prompt
        prompt = f"""You are a bond covenant compliance analyst for an investment firm.

Analyze the following covenant from the master covenant list and determine how well the bond memorandum complies with it.

COVENANT DEFINITION:
==================
Name: {covenant_name}
Type: {covenant_type}
ID: {covenant_id}
Description: {covenant_desc}

MATCHED TEXT FROM BOND DOCUMENT:
===============================
{matched_text}

ANALYSIS TASK:
==============
Based on the matched text from the bond document, analyze:

1. COMPLIANCE: Does the bond appear to comply with this covenant?
   Answer: Yes / No / Partial (if mixed or unclear)

2. IMPACT: Is this positive or negative for an investor?
   - Positive: Bond complies with protective covenant (good for investor)
   - Negative: Bond violates or lacks covenant (bad for investor)
   - Neutral: Unclear or neutral impact

3. CONFIDENCE: How confident are you in your assessment? (0-100)
   - 95-100: Very clear evidence
   - 80-94: Clear evidence with minor ambiguity
   - 65-79: Reasonable interpretation required
   - 50-64: Significant ambiguity
   - <50: Insufficient data

4. RISK LEVEL: What's the risk if this covenant is violated?
   - High: Critical for bondholder protection
   - Medium: Important but manageable
   - Low: Minor concern

5. INVESTOR IMPACT: One sentence on what this means for investor

Respond ONLY with valid JSON (no other text):
{{
  "covenant_id": "{covenant_id}",
  "covenant_name": "{covenant_name}",
  "compliant": "Yes/No/Partial",
  "is_positive": true/false,
  "confidence": <0-100>,
  "risk_level": "High/Medium/Low",
  "investor_impact": "One sentence summary",
  "reasoning": "Brief explanation of your analysis",
  "matched_chunk_count": {len(matched_chunks)},
  "best_similarity": {matched_chunks[0]['similarity_score'] if matched_chunks else 0}
}}"""
        
        # Query Gemini API with retries
        for attempt in range(max_retries):
            try:
                #response = self.model.generate_content(prompt)
                response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )

                if not response.text:
                    raise Exception("Empty response from API")
                
                # Extract JSON from response
                response_text = response.text.strip()
                
                # Try to find JSON in response
                if '{' in response_text and '}' in response_text:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    json_str = response_text[json_start:json_end]
                else:
                    raise Exception("No JSON found in response")
                
                # Parse JSON
                result = json.loads(json_str)
                result['matched_chunks'] = matched_chunks
                
                return result
            
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON parsing error for {covenant_id}: {e}")
                if attempt < max_retries - 1:
                    print(f"      Retrying ({attempt+1}/{max_retries})...")
                    time.sleep(1)
                else:
                    return {
                        "covenant_id": covenant_id,
                        "covenant_name": covenant_name,
                        "error": f"JSON parsing failed: {str(e)}",
                        "compliant": "Unknown",
                        "confidence": 0,
                        "matched_chunks": matched_chunks
                    }
            
            except Exception as e:
                print(f"   ⚠️  API error for {covenant_id}: {e}")
                if attempt < max_retries - 1:
                    print(f"      Retrying ({attempt+1}/{max_retries})...")
                    time.sleep(2)
                else:
                    return {
                        "covenant_id": covenant_id,
                        "covenant_name": covenant_name,
                        "error": f"API error: {str(e)}",
                        "compliant": "Unknown",
                        "confidence": 0,
                        "matched_chunks": matched_chunks
                    }
    
    def analyze_all_covenants(self,
                             retrieval_results: Dict,
                             progress_interval: int = 10) -> List[Dict]:
        """
        Analyze all covenants using Gemini API
        """
        
        print(f"\n🤖 Analyzing {len(retrieval_results)} covenants with Gemini API...")
        print(f"   Using model: {self.model_name}")
        print(f"   This will take ~{len(retrieval_results) * 2 // 60} minutes")
        
        analysis_results = []
        
        for i, (covenant_id, retrieval_data) in enumerate(retrieval_results.items()):
            covenant = retrieval_data['covenant']
            matched_chunks = retrieval_data['matched_chunks']
            
            result = self.analyze_covenant(covenant, matched_chunks)
            analysis_results.append(result)
            
            if (i + 1) % progress_interval == 0:
                print(f"  ✓ Analyzed {i+1}/{len(retrieval_results)} covenants")
            
            time.sleep(0.5)  # Rate limiting
        
        print(f"✅ Analysis complete: {len(analysis_results)} covenants analyzed")
        
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
        
        confidences = [r.get('confidence', 0) for r in analysis_results if 'confidence' in r]
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
            "errors": errors
        }