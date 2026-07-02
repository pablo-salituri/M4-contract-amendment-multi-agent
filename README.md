# Contract Amendment Multi-Agent System

**LegalMove** is a legal-tech company that processes thousands of contract amendments every month. Today, the Compliance team spends more than 40 hours per week manually comparing original contracts with their addenda to identify what changed, assess legal impact, and route documents for review. This system automates that workflow: it accepts scanned images of both documents, extracts text with multimodal vision, coordinates two specialized agents to pinpoint legal changes, and returns a strictly validated JSON report with full step-by-step traceability in Langfuse for production-grade auditing.

---



## General architecture


| Component               | Location                                | Role                                                                  |
| ----------------------- | --------------------------------------- | --------------------------------------------------------------------- |
| Entry point             | `src/main.py`                           | CLI: health check + pipeline execution                                |
| Pipeline                | `src/pipeline.py`                       | Stage orchestration, error handling, Langfuse instrumentation         |
| Image parser            | `src/image_parser.py`                   | `parse_contract_image()` — validation, Base64 encoding, GPT-4o Vision |
| Contextualization agent | `src/agents/contextualization_agent.py` | Structural alignment map between both contracts                       |
| Extraction agent        | `src/agents/extraction_agent.py`        | Change detection + `ContractChangeOutput`                             |
| Pydantic model          | `src/models.py`                         | `ContractChangeOutput` schema validation                              |
| Configuration           | `src/config.py`                         | Environment variables, per-stage settings, client factories           |
| Prompts                 | `src/prompts.py`                        | System and user prompts for both agents                               |
| Token tracking          | `src/model_usage.py`                    | Normalizes usage metadata for Langfuse spans                          |
| Health check            | `src/health_check.py`                   | Pre-flight validation of `.env` and Langfuse connectivity             |
| Input validation        | `src/input_validation.py`               | Early validation of image paths                                       |
| Test images             | `data/test_contracts/`                  | 3 contract pairs (6 images)                                           |
| Observability           | Langfuse (`contract-analysis` trace)    | Hierarchical generations with inputs, outputs, tokens, latency        |


---



## Execution flow

Linear pipeline — no branches, no automatic retries. Each stage runs exactly once; a failure stops execution immediately.

```text
        Original image
              |
              v
   parse_original_contract (GPT-4o Vision)
              |
              v
        Original text
              |                  
              v                  
        Amendment image          
              |                  
              v                  
   parse_amendment_contract      
        (GPT-4o Vision)          
              |                  
              v                  
        Amendment text 
              |
              v
   contextualization_agent
              |
              v
         Context map
              |
              v
      extraction_agent
              |
              v
   ContractChangeOutput (JSON)
```

1. **Health check** — Validates `.env`, API credentials, and Langfuse connectivity.
2. `parse_original_contract` — Transcribes the original contract image via GPT-4o Vision.
3. `parse_amendment_contract` — Transcribes the amendment image.
4. `contextualization_agent` — Builds a structural alignment map between both texts (sections, correspondences, reorganizations). Does **not** extract changes.
5. `extraction_agent` — Uses the context map plus both full texts to identify confirmed additions, modifications, and deletions. Returns Pydantic-validated JSON.



### Why two agents


| Agent                      | Responsibility                                 | Does not                             |
| -------------------------- | ---------------------------------------------- | ------------------------------------ |
| **ContextualizationAgent** | Section structure and cross-document alignment | Extract or summarize content changes |
| **ExtractionAgent**        | Confirmed legal changes → structured output    | Rebuild full document structure      |


Splitting structure analysis from change extraction reduces cognitive load per LLM call, improves accuracy on long documents, and allows independent observability of each phase in Langfuse.

### Output schema (`ContractChangeOutput`)


| Field                   | Type        | Description                                                                                      |
| ----------------------- | ----------- | ------------------------------------------------------------------------------------------------ |
| `sections_changed`      | `list[str]` | Semantic `snake_case` keys for affected topics (e.g. `duracion`, `canon_mensual`)                |
| `topics_touched`        | `list[str]` | Lowercase Spanish descriptive phrases (e.g. `duracion contractual`, `canon mensual de locacion`) |
| `summary_of_the_change` | `str`       | Concise Spanish summary of confirmed changes, with old/new values when visible                   |


Validated via LangChain `with_structured_output(ContractChangeOutput)` and Pydantic `model_validate()`.

---



## Installation

Use **Python 3.10+** and run all commands from the **repository root**.

### Clone the repository

Clone the `main` branch:

```bash
git clone -b main https://github.com/pablo-salituri/M4-contract-amendment-multi-agent.git
cd M4-contract-amendment-multi-agent
```



### Create a virtual environment

```bash
python -m venv .venv
```



### Activate the environment

```bash
source .venv/Scripts/activate
```



### Install dependencies

```bash
pip install -r requirements.txt
```

---



## `.env` configuration

Edit .env with your credentials:

```env
OPENAI_API_KEY=your-key-here
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```


| Variable                                      | Usage                                                   |
| --------------------------------------------- | ------------------------------------------------------- |
| `OPENAI_API_KEY`                              | GPT-4o Vision parsing + both text agents                |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Trace ingestion                                         |
| `LANGFUSE_HOST`                               | Langfuse server URL (e.g. `https://cloud.langfuse.com`) |


---



## Running the application



### Health check (no images required)

Validates environment setup and Langfuse authentication:

```bash
python -m src.main
```

Expected: all 5 checks pass with a success message.

### Full pipeline — simple case (recommended first demo)

Service contract with a single clause change (amount and due date):

```bash
python -m src.main data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg
```



### Full pipeline — complex case (recommended for live defense)

NDA with multiple changes: new clause, territorial scope modification, and removed restriction:

```bash
python -m src.main data/test_contracts/documento_2__original.jpg data/test_contracts/documento_2__enmienda.jpg
```



### Example output

```json
{
  "sections_changed": ["duracion", "canon_mensual"],
  "topics_touched": ["duracion contractual", "canon mensual de locacion"],
  "summary_of_the_change": "La duracion se extiende de 12 a 18 meses. El canon mensual pasa de $50.000 a $65.000."
}
```



## Supported image formats: `.jpg`, `.jpeg`, `.png`.



## Langfuse observability

Every pipeline run creates a root trace `contract-analysis` with four child **generations** (one per LLM stage):

```text
contract-analysis
├── parse_original_contract
├── parse_amendment_contract
├── contextualization_agent
└── extraction_agent
```

Each generation records:

- **Inputs** — image paths or text lengths (not full contract text)
- **Outputs** — truncated previews or final JSON
- **Metadata** — model, temperature, pipeline version, stage name
- **Usage** — token consumption per stage
- **Errors** — stage-level failures with typed error messages

After running the pipeline:

1. Open your project in [Langfuse Cloud](https://cloud.langfuse.com).
2. Find the latest `contract-analysis` trace.
3. Inspect each generation: inputs, outputs, latency, and token metrics.

Full contract text is **never** sent to Langfuse — only truncated previews for privacy.

---



## Known limitations

- **Vision quality:** transcription accuracy depends on image resolution and legibility; low-quality scans may degrade downstream analysis.
- **API cost:** each run makes 4 LLM calls (2 vision + 2 text agents).
- **Spanish output:** `topics_touched` and `summary_of_the_change` are produced in Spanish to match the contract language.
- **No automatic retries:** API failures (rate limits, timeouts) stop the pipeline immediately with a typed error per stage.

---



## Technical decisions



### Why GPT-4o Vision

The assignment requires multimodal parsing of scanned contract images. GPT-4o Vision transcribes documents faithfully via the OpenAI SDK (`client.chat.completions.create`) with Base64-encoded images. The vision prompt instructs verbatim transcription preserving section hierarchy — no summarization or interpretation at this stage.

### Why LangChain

LangChain provides `ChatOpenAI` for both text agents and `with_structured_output(ContractChangeOutput)` on the extraction agent, enforcing the Pydantic schema at generation time. This aligns with the rubric requirement for structured, production-ready JSON output.

### Why Pydantic

`ContractChangeOutput` defines the three required fields (`sections_changed`, `topics_touched`, `summary_of_the_change`) with typed validation. The pipeline guarantees schema compliance before returning results to the caller.

### Why two agents instead of one

Structure alignment and change extraction are distinct cognitive tasks. A single monolithic agent would conflate section mapping with diff detection, increasing hallucination risk on long legal documents. The handoff — context map from Agent 1 to Agent 2 — is explicit and observable.

### Why Langfuse

Langfuse instruments the full workflow with a parent trace and per-stage generations. Token usage, latency, and metadata are recorded for each step, satisfying the rubric's traceability requirement and supporting live defense demonstrations.

### Robustness choices

- Temperature `0` by default across all stages for deterministic output.
- Reusable clients per run (`create_pipeline_clients`) — one OpenAI, one Langfuse, two agents.
- Per-stage settings (`VisionSettings`, `ContextualizationSettings`, `ExtractionSettings`) configurable via environment variables.
- Prompt injection protection: contract text is treated as data, not instructions.
- Anti-inference rules: the extraction agent reports only changes explicitly evidenced in the documents.

---



## Repository structure

```text
├── data/
│   └── test_contracts/            # Test image pairs + README
├── src/
│   ├── main.py                    # CLI entry point
│   ├── pipeline.py                # Orchestration + Langfuse
│   ├── image_parser.py            # Multimodal parsing
│   ├── model_usage.py             # Token normalization for traces
│   ├── models.py                  # ContractChangeOutput
│   ├── config.py                  # Settings and client factories
│   ├── prompts.py                 # Agent prompts
│   ├── health_check.py            # Environment validation
│   ├── input_validation.py        # Image path validation
│   ├── console_ui.py              # Rich terminal output
│   └── agents/
│       ├── contextualization_agent.py
│       └── extraction_agent.py
├── .env.example
├── requirements.txt
└── README.md
```

