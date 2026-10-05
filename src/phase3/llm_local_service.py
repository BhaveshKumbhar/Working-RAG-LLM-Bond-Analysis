import json, re, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

class LocalLLMService:
    DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

    def __init__(self, model_name=DEFAULT_MODEL, max_retries=1):
        print("Loading model:", model_name)
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, quantization_config=quant_config,
            device_map="auto", torch_dtype=torch.float16, trust_remote_code=True
        )
        self.model.eval()
        print("Model loaded.")

    def _build_prompt(self, covenant, matched_chunks):
        evidence = []
        for i, chunk in enumerate(matched_chunks[:5]):
            evidence.append(f"EVIDENCE {i+1} [Page {chunk['page']}] (sim={chunk['similarity']:.2f}):\n{chunk['text']}")
        evidence_str = "\n\n".join(evidence)
        prompt = f"""You are an assistant analyzing bond covenants.
Master Covenant ID: {covenant['id']}
Name: {covenant['name']}
Requirement: {covenant['description']}

BOND EVIDENCE:
{evidence_str}

Question: Does this evidence show the covenant is satisfied?

Return JSON with keys:
  - compliant (Yes/No/Partial/Unknown)
  - is_positive (true/false)
  - confidence (0-100)
  - risk_level (Low/Medium/High)
  - investor_impact (brief)
  - reason (brief, evidence-based).
"""
        return prompt

    def _parse_json(self, text):
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        # If parsing fails, return unknown structure
        return {"compliant":"Unknown","is_positive":False,"confidence":0,
                "risk_level":"High","investor_impact":"Parsing failed.","reason":cleaned[:100]}

    def analyze_covenant(self, covenant, matched_chunks):
        if not matched_chunks:
            return {"covenant_id": covenant['id'], "covenant_name": covenant['name'],
                    "compliant":"Unknown", "is_positive": covenant['type']=="positive",
                    "confidence":0, "risk_level":"High",
                    "investor_impact":"No evidence found.", "reason":"",
                    "matched_chunks":[], "model": self.DEFAULT_MODEL}
        prompt = self._build_prompt(covenant, matched_chunks)
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=12000)
        inputs = {k: v.to(self.model.device) for k,v in inputs.items()}
        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=300, do_sample=False, pad_token_id=self.tokenizer.eos_token_id)
        response = self.tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        result = self._parse_json(response)
        result.update({
            "covenant_id": covenant['id'], 
            "covenant_name": covenant['name'],
            "is_positive": (covenant['type']=="positive"),
            "matched_chunks": matched_chunks, "model": self.DEFAULT_MODEL
        })
        return result

    def analyze_all_covenants(self, retrieval_results):
        results = []
        for cov_id, data in retrieval_results.items():
            cov = data["covenant"]
            chunks = data["matched_chunks"]
            res = self.analyze_covenant(cov, chunks)
            results.append(res)
        return results
