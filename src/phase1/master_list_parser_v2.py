# master_list_parser_v2.py

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class Covenant:
    """Structured covenant from master list"""
    id: str
    number: str  # e.g., "A.1" or "B.8"
    name: str
    section: str  # e.g., "Regulatory & Corporate Compliance"
    type: str  # "positive" or "negative"
    description: str
    sub_items: List[str]  # If covenant has bullet points
    keywords: List[str]
    criteria: Optional[str] = None
    severity: str = "high"
    check_frequency: str = "quarterly"
    investor_impact: Optional[str] = None

class MasterListParserV2:
    """Parse your covenant master list format"""
    
    def __init__(self):
        # Map section headers to categories and covenant type
        self.positive_sections = {
            "A": {"title": "Regulatory & Corporate Compliance", "category": "regulatory"},
            "B": {"title": "End Use & Utilisation Covenants", "category": "operational"},
            "C": {"title": "Security Creation & Maintenance Covenants", "category": "security"},
            "D": {"title": "Financial Covenants", "category": "financial"},
            "E": {"title": "Reporting & Information Covenants", "category": "reporting"},
            "F": {"title": "Event-Based Reporting Covenants", "category": "reporting"},
            "G": {"title": "Governance Covenants", "category": "governance"},
            "H": {"title": "Inspection & Monitoring Covenants", "category": "governance"},
            "I": {"title": "Shareholding & Management Covenants", "category": "structural"},
        }
        
        self.negative_sections = {
            "A": {"title": "Capital Structure Restrictions", "category": "financial"},
            "B": {"title": "Dividend Restrictions", "category": "financial"},
            "C": {"title": "Debt Restrictions", "category": "financial"},
            "D": {"title": "Security & Asset Disposal Restrictions", "category": "security"},
            "E": {"title": "Merger / M&A Restrictions", "category": "structural"},
            "F": {"title": "Business Restrictions", "category": "operational"},
            "G": {"title": "Constitutional Document Restrictions", "category": "governance"},
            "H": {"title": "Related Party Restrictions", "category": "governance"},
            "I": {"title": "Shareholding & Control Restrictions", "category": "structural"},
            "J": {"title": "Transactions Outside Ordinary Course", "category": "operational"},
            "K": {"title": "Insolvency / Restructuring Restrictions", "category": "financial"},
        }
        
        # Keywords for covenant classification
        self.financial_keywords = [
            "debt", "equity", "ratio", "interest", "coverage", "ebitda", "cash flow",
            "profitability", "pat", "dividends", "dscr", "indebtedness", "capital adequacy",
            "crar", "npa", "leverage"
        ]
        
        self.reporting_keywords = [
            "report", "disclosure", "submit", "financial statements", "audit", "quarterly",
            "annual", "monthly", "mis", "certificate", "information", "notify"
        ]
        
        self.security_keywords = [
            "security", "charge", "collateral", "hypothecated", "receivables", "cover",
            "roc", "cersai", "encumbrance", "asset pool", "eligible"
        ]
        
        self.operational_keywords = [
            "utilization", "proceeds", "usage", "business", "activities", "acquisition",
            "merger", "restructure", "transfer", "sale", "disposal", "transaction"
        ]
        
        self.structural_keywords = [
            "shareholding", "promoter", "management", "control", "board", "composition",
            "constitutional", "voting", "capital structure", "restructuring"
        ]
        
        self.regulatory_keywords = [
            "comply", "compliance", "regulations", "rbi", "sebi", "companies act",
            "nbfc", "registration", "licenses", "approvals", "authorization", "noc"
        ]
        
        self.governance_keywords = [
            "governance", "internal controls", "anti-fraud", "aml", "kyc", "independent",
            "board", "management", "monitoring", "inspection", "access"
        ]
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from covenant text"""
        text_lower = text.lower()
        found_keywords = set()
        
        keyword_groups = {
            "financial": self.financial_keywords,
            "reporting": self.reporting_keywords,
            "security": self.security_keywords,
            "operational": self.operational_keywords,
            "structural": self.structural_keywords,
            "regulatory": self.regulatory_keywords,
            "governance": self.governance_keywords,
        }
        
        for keywords in keyword_groups.values():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.add(keyword)
        
        # Also extract specific financial metrics/terms
        metrics = re.findall(r'\b(CRAR|DSCR|NPA|PAT|NBFC|ROC|CERSAI|CHG-9|RBI|SEBI)\b', text, re.IGNORECASE)
        found_keywords.update([m.upper() for m in metrics])
        
        return sorted(list(found_keywords))
    
    def parse_covenant_item(self, 
                           number: str,
                           text: str,
                           section_title: str,
                           covenant_type: str,
                           category: str) -> Optional[Covenant]:
        """Parse a single covenant item"""
        
        # Split into main description and sub-items
        lines = text.strip().split('\n')
        main_description = lines[0].strip()
        
        # Extract bullet points if any
        sub_items = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('*'):
                sub_items.append(line[1:].strip())
        
        # Skip if empty
        if not main_description:
            return None
        
        # Generate unique ID
        covenant_id = f"COV_{covenant_type[0].upper()}_{number.replace('.', '_')}"
        
        # Extract keywords
        keywords = self.extract_keywords(main_description + " " + " ".join(sub_items))
        
        # Determine severity
        if covenant_type == "negative":
            severity = "high"  # Negative covenants are restrictive
        else:
            # Positive covenants - check if critical
            critical_keywords = ["capital", "security", "compliance", "reporting"]
            severity = "high" if any(k in " ".join(keywords) for k in critical_keywords) else "medium"

        
        # Determine investor impact
        if covenant_type == "positive":
            investor_impact = "Protects investor interests through required actions/disclosures"
        else:
            investor_impact = "Restricts company actions that could harm investor interests"
        
        covenant = Covenant(
            id=covenant_id,
            number=number,
            name=main_description,
            section=section_title,
            type=covenant_type,
            description=main_description,
            sub_items=sub_items,
            keywords=keywords,
            severity=severity,
            check_frequency="quarterly" if "reporting" in category.lower() else "ongoing",
            investor_impact=investor_impact
        )
        
        return covenant
    
    def parse_positive_covenants(self, text: str) -> List[Covenant]:
        """Parse positive covenants section"""
        print("Parsing POSITIVE Covenants...")
        
        covenants = []
        
        # Split by section headers (A, B, C, etc.)
        section_pattern = r'^([A-I])\.\s+(.+?)$'
        current_section = None
        current_section_title = None
        current_section_category = None
        covenant_number = 0
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.rstrip()
            
            # Check for section header
            section_match = re.match(section_pattern, line)
            if section_match:
                section_letter = section_match.group(1)
                current_section = section_letter
                current_section_title = self.positive_sections[section_letter]["title"]
                current_section_category = self.positive_sections[section_letter]["category"]
                covenant_number = 0
                continue
            
            # Check for numbered covenant
            covenant_match = re.match(r'^(\d+)\.\s+(.+?)$', line)
            if covenant_match and current_section:
                covenant_number = int(covenant_match.group(1))
                covenant_text = covenant_match.group(2)
                
                # Collect sub-items until next numbered item or section
                sub_items = []
                
                covenant_id = f"{current_section}.{covenant_number}"
                
                covenant = self.parse_covenant_item(
                    number=covenant_id,
                    text=covenant_text,
                    section_title=current_section_title,
                    covenant_type="positive",
                    category=current_section_category
                )
                
                if covenant:
                    covenants.append(covenant)
            
            # Check for bullet points (sub-items)
            elif line.strip().startswith('*') and current_section and covenant_number > 0:
                # This is a sub-item, it will be captured in next parse
                pass
        
        print(f"Parsed {len(covenants)} positive covenants")
        return covenants
    
    def parse_negative_covenants(self, text: str) -> List[Covenant]:
        """Parse negative covenants section"""
        print("Parsing NEGATIVE Covenants...")
        
        covenants = []
        
        # Split by section headers (A-K)
        current_section = None
        current_section_title = None
        current_section_category = None
        covenant_number = 0
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.rstrip()
            
            # Check for section header (A-K for negative)
            section_match = re.match(r'^([A-K])\.\s+(.+?)$', line)
            if section_match:
                section_letter = section_match.group(1)
                current_section = section_letter
                
                if section_letter in self.negative_sections:
                    current_section_title = self.negative_sections[section_letter]["title"]
                    current_section_category = self.negative_sections[section_letter]["category"]
                
                covenant_number = 0
                continue
            
            # Check for numbered covenant
            covenant_match = re.match(r'^(\d+)\.\s+(.+?)$', line)
            if covenant_match and current_section:
                covenant_number = int(covenant_match.group(1))
                covenant_text = covenant_match.group(2)
                
                covenant_id = f"{current_section}.{covenant_number}"
                
                covenant = self.parse_covenant_item(
                    number=covenant_id,
                    text=covenant_text,
                    section_title=current_section_title,
                    covenant_type="negative",
                    category=current_section_category
                )
                
                if covenant:
                    covenants.append(covenant)
        
        print(f"Parsed {len(covenants)} negative covenants")
        return covenants
    
    def parse_additional_covenants(self, text: str) -> List[Covenant]:
        """Parse additional covenants (bullet points)"""
        print("Parsing ADDITIONAL Covenants...")
        
        covenants = []
        counter = 0
        
        # Find "Additional Positive Covenants" and "Additional Negative Covenants" sections
        positive_start = text.find("Additional Positive Covenants")
        negative_start = text.find("Additional Negative Covenants")
        
        if positive_start > 0:
            positive_text = text[positive_start:negative_start if negative_start > 0 else len(text)]
            
            # Extract bullet points
            bullets = re.findall(r'\*\s*(.+?)(?=\*|$)', positive_text)
            for bullet in bullets:
                if bullet.strip():
                    counter += 1
                    covenant_id = f"ADDITIONAL_POS_{counter}"
                    
                    covenant = Covenant(
                        id=covenant_id,
                        number=f"ADD.P.{counter}",
                        name=bullet.strip(),
                        section="Additional Positive Covenants",
                        type="positive",
                        description=bullet.strip(),
                        sub_items=[],
                        keywords=self.extract_keywords(bullet),
                        severity="medium",
                        investor_impact="Additional protection for investors"
                    )
                    covenants.append(covenant)
        
        if negative_start > 0:
            negative_text = text[negative_start:]
            
            # Extract bullet points
            bullets = re.findall(r'\*\s*(.+?)(?=\*|$)', negative_text)
            counter = 0
            for bullet in bullets:
                if bullet.strip():
                    counter += 1
                    covenant_id = f"ADDITIONAL_NEG_{counter}"
                    
                    covenant = Covenant(
                        id=covenant_id,
                        number=f"ADD.N.{counter}",
                        name=bullet.strip(),
                        section="Additional Negative Covenants",
                        type="negative",
                        description=bullet.strip(),
                        sub_items=[],
                        keywords=self.extract_keywords(bullet),
                        severity="high",
                        investor_impact="Additional restrictions on company actions"
                    )
                    covenants.append(covenant)
        
        print(f"Parsed {len(covenants)} additional covenants")
        return covenants
    
    def parse_master_list(self, master_list_text: str) -> List[Dict]:
        """Parse complete master list"""
        
        # Split into positive and negative sections
        positive_start = master_list_text.find("POSITIVE (AFFIRMATIVE) COVENANTS")
        negative_start = master_list_text.find("MASTER LIST - NEGATIVE COVENANTS")
        additional_start = master_list_text.find("Additional Positive Covenants")
        
        all_covenants = []
        
        # Parse positive covenants
        if positive_start > 0:
            positive_text = master_list_text[positive_start:negative_start]
            positive_covenants = self.parse_positive_covenants(positive_text)
            all_covenants.extend(positive_covenants)
        
        # Parse negative covenants
        if negative_start > 0:
            negative_text = master_list_text[negative_start:additional_start if additional_start > 0 else len(master_list_text)]
            negative_covenants = self.parse_negative_covenants(negative_text)
            all_covenants.extend(negative_covenants)
        
        # Parse additional covenants
        if additional_start > 0:
            additional_text = master_list_text[additional_start:]
            additional_covenants = self.parse_additional_covenants(additional_text)
            all_covenants.extend(additional_covenants)
        
        return [asdict(covenant) for covenant in all_covenants]
    
    def save_to_json(self, covenants: List[Dict], output_path: str = "master_key.json") -> Dict:
        """Save structured covenants to JSON with enhanced metadata"""
        
        # Calculate statistics
        positive_count = len([c for c in covenants if c['type'] == 'positive'])
        negative_count = len([c for c in covenants if c['type'] == 'negative'])
        
        category_counts = {}
        for covenant in covenants:
            cat = covenant.get('keywords', [])[0] if covenant.get('keywords') else 'general'
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Group by section for easy reference
        by_section = {}
        for covenant in covenants:
            section = covenant['section']
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(covenant)
        
        master_key = {
            "version": "2.0",
            "format": "Your Covenant Master List",
            "total_covenants": len(covenants),
            "summary": {
                "positive_covenants": positive_count,
                "negative_covenants": negative_count,
                "additional_covenants": len([c for c in covenants if "ADDITIONAL" in c['id']])
            },
            "by_type": {
                "positive": [c for c in covenants if c['type'] == 'positive'],
                "negative": [c for c in covenants if c['type'] == 'negative']
            },
            "by_section": by_section,
            "all_covenants": covenants
        }
        
        with open(output_path, 'w') as f:
            json.dump(master_key, f, indent=2)
        
        print(f"\nMaster key saved to {output_path}")
        print(f"""
COVENANT SUMMARY:
   Total Covenants: {len(covenants)}
   - Positive Covenants: {positive_count}
   - Negative Covenants: {negative_count}
   
SECTIONS FOUND:
""")
        for section, items in by_section.items():
            print(f"   - {section}: {len(items)} covenants")
        
        return master_key

# Usage
if __name__ == "__main__":
    # Read your master list
    with open("/mnt/user-data/uploads/Covenants.txt", "r") as f:
        master_list_text = f.read()
    
    parser = MasterListParserV2()
    covenants = parser.parse_master_list(master_list_text)
    master_key = parser.save_to_json(covenants, "master_key.json")
    
    # Print first few covenants as sample
    print("\nSAMPLE COVENANTS:")
    for covenant in covenants[:5]:
        print(f"\n   ID: {covenant['id']}")
        print(f"   Name: {covenant['name']}")
        print(f"   Type: {covenant['type']}")
        print(f"   Section: {covenant['section']}")
        print(f"   Keywords: {', '.join(covenant['keywords'][:3])}...")