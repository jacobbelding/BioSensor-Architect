#!/usr/bin/env python3
"""Batch ingest of curated plant genetic parts from Gemini Deep Research PDF.

Directly creates parts catalog and pathways entries from the structured data
in 'Plant Biosensor Genetic Parts Database.pdf' — no LLM calls needed since
the PDF already contains expert-curated information.

Usage:
    python scripts/batch_ingest_gemini_parts.py [--dry-run]
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from biosensor_architect.tools.paper_ingest import (
    PARTS_FILE,
    PATHWAYS_FILE,
    append_to_catalog,
    append_to_pathways,
    deduplicate_parts,
    deduplicate_pathways,
    load_catalog,
    load_pathways,
)

# ============================================================================
# NEW PARTS — extracted from Gemini Deep Research PDF
# ============================================================================

NEW_PARTS = [
    # ── Category 1: Signal-Responsive Promoters ──

    # Potassium
    {
        "id": "pAtHAK5",
        "name": "AtHAK5 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "potassium deficiency",
        "description": "High-affinity K+ transporter promoter. Strongly induced by K+ starvation via CBL1/CBL9-CIPK23 cascade and ethylene signaling (RAP2.11). Also modulated by N and P availability — cross-talk must be managed. Root-specific.",
        "references": ["PMID:39362862", "PMID:24716623"],
        "notes": "Already in catalog — will be deduplicated. Included for completeness."
    },
    # Iron
    {
        "id": "pAtIRT1",
        "name": "AtIRT1 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "iron deficiency",
        "description": "Iron-Regulated Transporter 1 promoter. Exquisitely sensitive to Fe starvation, restricted to root epidermis and cortex. Regulated by FIT/bHLH TF complex upstream through URI phosphorylation. IRT1 protein itself regulated by ubiquitin-mediated turnover at K146/K171.",
        "references": ["PMID:12084823", "PMID:31636177"],
        "notes": "Root external cell layer specific. Cross-reactivity: Zn and Mn can affect IRT1 protein turnover."
    },
    {
        "id": "pAtFRO2",
        "name": "AtFRO2 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "iron deficiency",
        "description": "Ferric Reduction Oxidase 2 promoter. Co-regulated with IRT1 under Fe deficiency via FIT/bHLH TF network. Drives expression of the ferric reductase required for Fe3+ → Fe2+ conversion prior to IRT1 uptake.",
        "references": ["PMID:12084823", "PMID:31636177"],
        "notes": "Strategy I iron acquisition. Root-specific expression."
    },
    # Zinc
    {
        "id": "pAtZIP4",
        "name": "AtZIP4 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "zinc deficiency",
        "description": "ZIP family transporter promoter. Contains the 10-bp ZDRE (Zinc Deficiency Response Element) palindrome bound by bZIP19/bZIP23 TFs. Massive transcriptional induction within 6 hours of Zn deprivation. Isolated ZDRE motifs eliminate cross-reactivity with Fe/Cu starvation.",
        "references": ["PMID:20479230", "PMID:33594269"],
        "notes": "bZIP19/23 are direct intracellular Zn sensors — no upstream kinase required. Highly orthogonal."
    },
    # Calcium
    {
        "id": "pCaResponsive",
        "name": "Synthetic Ca2+ responsive promoter (CRT/DRE + CAM box)",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "calcium",
        "description": "Synthetic arrays of experimentally validated CAMTA-target motifs: C-Repeat/DRE, Site II, and CAM box. Provides rapid, transient transcriptional readout of intracellular Ca2+ spiking. Useful for mapping earliest moments of stress perception.",
        "references": ["PMID:22086087"],
        "notes": "Ca2+ is a universal second messenger — inherently challenging to isolate specific stimuli. Best for kinetic biosensor applications."
    },
    # Salt/Sodium
    {
        "id": "pAtSOS1",
        "name": "AtSOS1 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "salt stress",
        "description": "Salt Overly Sensitive 1 (Na+/H+ antiporter) promoter. Rapidly induced by NaCl exposure via SOS3(CBL4)-SOS2(CIPK24) calcium-dependent signaling cascade. Essential for salt tolerance.",
        "references": ["PMID:10831000"],
        "notes": "SOS pathway: Ca2+ spike → SOS3 → SOS2 → phosphorylates SOS1. Regulation intertwined with ABA/osmotic pathways — truncation needed for salt-specific response."
    },
    {
        "id": "pAtNHX1",
        "name": "AtNHX1 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "salt stress",
        "description": "Vacuolar Na+/H+ exchanger promoter. Induced under saline conditions. NHX1 sequesters Na+ into vacuoles for salt tolerance.",
        "references": ["PMID:10831000"],
        "notes": "Companion to SOS1 — vacuolar compartmentalization arm of salt response."
    },
    # Cold
    {
        "id": "pAtCOR15A",
        "name": "AtCOR15A promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "cold stress",
        "description": "Cold-Regulated gene 15A promoter. Contains CRT/DRE motif (CCGAC) bound by CBF/DREB1 TFs. Lacks basal activity but achieves high systemic induction precisely at freezing temperatures. ICE1 → CBF1/2/3 → COR15A pathway.",
        "references": ["PMID:8193295"],
        "notes": "Cross-reactivity with drought (DRE element shared). COR15B promoter is stronger due to flanking sequence context."
    },
    # Heat
    {
        "id": "pAtHSP18.2",
        "name": "AtHSP18.2 promoter (full-length)",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "heat stress",
        "description": "Heat Shock Protein 18.2 promoter. Contains Heat Shock Elements (HSEs, nGAAnnTTCn consensus) bound by Heat Shock Factors (HSFs). Exceptionally low basal activity at 22-25C with up to 1000-fold induction within 2 hours of 37-40C heat shock.",
        "references": ["PMID:8597550"],
        "notes": "Premier choice for orthogonal biosensor construction due to minimal leakage and massive dynamic range."
    },
    # Ethylene
    {
        "id": "pSlE4",
        "name": "Tomato E4 promoter",
        "type": "promoter",
        "organism": "Solanum lycopersicum",
        "signal": "ethylene",
        "description": "Ethylene-responsive promoter from tomato. Contains two cooperative cis-elements (-150 to -121 and -40 to +65) required for ethylene response. Minimal responsive elements mapped. ERF TFs bind GCC-box (AGCCGCC).",
        "references": ["PMID:8914528"],
        "notes": "Native ripening promoter — tissue-specific variations in developmental context."
    },
    {
        "id": "pEBSn",
        "name": "Synthetic EBSn promoter",
        "type": "promoter",
        "organism": "Synthetic",
        "signal": "ethylene",
        "description": "Synthetic ethylene-responsive promoter constructed from 10 tandem repeats of the EIN3 Binding Site. Provides uniform, high-amplitude expression independent of developmental and tissue-specific variations in native promoters.",
        "references": [],
        "notes": "Synthetic design eliminates developmental cross-talk seen in native E4/E8 promoters."
    },
    # Auxin
    {
        "id": "pDR5",
        "name": "Synthetic DR5 promoter",
        "type": "promoter",
        "organism": "Synthetic (Arabidopsis/soybean)",
        "signal": "auxin",
        "description": "The most widely used synthetic auxin-responsive promoter. Contains 11-bp tandem repeats of TGTCTC (AuxRE) derived from soybean GH3 promoter. Highly sensitive, dose-dependent, quantitative readout of localized auxin concentrations. TIR1/AFB → Aux/IAA degradation → ARF activation → DR5.",
        "references": ["PMID:9401121", "PMID:8038604"],
        "notes": "Eliminates cross-reactivity present in native GH3 sequences through optimized spacing and serial repetition."
    },
    # Cytokinin
    {
        "id": "pTCSn",
        "name": "Synthetic TCSn promoter (Two-Component Sensor new)",
        "type": "promoter",
        "organism": "Synthetic (Arabidopsis)",
        "signal": "cytokinin",
        "description": "Optimized synthetic cytokinin reporter. Tandemly arrayed type-B ARR binding motifs with precisely 11-bp spacing (one full helical turn of B-form DNA). Vastly superior dynamic range vs original TCS due to steric cooperativity of TFs on same DNA face. AHK receptors → AHP → type-B ARR → TCSn.",
        "references": ["PMID:23537731"],
        "notes": "11-bp motif spacing is critical — corresponds to one helical turn ensuring all TFs bind same face."
    },
    # Light
    {
        "id": "pAtRBCS",
        "name": "AtRBCS promoter (Rubisco small subunit)",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "light",
        "description": "Ribulose-1,5-bisphosphate carboxylase small subunit promoter. Foundational light-responsive part. Contains Light-Responsive Elements (LREs) that act combinatorially; paired LREs confer robust light-inducible expression. phyA/phyB → HY5 (bZIP) → LRE activation.",
        "references": ["PMID:8310058", "PMID:1380166"],
        "notes": "Differential phytochrome regulation. LRE arrays can be engineered for light-activated synthetic biosensors."
    },
    {
        "id": "pAtCAB",
        "name": "AtCAB promoter (Chlorophyll a/b binding protein)",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "light",
        "description": "Light-Harvesting Chlorophyll a/b Binding protein promoter. Strongly light-inducible with independent developmental and phytochrome-mediated induction phases.",
        "references": ["PMID:1380166"],
        "notes": "Foundational light-responsive promoter. Green tissue expression."
    },
    # Pathogen/Defense
    {
        "id": "pAtPR1",
        "name": "AtPR1 promoter (Pathogenesis-Related 1)",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "pathogen (salicylic acid)",
        "description": "Universal marker for SA-mediated Systemic Acquired Resistance. Activated by NPR1 which recruits TGA bZIP TFs and WRKY TFs (especially WRKY50) to W-box (TTGAC) and variant WK box elements. WRKY factors synergize with TGA1a for massive induction.",
        "references": ["PMID:17098858", "PMID:10339596"],
        "notes": "SA pathway. For dual SA+JA biosensors, synthetic dual-responsive promoters combining SA and JA elements have been engineered."
    },
    # Ammonium
    {
        "id": "pAtAMT1.1",
        "name": "AtAMT1;1 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "ammonium / nitrogen deficiency",
        "description": "Ammonium Transporter 1;1 promoter. Strongly upregulated by nitrogen deficiency. Root-specific expression. AMT1;1 protein also acts as direct ammonium sensor via C-terminal T494 phosphorylation (allosteric gating).",
        "references": ["PMID:17565866"],
        "notes": "Reflects systemic N demand, not instantaneous soil NH4+ concentration. Dual regulation: transcriptional induction + post-translational allosteric gating."
    },
    # Sulfur
    {
        "id": "pAtSULTR1.1",
        "name": "AtSULTR1;1 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "sulfur deficiency",
        "description": "Sulfate transporter 1;1 promoter. Regulated by SLIM1/EIL3 TF under S deficiency. Contains the 16-bp SURE (Sulfur-Responsive Element) with core GAGAC motif. SURE is highly specific to sulfur deficiency — repressed by downstream sulfur metabolites (cysteine, glutathione).",
        "references": ["PMID:15047883", "PMID:15842617"],
        "notes": "SURE motif overlaps with AuxRE but exhibits exclusive S-deficiency responsiveness. Excellent for minimal synthetic biosensor parts."
    },
    # Boron
    {
        "id": "pAtNIP5.1",
        "name": "AtNIP5;1 promoter",
        "type": "promoter",
        "organism": "Arabidopsis thaliana",
        "signal": "boron deficiency",
        "description": "Boric acid channel NIP5;1 promoter. Upregulated under B limitation, root elongation zone specific. BOR1 (boron exporter) has a unique post-transcriptional sensor: a uORF (AUGUAA) in the 5'UTR causes ribosome stalling under high B, suppressing translation.",
        "references": ["PMID:19017629"],
        "notes": "BOR1 uORF is an excellent self-contained post-transcriptional boron-toxicity logic gate."
    },

    # ── Category 2: Reporter Systems ──

    {
        "id": "RUBY",
        "name": "RUBY reporter (CYP76AD1-DODA-GT polycistron)",
        "type": "reporter",
        "organism": "Synthetic (Beta vulgaris enzymes)",
        "signal": "visible color",
        "description": "Polycistronic betalain biosynthesis cassette. Three enzymes (CYP76AD1, DODA, GT) linked by self-cleaving 2A peptides in a single ORF. Converts native tyrosine to vivid red/purple betalain pigments. Visible to naked eye, zero background in most plants, quantifiable by spectrophotometry/HPLC.",
        "references": ["PMID:39359623", "PMID:32901306"],
        "notes": "No substrate needed. Works in transient and stable transformations across diverse species (maize, Nicotiana)."
    },
    {
        "id": "dGFP-PEST",
        "name": "Destabilized GFP (PEST-tagged)",
        "type": "reporter",
        "organism": "Synthetic (Aequorea victoria + mouse PEST)",
        "signal": "fluorescence (kinetic)",
        "description": "GFP fused to PEST degradation domain (from mouse ornithine decarboxylase or yeast Cln2). Reduces fluorescence half-life from ~26 hours to under 2 hours. Essential for tracking transient transcriptional bursts rather than cumulative expression.",
        "references": ["PMID:9857028", "PMID:11015728"],
        "notes": "Use for kinetic measurements where wild-type GFP is too stable to resolve temporal dynamics."
    },
    {
        "id": "GREAT",
        "name": "GREAT (Green/Red luciferase ratiometric)",
        "type": "reporter",
        "organism": "Synthetic",
        "signal": "luminescence (ratiometric)",
        "description": "Dual-color luciferase system emitting green and red light from a single substrate. Two distinct luciferases on one transcript separated by 2A peptide. Built-in internal normalization eliminates transformation efficiency variance. High dynamic range.",
        "references": ["PMID:34520169"],
        "notes": "Eliminates need for separate normalization plasmid. Cheap, fast, internally controlled expression measurements."
    },
    {
        "id": "NanoLuc-plant",
        "name": "NanoLuc (GeNL-furimazine system)",
        "type": "reporter",
        "organism": "Synthetic (Oplophorus gracilirostris)",
        "signal": "bioluminescence (deep tissue)",
        "description": "Engineered 19.1 kDa luciferase producing extraordinarily intense bioluminescence. GeNL-furimazine emission spectrum aligns with the optical transparency window of chlorophyll, bypassing autofluorescence limitations that plague standard fluorescent reporters in photosynthetic tissues.",
        "references": [],
        "notes": "Ideal for deep-tissue tracking in roots, thick stems, or dense canopy organs where fluorescence fails."
    },

    # ── Category 3: Terminators & Regulatory Elements ──

    {
        "id": "kozak-KZ3",
        "name": "Optimized Kozak KZ3 sequence",
        "type": "regulatory",
        "organism": "Universal",
        "signal": "N/A",
        "description": "Synthetic optimized Kozak consensus for the 3 nucleotides upstream of AUG start codon. Base-editing the -3 to -1 positions quantitatively scales translation efficiency without altering transcription. Can increase or decrease output bidirectionally.",
        "references": ["PMID:38997252"],
        "notes": "KZ3 region modification provides precise translational tuning independent of promoter strength."
    },
    {
        "id": "IME-UBQ10",
        "name": "UBQ10 first intron (IME element)",
        "type": "regulatory",
        "organism": "Arabidopsis thaliana",
        "signal": "N/A",
        "description": "First intron of Arabidopsis UBQ10 gene. Classic Intron-Mediated Enhancement (IME) element. Placed near TSS, acts at chromatin level (not RNA splicing) to create locally accessible open chromatin. Boosts expression 10-50 fold depending on tissue.",
        "references": ["PMID:26089147"],
        "notes": "IME acts primarily at DNA level via chromatin opening, unlike traditional enhancers that operate via DNA looping."
    },
    {
        "id": "insulator-Ugibba",
        "name": "Utricularia gibba insulator elements",
        "type": "regulatory",
        "organism": "Utricularia gibba",
        "signal": "N/A",
        "description": "Short (<1 kb) plant-derived insulator sequences mined from the compact U. gibba genome. Establish independent chromatin domains, shielding promoters from heterochromatin silencing and ectopic enhancer bleed-through. Robustly block CaMV 35S ectopic interference.",
        "references": [],
        "notes": "Critical for multi-cassette constructs. May possess mild localized silencing effects alongside insulation — calibrate carefully."
    },
]

# ============================================================================
# NEW PATHWAYS — extracted from Gemini Deep Research PDF
# ============================================================================

NEW_PATHWAYS = [
    {
        "signal": "potassium deficiency",
        "organism": "Arabidopsis thaliana",
        "description": "Potassium starvation sensing via HAK/KUP/KT transporters and CBL-CIPK signaling",
        "receptor": "Membrane potential depolarization / ROS generation",
        "transduction_chain": [
            "K+ depletion → membrane hyperpolarization",
            "CBL1/CBL9 Ca2+ sensors activate",
            "CIPK23 kinase phosphorylates target proteins (AKT1, HAK5)",
            "Ethylene signaling via RAP2.11 (AP2/ERF) binds HAK5 promoter cis-elements",
            "HAK5 transcriptional upregulation"
        ],
        "candidate_promoters": ["pAtHAK5"],
        "transcription_factors": ["RAP2.11", "EIN3"],
        "key_references": ["PMID:39362862", "PMID:24716623"],
        "notes": "Cross-talk with nitrogen and phosphorus availability. Root-specific. OsHAK1 and SlHAK5 are crop orthologs."
    },
    {
        "signal": "iron deficiency",
        "organism": "Arabidopsis thaliana",
        "description": "Strategy I iron acquisition via FIT/bHLH TF network and URI master switch",
        "receptor": "URI (Upstream Regulator of IRT1) — bHLH TF, primary iron-dependent molecular switch",
        "transduction_chain": [
            "Fe depletion → URI protein stabilized (normally degraded by BRUTUS/BTS E3 ligase under Fe-replete)",
            "Phosphorylated URI accumulates",
            "URI activates subgroup Ib bHLH factors (bHLH38, bHLH39, bHLH100, bHLH101)",
            "FIT (bHLH029) heterodimerizes with Ib bHLHs",
            "FIT/bHLH complex drives IRT1 and FRO2 expression"
        ],
        "candidate_promoters": ["pAtIRT1", "pAtFRO2"],
        "transcription_factors": ["URI", "FIT (bHLH029)", "bHLH38", "bHLH39", "bHLH100", "bHLH101"],
        "key_references": ["PMID:12084823", "PMID:31636177"],
        "notes": "IRT1 is root epidermis/cortex specific. IRT1 protein also post-translationally regulated by ubiquitin (K146/K171) under Zn/Mn excess."
    },
    {
        "signal": "zinc deficiency",
        "organism": "Arabidopsis thaliana",
        "description": "Zinc homeostasis via direct bZIP19/bZIP23 intracellular zinc sensors",
        "receptor": "bZIP19 and bZIP23 — direct intracellular Zn2+ sensors (no upstream kinase)",
        "transduction_chain": [
            "Cytosolic Zn2+ drops",
            "Zn2+ dissociates from bZIP19/bZIP23 zinc-sensor motif",
            "Conformational shift activates bZIP19/bZIP23 as TFs",
            "Bind 10-bp ZDRE palindrome in ZIP4 promoter (and other ZIP targets)",
            "ZIP transporter family upregulated for Zn uptake"
        ],
        "candidate_promoters": ["pAtZIP4"],
        "transcription_factors": ["bZIP19", "bZIP23"],
        "key_references": ["PMID:20479230", "PMID:33594269"],
        "notes": "Uniquely orthogonal — bZIP19/23 function as direct sensors, no kinase cascade. Isolated ZDRE motifs eliminate Fe/Cu cross-reactivity."
    },
    {
        "signal": "salt stress",
        "organism": "Arabidopsis thaliana",
        "description": "SOS pathway for Na+ exclusion and vacuolar compartmentalization",
        "receptor": "SOS3 (CBL4) — calcium sensor detecting salt-induced Ca2+ spike",
        "transduction_chain": [
            "NaCl exposure → rapid cytosolic Ca2+ spike",
            "SOS3 (CBL4) binds Ca2+",
            "SOS3 recruits and activates SOS2 (CIPK24) kinase",
            "SOS2/SOS3 complex phosphorylates SOS1 (Na+/H+ antiporter)",
            "SOS1 activated → rapid Na+ efflux from cell",
            "Parallel: NHX1 sequesters Na+ into vacuole, HKT1;1 degraded to restrict Na+ entry"
        ],
        "candidate_promoters": ["pAtSOS1", "pAtNHX1", "pOsHKT1;5"],
        "transcription_factors": [],
        "key_references": ["PMID:10831000"],
        "notes": "Regulation intertwined with ABA and osmotic stress pathways. Requires careful promoter truncation for salt-specific response."
    },
    {
        "signal": "cold stress",
        "organism": "Arabidopsis thaliana",
        "description": "ICE-CBF-COR cold acclimation cascade",
        "receptor": "ICE1 (Inducer of CBF Expression) — constitutively expressed, activated by cold",
        "transduction_chain": [
            "Cold shock activates ICE1",
            "ICE1 rapidly upregulates CBF1/DREB1B, CBF2/DREB1C, CBF3/DREB1A",
            "CBF proteins bind CRT/DRE motif (CCGAC) in COR gene promoters",
            "COR15A, COR15B, and other cold-regulated genes induced"
        ],
        "candidate_promoters": ["pAtCOR15A"],
        "transcription_factors": ["ICE1", "CBF1/DREB1B", "CBF2/DREB1C", "CBF3/DREB1A"],
        "key_references": ["PMID:8193295", "PMID:150776"],
        "notes": "CRT/DRE motif shared with drought response (DRE). COR15B promoter is stronger than COR15A due to flanking sequence context."
    },
    {
        "signal": "heat stress",
        "organism": "Arabidopsis thaliana",
        "description": "Heat Shock Factor (HSF) → Heat Shock Element (HSE) response",
        "receptor": "HSFs — activated by protein unfolding / heat-induced conformational changes",
        "transduction_chain": [
            "Temperature increase (37-40C) causes protein unfolding",
            "HSP70/HSP90 release sequestered HSFs",
            "Free HSFs trimerize and bind HSE (nGAAnnTTCn) in HSP promoters",
            "Massive transcriptional upregulation of HSP18.2 and other HSPs"
        ],
        "candidate_promoters": ["pAtHSP18.2"],
        "transcription_factors": ["HSFA1", "HSFA2", "HSFB1"],
        "key_references": ["PMID:8597550"],
        "notes": "HSP18.2 promoter: 1000-fold induction, minimal basal leakage at 22-25C. Premier orthogonal biosensor part."
    },
    {
        "signal": "ethylene",
        "organism": "Arabidopsis thaliana / Solanum lycopersicum",
        "description": "Ethylene de-repression cascade via EIN3/EIL1 and ERF TFs",
        "receptor": "ETR1/ERS1 — ER-membrane ethylene receptors (active in absence of ethylene)",
        "transduction_chain": [
            "Ethylene binds receptors → receptors inactivated",
            "CTR1 kinase deactivated (de-repression)",
            "EIN2 C-terminus cleaved, translocates to nucleus",
            "EIN3 and EIL1 TFs stabilized (normally degraded by 26S proteasome)",
            "EIN3/EIL1 activate AP2/ERF transcription factor genes",
            "ERFs bind GCC-box (AGCCGCC) in target promoters"
        ],
        "candidate_promoters": ["pSlE4", "pEBSn"],
        "transcription_factors": ["EIN3", "EIL1", "ERF1", "AP2/ERF family"],
        "key_references": ["PMID:8914528"],
        "notes": "De-repression model — ethylene removes active repression. Native E4/E8 are ripening-associated; synthetic EBSn avoids developmental context."
    },
    {
        "signal": "auxin",
        "organism": "Arabidopsis thaliana",
        "description": "TIR1/AFB auxin perception and ARF-mediated transcription",
        "receptor": "TIR1/AFB — F-box proteins, auxin co-receptors with Aux/IAA",
        "transduction_chain": [
            "Auxin binds TIR1/AFB-Aux/IAA co-receptor complex",
            "Aux/IAA repressors targeted for 26S proteasomal degradation",
            "Auxin Response Factors (ARFs) freed from Aux/IAA repression",
            "ARFs bind AuxRE (TGTCTC) in target promoters",
            "Transcriptional activation of auxin-responsive genes"
        ],
        "candidate_promoters": ["pDR5"],
        "transcription_factors": ["ARF5/MP", "ARF7", "ARF19"],
        "key_references": ["PMID:9401121", "PMID:8038604"],
        "notes": "DR5 synthetic promoter: 11-bp TGTCTC tandem repeats. Eliminates cross-reactivity of native GH3 promoter."
    },
    {
        "signal": "cytokinin",
        "organism": "Arabidopsis thaliana",
        "description": "Two-component phosphorelay system (AHK → AHP → ARR)",
        "receptor": "AHK2, AHK3, AHK4/CRE1 — Histidine Kinase receptors",
        "transduction_chain": [
            "Cytokinin binds AHK receptor CHASE domain",
            "AHK autophosphorylates (His residue)",
            "Phosphoryl transfer to Histidine Phosphotransfer proteins (AHPs)",
            "AHPs shuttle to nucleus, phosphorylate type-B ARRs",
            "Type-B ARRs activate target gene transcription"
        ],
        "candidate_promoters": ["pTCSn"],
        "transcription_factors": ["ARR1", "ARR2", "ARR10", "ARR12"],
        "key_references": ["PMID:23537731", "PMID:1851144"],
        "notes": "TCSn: 11-bp spacing of type-B ARR motifs = one helical turn of B-form DNA, ensuring cooperative TF binding on same DNA face."
    },
    {
        "signal": "light",
        "organism": "Arabidopsis thaliana",
        "description": "Phytochrome-mediated light signaling via HY5",
        "receptor": "phyA, phyB — phytochrome photoreceptors (red/far-red)",
        "transduction_chain": [
            "Light activates phyA/phyB (Pr → Pfr conformational switch)",
            "Active phytochromes translocate to nucleus",
            "Phytochromes trigger degradation of PIF (Phytochrome Interacting Factor) repressors",
            "HY5 (bZIP TF) accumulates (normally COP1-degraded in dark)",
            "HY5 activates Light-Responsive Elements (LREs) in CAB, RBCS promoters"
        ],
        "candidate_promoters": ["pAtRBCS", "pAtCAB"],
        "transcription_factors": ["HY5", "PIF1", "PIF3", "PIF4", "PIF5"],
        "key_references": ["PMID:8310058", "PMID:1380166"],
        "notes": "LREs act combinatorially — paired LREs required for robust induction. Temporal light quality dependence (red vs far-red)."
    },
    {
        "signal": "pathogen defense (salicylic acid)",
        "organism": "Arabidopsis thaliana",
        "description": "SA-mediated Systemic Acquired Resistance via NPR1/TGA/WRKY",
        "receptor": "NPR1 — SA receptor and transcriptional coactivator",
        "transduction_chain": [
            "Pathogen infection → SA accumulation",
            "SA binds NPR1, induces monomerization",
            "NPR1 monomers translocate to nucleus",
            "NPR1 recruits TGA bZIP TFs to as-1-like elements",
            "WRKY TFs (WRKY50, WRKY11/17) bind W-box (TTGAC) and WK box (TTTTCCAC)",
            "Synergistic activation of PR1 and other defense genes"
        ],
        "candidate_promoters": ["pAtPR1"],
        "transcription_factors": ["NPR1", "TGA1", "TGA2", "WRKY50", "WRKY11", "WRKY17"],
        "key_references": ["PMID:17098858", "PMID:10339596"],
        "notes": "For dual SA+JA biosensors, synthetic promoters combining both responsive elements have been engineered to circumvent natural antagonism."
    },
    {
        "signal": "sulfur deficiency",
        "organism": "Arabidopsis thaliana",
        "description": "SLIM1/EIL3 regulation of sulfate transporters via SURE element",
        "receptor": "SLIM1 (SULFUR LIMITATION1, also EIL3) — S-status sensor TF",
        "transduction_chain": [
            "Sulfur depletion sensed (mechanism upstream of SLIM1 unclear)",
            "SLIM1/EIL3 activated",
            "SLIM1 drives SULTR expression",
            "SULTR1;1 promoter contains 16-bp SURE element (core: GAGAC)",
            "SURE element specifically responsive to S deficiency, repressed by Cys/GSH"
        ],
        "candidate_promoters": ["pAtSULTR1.1"],
        "transcription_factors": ["SLIM1/EIL3"],
        "key_references": ["PMID:15047883", "PMID:15842617"],
        "notes": "SURE motif overlaps with AuxRE but maintains exclusive S-deficiency specificity. Ideal minimal element for synthetic biosensors."
    },
    {
        "signal": "ammonium",
        "organism": "Arabidopsis thaliana",
        "description": "AMT1 transcriptional induction and allosteric regulation",
        "receptor": "AMT1;1 protein itself — dual function as transporter and sensor (T494 phosphorylation)",
        "transduction_chain": [
            "Nitrogen deficiency → AMT1;1 transcriptionally upregulated",
            "Under NH4+ excess: T494 phosphorylation on AMT1;1 C-terminus",
            "Phospho-T494 causes homotrimeric pore closure (allosteric gating)",
            "Prevents ammonium toxicity"
        ],
        "candidate_promoters": ["pAtAMT1.1"],
        "transcription_factors": [],
        "key_references": ["PMID:17565866"],
        "notes": "AMT1;1 promoter reflects systemic N demand, not instantaneous NH4+. Root-specific."
    },
]


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("BioSensor-Architect — Batch Parts Ingestion")
    print("Source: Gemini Deep Research PDF")
    print("=" * 60)

    # Load existing data
    existing_parts = load_catalog()
    existing_pathways = load_pathways()
    print(f"\nExisting catalog: {len(existing_parts)} parts, {len(existing_pathways)} pathways")

    # Deduplicate
    unique_parts = deduplicate_parts(NEW_PARTS, existing_parts)
    unique_pathways = deduplicate_pathways(NEW_PATHWAYS, existing_pathways)

    print(f"\nNew parts to add: {len(unique_parts)} (of {len(NEW_PARTS)} total, {len(NEW_PARTS) - len(unique_parts)} duplicates skipped)")
    print(f"New pathways to add: {len(unique_pathways)} (of {len(NEW_PATHWAYS)} total, {len(NEW_PATHWAYS) - len(unique_pathways)} duplicates skipped)")

    if unique_parts:
        print("\n── New Parts ──")
        for p in unique_parts:
            print(f"  [{p['type']:10s}] {p['id']:20s} — {p.get('signal', 'N/A'):25s} ({p['organism']})")

    if unique_pathways:
        print("\n── New Pathways ──")
        for pw in unique_pathways:
            print(f"  {pw['signal']:30s} in {pw['organism']}")

    if dry_run:
        print("\n[DRY RUN] No changes written.")
        return

    if not unique_parts and not unique_pathways:
        print("\nNothing new to add.")
        return

    # Append
    n_parts = append_to_catalog(unique_parts)
    n_pathways = append_to_pathways(unique_pathways)

    print(f"\n✓ Added {n_parts} parts and {n_pathways} pathways to the database.")
    print(f"  Parts catalog: {PARTS_FILE}")
    print(f"  Pathways DB:   {PATHWAYS_FILE}")

    # Final counts
    final_parts = load_catalog()
    final_pathways = load_pathways()
    print(f"\n  Total parts now: {len(final_parts)}")
    print(f"  Total pathways now: {len(final_pathways)}")


if __name__ == "__main__":
    main()
