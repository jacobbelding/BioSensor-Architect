# Gemini Deep Research Prompt: Plant Biosensor Parts Database Expansion

> Copy-paste this prompt into Google Gemini Pro with Deep Research mode enabled.
> The goal is to get a comprehensive list of papers to ingest via `bsa ingest` to
> expand the curated parts catalog and pathways database.

---

## Prompt

I am building a curated database of plant genetic parts (promoters, reporters, terminators, regulatory elements) and signal transduction pathways for designing transgenic biosensor plants. I need you to do a comprehensive literature search and return a structured list of papers I should read, organized by category.

### What I already have

My current database covers these **signals/pathways** (4 total):
- Nitrate sensing (NRT1.1/CHL1 → NLP7 → NRT2.1 promoter, Arabidopsis)
- Drought/ABA (PYR/PYL → PP2C → SnRK2 → AREB → RD29A promoter, Arabidopsis)
- Heavy metals (MT2A, Arabidopsis)
- Phosphorus starvation (PHR1 → SPX → PHT1;4, Arabidopsis)

My current **parts catalog** has 18 entries:
- Promoters: CaMV 35S, pAtNRT2.1, pRD29A, pMT2A, pAtPHT1;4, pAtHAK5, pOsHKT1;5
- Reporters: GFP, mCherry, GUS (uidA), Firefly Luciferase, Betanin (CYP76AD1+DODA+cDOPA5GT)
- Terminators: NOS, tOCS, tHSP18.2, t35S
- Regulatory: Omega enhancer (TMV), AtADH1 5'UTR intron

### What I need you to find

#### Category 1: Additional signal-responsive promoters (HIGH PRIORITY)
Find papers that characterize promoters responsive to these environmental signals in plants. I need promoters with **published experimental validation** (not just bioinformatic predictions) showing signal-specific induction:

- **Potassium** deficiency/starvation (HAK/KUP/KT family promoters, especially in Arabidopsis, rice, tomato)
- **Iron** deficiency (IRT1, FRO2, FIT promoters)
- **Zinc** excess/deficiency
- **Calcium** signaling
- **Salt/sodium** stress (SOS1, NHX, HKT family)
- **Cold** stress (CBF/DREB, COR promoters)
- **Heat** stress (HSP promoters)
- **Ethylene** (ERF family, EBS elements)
- **Auxin** (DR5, GH3 promoters)
- **Cytokinin** (ARR, TCS/TCSnew synthetic promoters)
- **Light/phytochrome** (CAB, RBCS, phyA/phyB responsive)
- **Pathogen/defense** (PR1, PDF1.2, WRKY promoters)
- **Ammonium** (AMT family promoters)
- **Sulfur** deficiency (SULTR family)
- **Boron** deficiency/toxicity

For each signal, I especially want papers that report:
- Quantitative fold-induction (dose-response data)
- Tissue/organ specificity of expression
- Cross-reactivity with other signals
- Promoter deletions identifying minimal responsive elements

#### Category 2: Reporter systems for plants
Find papers describing reporter genes used in plant biosensors beyond what I already have:
- Anthocyanin pathway reporters (ANT1/PAP1/MYB transcription factors driving visible pigment)
- RUBY reporter system (visible red betalain)
- Split-GFP or BiFC for protein-protein interaction readouts
- Destabilized reporters (dGFP, PEST-tagged) for kinetic measurements
- Ratiometric reporters (dual fluorescent protein systems)
- Bioluminescence reporters optimized for plants (NanoLuc, plant-optimized luciferase)

#### Category 3: Terminators and regulatory elements
- Comparative studies of terminator strength in plants (especially beyond NOS/OCS/35S)
- Enhancer elements that boost expression in specific tissues
- Synthetic 5'UTR and kozak sequences optimized for plant expression
- Intron-mediated enhancement (IME) elements
- Insulator sequences to prevent read-through between cassettes

#### Category 4: Signal transduction pathways
Papers describing the complete signal transduction chain for the signals in Category 1, specifically:
- The receptor/sensor protein
- Intermediate signaling kinases and phosphatases
- Terminal transcription factors that bind promoter cis-elements
- The specific cis-elements (motifs) they bind

#### Category 5: Synthetic biology tools for plants
- Golden Gate / MoClo toolkit papers with standardized plant parts
- CRISPRi/CRISPRa systems in plants (dCas9 fusions for transcriptional control)
- Synthetic promoter design (e.g., combining minimal promoter + cis-elements)
- Logic gates in plants (AND, OR, NOT circuits)

### Output format

For each paper, provide:
1. **PMID** (required — I need this to ingest the paper)
2. **DOI** (if available)
3. **Title**
4. **Year**
5. **Category** (from above: 1-5)
6. **Signal/part** (what specific signal or part this paper is about)
7. **Key finding** (one sentence — what makes this paper useful for my database)
8. **Organism** (which plant species)

Please organize results as a table grouped by category, sorted by relevance within each category. Aim for **60-100 papers total**, prioritizing:
- Highly cited foundational papers characterizing specific promoters
- Recent reviews that reference multiple validated parts
- Papers with quantitative dose-response data
- Papers in Arabidopsis, rice, tomato, and tobacco (most common transformation hosts)

Exclude papers that are purely computational/bioinformatic predictions without experimental validation.
