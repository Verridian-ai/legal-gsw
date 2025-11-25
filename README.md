<p align="center">
  <img src="docs/assets/rag_vs_gsw.png" alt="Legal GSW - Smarter AI" width="100%">
</p>

<h1 align="center">Legal GSW</h1>

<p align="center">
  <strong>Global Semantic Workspace for Legal Document Intelligence</strong>
</p>

<p align="center">
  <em>Actor-Centric Episodic Memory for the Australian Legal Corpus</em>
</p>

<p align="center">
  <a href="#features"><img src="https://img.shields.io/badge/Features-Actor--Centric%20Memory-blue?style=for-the-badge" alt="Features"></a>
  <a href="#architecture"><img src="https://img.shields.io/badge/Architecture-GSW%20Model-green?style=for-the-badge" alt="Architecture"></a>
  <a href="https://arxiv.org/abs/2511.07587"><img src="https://img.shields.io/badge/arXiv-2511.07587-b31b1b?style=for-the-badge" alt="arXiv"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome">
  <img src="https://img.shields.io/badge/corpus-232K%20docs-orange.svg" alt="Corpus Size">
</p>

---

## Video Overview

<p align="center">
  <a href="docs/assets/how_ai_learns.mp4">
    <img src="docs/assets/gsw_episodic_memory.png" alt="How AI Learns to Remember - Click to Watch" width="80%">
  </a>
</p>

<p align="center">
  <em>Click image above to watch: How AI Learns to Remember</em>
</p>

---

## The Problem: Why Standard AI Fails Complex Analysis

<p align="center">
  <img src="docs/assets/beyond_search.png" alt="Beyond Search: Building a True Legal Reasoning Engine" width="100%">
</p>

**Legal GSW** implements the **Global Semantic Workspace (GSW)** model for legal document understanding, based on the research paper [*"Functional Structure of Episodic Memory"*](https://arxiv.org/abs/2511.07587).

The system extracts **actor-centric episodic memories** from legal documents - tracking WHO did WHAT, WHEN, WHERE, and WHY - enabling sophisticated legal reasoning and analysis.

---

## How GSW Works

<p align="center">
  <img src="docs/assets/gsw_episodic_memory.png" alt="GSW: Giving Language Models a Human-like Episodic Memory" width="100%">
</p>

### Why Actor-Centric?

Traditional NLP approaches focus on **verb-centric** representations (Subject-Verb-Object triples). GSW takes a fundamentally different approach:

| Approach | Focus | Example |
|----------|-------|---------|
| **Verb-Centric** | Actions | `(John, married, Jane)` |
| **Actor-Centric (GSW)** | Entities + States + Roles | `John: {roles: [husband, applicant], states: [married->separated], linked: [Jane, Property, Children]}` |

The actor-centric model mirrors how human memory works - we remember **people and their characteristics** across time, not isolated actions.

<p align="center">
  <img src="docs/assets/motivation.png" alt="GSW Motivation" width="80%">
</p>

---

## Key Features

<table>
<tr>
<td width="50%">

### 6-Task Operator Extraction
- **Actor Identification** - WHO is involved?
- **Role Assignment** - What roles do they play?
- **State Identification** - What are their conditions?
- **Verb Phrase Extraction** - What happened?
- **Question Generation** - What should we ask?
- **Answer Mapping** - What do we know?

</td>
<td width="50%">

### Advanced Capabilities
- **Spatio-Temporal Linking** - Bind entities by time/place
- **Entity Reconciliation** - "the husband" = "John Smith"
- **Predictive Questions** - Self-improving memory
- **TOON Compression** - 70% token reduction
- **Multi-Domain Support** - 14 legal domains
- **Reflexion Loop** - Continuous learning

</td>
</tr>
</table>

---

## Architecture

<p align="center">
  <img src="docs/assets/operatorv2.png" alt="GSW Operator Architecture" width="80%">
</p>

### Pipeline Components

```
                    +------------------+
                    |   Legal Corpus   |
                    |   (232K docs)    |
                    +--------+---------+
                             |
                             v
+-----------------------------------------------------------+
|                    DOMAIN CLASSIFIER                       |
|  Administrative | Family | Criminal | Commercial | ...     |
+----------------------------+------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|                     GSW OPERATOR                           |
|  +--------+  +------+  +-------+  +------+  +----------+  |
|  | Actors |->| Roles|->| States|->| Verbs|->| Questions|  |
|  +--------+  +------+  +-------+  +------+  +----------+  |
+----------------------------+------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|                  SPACETIME LINKER                          |
|           Temporal Bindings | Spatial Bindings             |
+----------------------------+------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|                     RECONCILER                             |
|        Entity Merging | Question Answering | Dedup         |
+----------------------------+------------------------------+
                             |
                             v
                    +--------+---------+
                    | Global Workspace |
                    |  (Actor Memory)  |
                    +------------------+
```

---

## Performance Comparison

### GSW vs Other RAG Methods (EpBench-200)

| Method | Overall F1-Score | Avg. Context Tokens |
|--------|------------------|---------------------|
| Embedding RAG | 0.771 | ~8,771 |
| HippoRAG2 | 0.753 | ~8,771 |
| GraphRAG | 0.714 | ~7,340 |
| **GSW (Ours)** | **0.850** | **~3,587** |

**Key Results:**
- **+10% accuracy** over best competitor
- **-51% token usage** vs standard RAG
- **+20% recall** on complex reasoning queries

### Token Compression (TOON)

| Format | Tokens | Reduction |
|--------|--------|-----------|
| JSON | 575 | - |
| TOON | 167 | **71%** |

---

## Installation

### Prerequisites

- Python 3.10+
- OpenRouter API key (for LLM access)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/Verridian-ai/legal-gsw.git
cd legal-gsw

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENROUTER_API_KEY="your-api-key-here"
```

---

## Quick Start

### 1. Basic Extraction

```python
from src.gsw.legal_operator import LegalOperator
from src.logic.gsw_schema import GlobalWorkspace

# Initialize operator
operator = LegalOperator(
    model="google/gemini-2.0-flash-001",
    api_key="your-api-key"
)

# Extract from legal text
text = """
The parties married on 10 June 2010 in Sydney. They separated on
1 March 2020 at the matrimonial home located at 123 Smith Street,
Parramatta. The husband is employed as an accountant earning $150,000
per annum. The wife is the primary carer of the two children.
"""

extraction = operator.extract(text, chunk_id="chunk_001")

# View extracted actors
for actor in extraction.actors:
    print(f"{actor.name}: {actor.roles}")
```

### 2. Full Pipeline

```python
from src.gsw.legal_operator import LegalOperator
from src.gsw.legal_spacetime import LegalSpacetime
from src.gsw.legal_reconciler import LegalReconciler
from src.logic.gsw_schema import GlobalWorkspace

# Initialize components
operator = LegalOperator(api_key="your-key")
spacetime = LegalSpacetime(api_key="your-key")
reconciler = LegalReconciler(api_key="your-key")

# Create workspace
workspace = GlobalWorkspace(domain="family")

# Process document
extraction = operator.extract(document_text, chunk_id="doc_001")
links = spacetime.link_entities(extraction, document_text)
extraction.spatio_temporal_links = links
extraction, log = reconciler.reconcile(extraction, workspace, document_text)

# Export to TOON format (70% token reduction)
toon_output = workspace.to_toon()
print(toon_output)
```

### 3. TOON Format Example

```
# GSW Workspace: family

Actors[5]{id,name,type,roles,states}
a1,John Smith,person,husband|applicant,marital_status=separated
a2,Jane Smith,person,wife|respondent,marital_status=separated
a3,Family Court,organization,court,
a4,15 March 2020,temporal,,
a5,123 Smith St,location,matrimonial_home,

VerbPhrases[2]{id,verb,agent,patients,temporal,spatial,implicit}
v1,married,a1,a2,,,0
v2,separated,a1,a2,a4,a5,0

Questions[2]{id,about,question,answered,answer}
q1,a1,What is John Smith's occupation?,1,accountant
q2,a5,What is the property value?,0,
```

---

## Supported Legal Domains

| Domain | Documents | Priority | Status |
|--------|-----------|----------|--------|
| Administrative | 58,726+ | High | Active |
| Legislation | 7,840+ | Medium | Active |
| Commercial | 1,842+ | Medium | Active |
| Criminal | 1,541+ | High | Active |
| Family | 200+ | **Highest** | **Active** |
| Property | 310+ | Medium | Planned |
| Tax | 168+ | Medium | Planned |
| Industrial | 553+ | Low | Planned |
| Procedural | 980+ | Low | Planned |

---

## Project Structure

```
legal-gsw/
├── src/
│   ├── gsw/                    # Core GSW components
│   │   ├── legal_operator.py   # 6-task extraction operator
│   │   ├── legal_spacetime.py  # Spatio-temporal linking
│   │   ├── legal_reconciler.py # Entity reconciliation
│   │   └── legal_summary.py    # Entity summarization
│   ├── logic/                  # Data models & ontology
│   │   ├── gsw_schema.py       # Pydantic models
│   │   └── ontology_seed.py    # Domain ontologies
│   ├── ingestion/              # Corpus processing
│   │   └── corpus_domain_extractor.py
│   ├── analysis/               # Reports & analytics
│   └── utils/                  # Utilities
│       └── toon.py             # TOON encoder/decoder
├── papers/                     # Research papers & figures
├── data/
│   └── processed/
│       └── workspaces/         # Extracted workspaces
├── examples/                   # Sample outputs
├── docs/                       # Documentation
└── tests/                      # Test suite
```

---

## Research Foundation

This implementation is based on:

> **"Functional Structure of Episodic Memory"**
> arXiv:2511.07587
>
> The paper proposes that episodic memory has a functional structure centered on **actors** (entities) rather than events. The GSW model implements this insight through:
>
> 1. **Actor-Centric Representation** - Entities as memory anchors
> 2. **State Tracking** - How actors change over time
> 3. **Spatio-Temporal Binding** - Linking actors by context
> 4. **Predictive Questions** - Self-improving knowledge

### Key Insight

> *"Traditional verb-centric approaches lose context when actions span multiple documents. Actor-centric memory maintains coherent entity timelines, enabling sophisticated reasoning about long-term relationships and changes."*

---

## Roadmap

- [x] Phase 1: Core GSW extraction pipeline
- [x] Phase 2: Spatio-temporal linking
- [x] Phase 3: Entity reconciliation
- [x] Phase 4: TOON compression
- [ ] Phase 5: Vector-based similarity matching
- [ ] Phase 6: Reflexion loop for self-improvement
- [ ] Phase 7: Query interface for legal Q&A
- [ ] Phase 8: Multi-document reasoning

---

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Research paper: [arXiv:2511.07587](https://arxiv.org/abs/2511.07587)
- Australian Legal Corpus providers
- OpenRouter for LLM API access
- The Pydantic and httpx maintainers

---

<p align="center">
  <strong>Built with cognitive science principles for legal AI</strong>
</p>

<p align="center">
  <a href="https://arxiv.org/abs/2511.07587">Paper</a> |
  <a href="#quick-start">Quick Start</a> |
  <a href="#architecture">Architecture</a> |
  <a href="https://github.com/Verridian-ai/legal-gsw/issues">Issues</a>
</p>
