# GSW PROJECT ROADMAP: Australian Family Law AI

## 1. Project Vision
**Goal**: Construct a comprehensive, self-evolving Knowledge Graph of Australian Family Law from raw legal texts (judgments, legislation).
**Philosophy**: "Logic First, Compute Second." We prioritize building a consistent internal "Mental Model" (The Dictionary) over blindly ingesting terabytes of text.

---

## 2. The "Self-Improving" Architecture

Our system is designed to get smarter with every batch of data it processes. It uses a **Neuro-Symbolic Feedback Loop**:

1.  **The Operator (Extraction)**:
    *   Uses **Gemini 2.0 Flash** to read legal text.
    *   **Reflexion Step**: The model immediately critiques its own output (e.g., "Did I miss the property value? Is 'Order' too vague?") and corrects it *before* saving.
    *   **Ontology Injection**: The Operator receives the current "Dictionary" (see below) in its system prompt, ensuring it uses established terms (e.g., "Final Parenting Order" instead of just "Order").

2.  **The Reconciler (Memory)**:
    *   Merges new entities with the **Global Graph** using Vector Search (BGE-M3).
    *   Resolves duplicates (e.g., "Mr. Smith" == "John Smith").
    *   **The Dictionary**: Continuously calculates the most common terms (Assets, Outcomes, Events) to form the "Known Ontology".

3.  **The Analyst (Auditing)**:
    *   Generates `LEGAL_LANDSCAPE_REPORT.md` after every batch.
    *   This report serves as our **Ontology Definition**, allowing us to track the convergence of vocabulary.

---

## 3. Workflow Protocols

### A. Calibration Mode (The Sandbox)
**Command**: `python main.py --calibration`
*   **Purpose**: To refine the extraction logic or prompt prompts without corrupting the master database.
*   **Behavior**:
    *   Loads existing graph.
    *   Processes a batch of cases.
    *   Generates a Report.
    *   **DISCARDS** the changes (State is not saved).
*   **Use Case**: "I want to see if the AI captures 'Superannuation' better if I tweak the prompt."

### B. Production Mode (The Build)
**Command**: `python main.py`
*   **Purpose**: To ingest data and grow the Knowledge Base.
*   **Behavior**:
    *   Loads existing graph.
    *   Processes the *next* batch of cases (tracked via `ingestion_state.json`).
    *   **SAVES** the updated graph to `graph_snapshot.json`.
*   **Use Case**: "The logic is good. Let's process the next 50 cases."

---

## 4. Strategic Roadmap

### ✅ Phase 1-3: Foundation (Completed)
- [x] Vector Store & Entity Linking (BGE-M3).
- [x] Pydantic Schema Definition (Persons, Assets, Timeline).
- [x] Basic Ingestion Pipeline.
- [x] Persistence (Save/Load Graph).

### 🔄 Phase 4: The "Self-Improving" Loop (Active)
- [x] **Reflexion**: Operator self-corrects extraction errors.
- [x] **Dynamic Ontology**: Reconciler feeds "Standard Terms" back to Operator.
- [x] **The Dictionary Report**: Automated auditing of vocabulary.
- [ ] **Convergence Goal**: Run batches until the Vocabulary lists in the Report stabilize (fewer synonyms, high specificity).

### 🔮 Phase 5: Logic & Consistency (Upcoming)
- [ ] **Rule Engine**: Implement Prolog or Python logic to validate graph consistency.
    -   *Example*: "Event 'Divorce' cannot occur before 'Marriage'."
- [ ] **Conflict Resolution**: When two cases assert different facts about the same entity, use timestamp weighting to resolve.

### 🚀 Phase 6: Scale & Interface (Future)
- [ ] **Full Corpus Run**: Process the entire 9.2GB dataset.
- [ ] **Query Engine**: Natural Language Interface for lawyers.
    -   *Query*: "Show me the timeline of assets for the 'Smith' family."
    -   *Query*: "What is the average duration of 'Property Settlement' proceedings?"

---

**Maintained by**: GSW Architect Agent
**Last Updated**: Phase 4.5
