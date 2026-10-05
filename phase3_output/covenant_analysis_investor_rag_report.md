# INVESTOR BOND COVENANT RISK REPORT

**Generated:** 2026-10-03 18:25:28  
**RAG embedding model:** Ollama `nomic-embed-text:latest`  
**Analysis model:** Ollama `qwen3.5:0.8b`  
**Scope:** Contractual covenant presence and investor protection; not operational compliance.  

## Executive conclusion

**Investor protection score among present covenants:** 100.0%

The review analyzed 120 covenant requirements against the most relevant 3 numbered bond sections for each requirement. 111 were classified present, 8 absent, and 1 unclear. An unclear result should be treated as requiring legal review rather than as protection.

## Covenant coverage

| Status | Count | Percentage |
|---|---:|---:|
| Present | 111 | 92.5% |
| Absent | 8 | 6.7% |
| Unclear | 1 | 0.8% |

## Critical missing or unclear protections

- **No compromise with creditors affecting security.** — Missing this safeguard increases investor risk: Collateral and security support repayment priority. (retrieved sections: 2.18.part3, 5.21, 2.4)

## Present protective covenants

| Covenant | Strength | Protection | Contract sections |
|---|---|---|---|
| Create security before or within stipulated timelines post allotment. | CRITICAL | The document explicitly outlines investor protections through the detailed disclosure of material contracts and the specific reference to financial covenants, ensuring investors are aware of their rights and obligations. | 8.38, 2.18.part3, 5.38 |
| Perfect security by filing CHG-9 with ROC. | CRITICAL | The document details the specific issue procedure, minimum bid lot, and settlement cycle, providing the investor with clear instructions on how to participate and receive their funds. | 4.1, 2.17, 5.11.part1 |
| Maintain minimum security cover at all times. | CRITICAL | The contract explicitly requires the issuer to maintain a minimum security cover ratio and conduct regular revaluation of hypothecated assets to protect the DebentureHolders from potential loss. | 2.18.part2.occ2, 5.7, 2.17 |
| Replenish security cover immediately upon shortfall. | CRITICAL | The contract explicitly mandates a 'minimum security cover' to ensure investor safety and compliance with the Companies Act, providing a clear mechanism for the issuer to replenish security upon shortfall. | 4.1, 5.7, 2.18.part2.occ2 |
| Provide periodic Security Cover Certificates certified by CA. | CRITICAL | The contract explicitly mandates that all payments to Debenture Holders be free and clear of Tax Deduction, requiring prompt notification of any Tax Deduction or change in rate/basis, which directly protects the investor from tax liabilities. | 4.1, 2.17, 8.25 |
| Replace ineligible or delinquent receivables forming part of security pool. | CRITICAL | The contract explicitly requires the issuer to maintain financial covenants, providing the investor with a clear legal obligation to monitor the issuer's financial health and ensuring the security is maintained. | 4.1, 2.18.part3, 8.25 |
| Top-up collateral if security cover falls below required levels. | CRITICAL | The contract explicitly provides for a mechanism to ensure the DebentureTrustee maintains sufficient security coverage against potential defaults, offering the investor a clear path to mitigate credit risk through the creation of additional collateral. | 2.18.part2.occ2, 5.7, 2.18.part1 |
| Maintain validity and enforceability of all security documents. | CRITICAL | The contract explicitly mandates the Issuers to maintain validity and enforceability of all security documents, ensuring the DebentureTrustee can enforce security rights. | 3.2.part1, 5.7, 2.17 |
| Maintain minimum CRAR/Capital Adequacy Ratio. | CRITICAL | The contract explicitly requires the issuer to maintain a minimum Capital Adequacy Ratio (CRAR) and provides specific mechanisms for replacement, revaluation, and hypothecation of assets to ensure security for DebentureHolders. | 2.18.part2.occ2, 7.4, 8.20 |
| Maintain Gross NPA below prescribed thresholds. | CRITICAL | The contract explicitly mandates that application money be paid into a designated bank account (ICCL) and only from that specific account, preventing the use of third-party accounts or funds from non-specified accounts to satisfy obligations. | 4.2, 2.18.part2.occ2, 8.25 |
| Maintain Net NPA below prescribed thresholds. | CRITICAL | The contract explicitly mandates that the application money be paid into a designated bank account (ICCL) and that any funds received from third-party accounts or unlisted accounts be refunded, thereby protecting the investor from unexpected disbursements or misappropriation of funds. | 4.2, 2.18.part2.occ2, 8.25 |
| Maintain positive profitability (PAT not negative). | CRITICAL | The covenant explicitly protects the investor by prohibiting the issuer from engaging in material regulatory or tax litigation that could result in material liabilities, ensuring the credit quality of the non-convertible securities remains stable. | 5.21, 2.3, 2.7.part1 |
| Maintain DSCR above stipulated threshold. | CRITICAL | The contract explicitly mandates that all payments must be made in totality, preventing partial payments from being treated as defaults and debarment penalties. | 4.2, 8.25, 2.9 |
| Raise minimum equity capital within agreed timelines (where applicable). | CRITICAL | The contract explicitly requires the issuer to provide a list of eligible loans and maintain monthly security cover, ensuring the DebentureTrustee has a defined and enforceable security interest against the Debentures. | 2.18.part2.occ2, 2.4, 2.18.part1.occ2 |
| Submit security cover certificates. | CRITICAL | The explicit requirement for security cover certificates and the specific face value of the debt instruments provide strong investor protection against default and ensure the security is fully valued. | 2.17, 5.7, 2.18.part2.occ2 |
| No redemption of share capital. | CRITICAL | The investor is protected from the loss of their investment if the issuer fails to redeem the shares as required by the contract. | 5.30, 2.18.part1, 5.21 |
| No reduction of capital. | CRITICAL | The covenant explicitly prohibits any reduction of capital, ensuring the investor's equity is protected against potential capital erosion. | 5.21, 2.7.part3, 8.39.part6 |
| No defeasance or return of capital. | CRITICAL | The explicit covenant to not return capital provides strong investor protection against default events. | 2.18.part3, 4.1, 5.7 |
| No change in capital structure without lender consent. | CRITICAL | The covenant explicitly requires disclosure of any material regulatory proceedings, tax litigation, or corporate restructuring events that could impact the issuer's financials or credit quality, providing the investor with specific mechanisms to monitor and mitigate potential credit risks. | 2.13, 5.21, 5.30 |
| No dividend declaration if debt servicing obligations remain unpaid. | CRITICAL | The presence of a security backing clause ensures that the bond is backed by a valid guarantee or letter of comfort, providing the investor with a clear security interest. | 5.30, 2.18.part1.occ2, 5.39.part1 |

## Investor risk interpretation

- **Financial risk:** Missing capital, profitability, asset-quality, or debt-service protections can weaken the issuer's repayment buffer.
- **Leverage risk:** Missing additional-indebtedness restrictions can increase leverage and dilute creditor protection.
- **Cash leakage risk:** Missing dividend restrictions can reduce cash retained for debt service.
- **Information risk:** Missing or unclear audited-reporting covenants can delay early warning of deterioration.
- **Legal review risk:** Semantic retrieval and LLM analysis accelerate review but do not replace counsel's reading of the executed documents.

## Method and limitations

Each covenant was embedded and matched against the top 3 ChromaDB results built from numbered bond sections. The LLM received only those retrieved sections and was instructed to classify contractual presence, not compliance. The report intentionally omits raw evidence excerpts to keep the investor view concise; section references remain for targeted follow-up. LLM failures are marked as fallbacks in the JSON output and are treated as unclear.
