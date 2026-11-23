# Chapter 2 — Exploring Design Patterns for AI Agents

Six notebooks, one per design pattern: tool use, working memory, episodic
memory, ReAct, evaluator-optimizer, and a sequential (prompt-chaining)
workflow — all applied to the same kind of finance material.

## The six labs in sequence — what they build, and why in this order

The twelve pattern chapters of the book revisit the same cheat sheet of agent
design patterns, so these six labs are not random samples: they are a **ladder
of increasing complexity**, and they reuse each other. Read in order 1 → 6:

The logic: **one agent → one agent that remembers → memory that persists
across sessions → transparent reasoning → two agents that refine each other →
N agents in a contract-bound chain.** Labs 2 and 3 share the same conversation
by design; the later labs add structure (feedback loops, deterministic stages)
rather than new data sources.

### Step 1 — Lab 1: Apple fundamentals (Tool use)

- **Pattern:** tool use / function calling — the foundation everything else sits on.
- **What it does:** one OpenAI Agents SDK agent (`gpt-4o-mini`) is handed a single tool, `get_company_fundamentals(ticker)`, built on Finance Toolkit / Financial Modeling Prep. Asked for Apple's liquidity ratios, the agent *decides* to call the tool and returns live numbers (profitability, valuation, liquidity) instead of guessing.
- **Sub-topic — the knowledge-cutoff effect:**
  - Run 1 (no year given): the model treats 2023 as "the most recent fiscal year" because of its training cutoff (2024).
  - Run 2 (prompt says "we are in 2026"): it correctly asks for, and gets, **2025** data.
  - Lesson: tools supply facts the model could never know; but the model still needs context (the current year) to frame *which* facts to request.
- **What it adds on the ladder:** the primitive that all six labs reuse — how an LLM gets live external data. Lab 6 reuses this exact FMP tool.
- **Bridge to Lab 2:** a single tool call has no memory; the next step is making the agent *remember* the conversation around those calls.

### Step 2 — Lab 2: Portfolio rebalancing (Working memory)

- **Pattern:** working memory — context *within* one conversation.
- **What it does:** the same rebalancing agent but now carried across **six turns** via one `SQLiteSession("conversation_ptf")`:
  - Each `Runner.run(..., session=...)` appends the user prompt and the agent reply as rows in SQLite (`agent_messages`, `message_data` JSON blobs keyed by `session_id`).
  - `get_items()` replays them in id order, so after each query the notebook prints the growing memory (2 → 4 → 6 → … → 12 items).
  - The simulated conversation moves allocations 70/20/10 → 50/35/15 → 45/40/15 → 55/30/15 → 70/25/05; the agent consistently reasons from the *latest* allocation because it "remembers" prior turns.
- **Key insight:** working memory is append-only within a session; pass a **new** session and it starts empty. It dies when the session/kernel ends.
- **What it adds:** memory as a first-class agent feature — but only *during* a conversation.
- **Bridge to Lab 3:** a multi-turn conversation is raw fuel. Condensing it into a reusable lesson is exactly what episodic memory (next step) does — that is why Lab 3 reuses Lab 2's agent and conversation verbatim.

### Step 3 — Lab 3: Portfolio rebalancing (Episodic memory)

- **Pattern:** episodic memory — long-term memory that survives *across* sessions (“I've seen this situation before”).
- **What it does:** takes **Lab 2's exact conversation** and turns it into a **structured episode** (JSON: `conversation_summary`, `portfolio_allocation_trajectory`, `what_worked`, `what_didnt_work`, `key_points`), produced **two interchangeable ways** — a LangChain chain (`ChatPromptTemplate` + `ChatOpenAI` + `JsonOutputParser`) and the OpenAI **Responses API**.
- **Storing it:**
  - The episode becomes a `document_text` embedded with `text-embedding-3-small`.
  - Stored in ChromaDB (`PersistentClient(path="./chroma_ptf_rebal")`, collection `episodic_memory_ptf_rebal`).
- **Using it:**
  - A brand-new query is embedded and matched with `collection.query(..., n_results=3)` → similar past episodes.
  - Injected into a **fresh** session (`conversation_ptf_2`) with no working memory — and the agent still recalls the last allocation from the past episode. That is the whole point: **cross-session recall**.
- **Ending:** "All in" wraps it as functions and adds an interactive loop (each `User:` prompt is augmented with similar episodes; typing `exit` summarizes the session and writes episode id `memory_2`).
- **What it adds:** memory is now *written to disk, embedded, retrievable, and reusable* — the working memory of Lab 2 feeds it like episodic memory in humans is formed from lived working-memory experiences.
- **Bridge to Lab 4:** Labs 1–3 all use the OpenAI Agents SDK. Lab 4 switches framework (LlamaIndex) and makes the underlying reasoning visible — same memory concepts, transparent mechanics.

### Step 4 — Lab 4: Stock price (ReAct, LlamaIndex)

- **Pattern:** ReAct = Reasoning + Acting — the model loops Thought → Action → Observation before answering; thinking step-by-step around tool calls.
- **What it does (different framework):** LlamaIndex's workflow `ReActAgent` (`gpt-4o`) with a `get_latest_price` tool over **Yahoo Finance** (no API key needed):
  - Run 1: "What is the last price of Apple?" → returns ticker + timestamp + close price.
  - **Streamed run:** subscribing to the `AgentStream` event prints the incremental **Thought → Action → Observation** trace as it happens — you literally see the model reason, call the tool, read the result, and answer.
- **Memory variant:** the same agent is re-run with a `Context` object:
  - Turn 1 (with `ctx`): fetches Apple's price.
  - Turn 2 (same `ctx`): "Which date was it?" is answered **from context memory, with no second tool call** — LlamaIndex's equivalent of Lab 2's working memory.
- **What it adds:** an alternative implementation of the single-agent + memory story, and *legibility* — the reasoning trace is the feature.
- **Bridge to Lab 5:** Lab 4 is still *one* agent reasoning. Lab 5 introduces the first *second* agent — and makes the system improve its output through feedback.

### Step 5 — Lab 5: Financial news (Evaluator-Optimizer)

- **Pattern:** evaluator-optimizer = two agents: a **generator** and a **judge** (LLM-as-a-Judge), in a feedback loop until the artifact passes.
- **What it does:** 
  - `web_news_searcher` — a generator equipped with OpenAI's hosted `WebSearchTool`; instructed to return recent (via `datetime.now()`-computed dates) financial news for a region, with citations, ≤ 300 words, 2–3 paragraphs.
  - `news_evaluator` — a judge that must verify three criteria: **source link**, **publication date**, **region**, and returns a dataclass `(feedback, score)` with `score ∈ {successful, failed}`.
- **The loop (up to `max_iteration = 4`):**
  - Run the searcher on current `input_items` → print the outline.
  - Run the evaluator on it.
  - If `successful` → exit; else **append the evaluator's `feedback` to `input_items`** and loop — the generator literally re-runs with the judge's critique as part of its prompt.
- **Demonstrated runs:** first attempt at "latest 5 Eurozone news" fails evaluation (weak sources / dates); feedback is fed back and the searcher iterates (e.g. restricted to Reuters) until `successful` — then a two-region request (Eurozone + US) is judged on *both* regions before passing. Re-runs show the loop converges in the same ~count of iterations.
- **What it adds:** the first **multi-agent** system and an automatic *quality gate* — output is not trusted once; it is verified and iteratively refined. (The news window moves with the run date, so exact headlines differ; the loop is the lesson.)
- **Bridge to Lab 6:** Lab 5's agents run in a *feedback* (cyclic) loop. Lab 6's agents run in a *linear* (acyclic) chain — the other main way to structure multiple agents.

### Step 6 — Lab 6: Investment recommendation (Sequential / prompt chaining)

- **Pattern:** sequential workflow / prompt chaining — a fixed pipeline of agents where each stage's output is the next stage's input.
- **What it does:** **three** `gpt-4o-mini` agents, each with a **JSON contract** (schema enforced by instructions):
  1. **Fundamental Retrieval Agent** — calls `get_company_fundamentals` (the same FMP tool as Lab 1) and emits **only** `{ticker, fundamentals}` — strictly factual, no interpretation.
  2. **Fundamental Analysis Agent** — consumes that JSON, rates **profitability** (ROE, margins) and **valuation** (P/E, EV/EBITDA) with `rating + evidence`, lists 2–3 risks, emits `{ticker, fundamentals, analysis, risks}`.
  3. **Decision Agent** — consumes the analysis, emits `{ticker, stance: BUY|HOLD|SELL, summary: {reasons[3], watchlist[3]}}`. In the example run it lands on **HOLD** for Apple, with watchlist metrics that would flip the stance.
- **The chain (in one cell):** `fundamental_results → Runner.run(analysis_agent, ...) → Runner.run(decision_agent, ...)`.
- **What it adds:** ends the ladder with **N agents + deterministic composition**: because each stage guarantees its JSON shape, stages are independently testable and swappable — the design that orchestrator / multi-agent chapters build on later in the book.

**Why this order matters:** Lab 1 gives you the tool primitive; Lab 2 wraps it in in-conversation memory; Lab 3 makes that memory durable and reusable across conversations; Lab 4 shows the same ideas in another framework with legible reasoning; Lab 5 introduces a second agent in a refinement loop; Lab 6 scales to a three-agent contract-bound pipeline. Each lab's *output is the input to the next* — both conceptually (memory becomes episodes) and literally (Lab 2's conversation is Lab 3's data; Lab 1's tool is Lab 6's tool).

## Labs

| Lab | Notebook | What it covers | |
|---|---|---|---|
| Lab 1 | `chapter_2_lab_1_retrieving_fundamental_ratios_Apple.ipynb` | **Tool use.** An OpenAI Agents SDK agent (`gpt-4o-mini`) calls a `get_company_fundamentals` tool built on Finance Toolkit / Financial Modeling Prep to return Apple's profitability, valuation, and liquidity ratios — and shows how the model's knowledge cutoff decides which year it treats as "the most recent fiscal year" | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PacktPublishing/Building-AI-Agents-for-Finance-/blob/main/Chapter%202/chapter_2_lab_1_retrieving_fundamental_ratios_Apple.ipynb) |
| Lab 2 | `chapter_2_lab_2_portfolio_rebalancing_working_memory.ipynb` | **Working memory.** A portfolio-rebalancing agent (`gpt-4o-mini`) carried across six turns with an Agents SDK `SQLiteSession`, printing the stored conversation after each turn, then a first pass at condensing it into an episode | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PacktPublishing/Building-AI-Agents-for-Finance-/blob/main/Chapter%202/chapter_2_lab_2_portfolio_rebalancing_working_memory.ipynb) |
| Lab 3 | `chapter_2_lab_3_portfolio_rebalancing_episodic_memory.ipynb` | **Episodic memory.** The same conversation turned into a structured JSON episode (summary, allocation trajectory, what worked / what didn't, key points) two ways — a LangChain chain and the OpenAI Responses API — embedded with `text-embedding-3-small`, stored in ChromaDB, retrieved by similarity, and injected into a fresh session; ends with an interactive loop that writes the episode when you type `exit` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PacktPublishing/Building-AI-Agents-for-Finance-/blob/main/Chapter%202/chapter_2_lab_3_portfolio_rebalancing_episodic_memory.ipynb) |
| Lab 4 | `chapter_2_lab_4_ReAct_agent_LlamaIndex_fetching_stock_price_information.ipynb` | **ReAct.** LlamaIndex's workflow `ReActAgent` (`gpt-4o`) with a `get_latest_price` tool over Yahoo Finance, streamed so the Thought / Action / Observation trace is visible, then re-run with a `Context` so a follow-up question is answered from memory instead of a second tool call | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PacktPublishing/Building-AI-Agents-for-Finance-/blob/main/Chapter%202/chapter_2_lab_4_ReAct_agent_LlamaIndex_fetching_stock_price_information.ipynb) |
| Lab 5 | `chapter_2_lab_5_Financial_News_agent_evaluator_optimizer_pattern.ipynb` | **Evaluator-optimizer (LLM as a judge).** `web_news_searcher` (hosted `WebSearchTool`) collects recent Reuters headlines for a region; `news_evaluator` returns a `feedback` + `score` dataclass; the loop re-runs the searcher with the feedback until the score is `successful` or four iterations pass | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PacktPublishing/Building-AI-Agents-for-Finance-/blob/main/Chapter%202/chapter_2_lab_5_Financial_News_agent_evaluator_optimizer_pattern.ipynb) |
| Lab 6 | `chapter_2_lab_6_investment_recommendation_sequential_pattern.ipynb` | **Sequential workflow (prompt chaining).** Three `gpt-4o-mini` agents in a fixed chain — retrieval (FMP ratios) → analysis (profitability, valuation, risks) → decision (BUY / HOLD / SELL plus a watchlist) — each handing structured JSON to the next | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PacktPublishing/Building-AI-Agents-for-Finance-/blob/main/Chapter%202/chapter_2_lab_6_investment_recommendation_sequential_pattern.ipynb) |

Labs 2 and 3 share the same agent and the same six-turn conversation. Lab 3 is
the fuller treatment of long-term memory; if you only run one of the two, run
Lab 3.

## Running the labs

These notebooks are written for Google Colab and read their keys from the
Colab secret store:

```python
from google.colab import userdata
OPENAI_API_KEY = userdata.get('OPENAI_API_KEY')
```

Add each key under the **key** icon in Colab's left sidebar, using exactly the
names in the table below.

To run locally, copy the root [`.env.sample`](../.env.sample) to `.env`, fill
in the keys you need, and replace that cell with:

```python
import os
from dotenv import load_dotenv          # pip install python-dotenv

load_dotenv()
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
# Labs 1 and 6 also need:
# FINANCIAL_MODELING_PREP_API_KEY = os.environ["FINANCIAL_MODELING_PREP_API_KEY"]
```

## API keys per lab

| Lab | Keys |
|---|---|
| Lab 1 | `OPENAI_API_KEY`, `FINANCIAL_MODELING_PREP_API_KEY` |
| Lab 2 | `OPENAI_API_KEY` (chat completions and embeddings) |
| Lab 3 | `OPENAI_API_KEY` (chat completions and embeddings) |
| Lab 4 | `OPENAI_API_KEY` |
| Lab 5 | `OPENAI_API_KEY` |
| Lab 6 | `OPENAI_API_KEY`, `FINANCIAL_MODELING_PREP_API_KEY` |

Yahoo Finance (Lab 4) needs no key. Lab 5 needs no separate search key either —
`WebSearchTool` is OpenAI's own hosted tool, billed per search on top of the
tokens, and it runs through the Responses API.

## Labs 1 and 6: the Financial Modeling Prep key

Both labs pull their ratios through
[Finance Toolkit](https://www.jeroenbouma.com/projects/financetoolkit), which
wraps the [Financial Modeling Prep](https://site.financialmodelingprep.com/)
API. Create a free account there; the key appears in your dashboard.

`Toolkit([ticker], api_key=..., start_date="2022-01-01")` followed by
`collect_all_ratios()` downloads the income statement, balance sheet, and cash
flow statement for every year since `start_date` and derives 37 ratios from
them, returned as a DataFrame indexed by ratio name. The labs then keep only
the profitability, valuation, and liquidity rows.

Free FMP plans are rate-limited and do not cover every statement endpoint, so
`collect_all_ratios()` can come back partly empty (a ratio row full of `NaN`
usually means the underlying statement line was not returned, not that the
company reported nothing). If that happens, check what your plan includes
before debugging the agent — the tool is fine, the data is missing.

## Labs 2 and 3: what actually persists

- `SQLiteSession("conversation_ptf")` keeps the conversation **in memory
  only** — `db_path` defaults to `":memory:"`, so the session is gone when the
  kernel restarts. Pass a file to keep it across runs:
  `SQLiteSession("conversation_ptf", "ptf_rebal.db")`.
- ChromaDB is the opposite: `PersistentClient(path="./chroma_ptf_rebal")`
  writes a folder next to the notebook. In Colab that folder lives on the
  runtime's disk and disappears when the runtime is recycled — mount Google
  Drive or download the folder if you want your episodes to survive.
- The final "All in" loop in Lab 3 reads from `input()`. It stores nothing
  until you type `exit`: that is what triggers the summarization of the
  session into an episode and the write to ChromaDB.

## Lab 4: keep the `-U` on the LlamaIndex install

The lab uses the workflow-based agent — `from
llama_index.core.agent.workflow import ReActAgent`, driven with `await
agent.run(...)` — which is why the install cell is `!pip install -U
llama-index`. On older `llama-index-core` releases (0.12.x, which is what you
get if something else in the environment pins it) that class requires `name`
and `description`, and the constructor call as written raises a Pydantic
`ValidationError`. Either upgrade, or add `name="price_agent",
description="Fetches the latest stock price"`.

## Lab 5: the loop is interactive

`main()` starts with `msg = input("User's request:")`, so run it in an
interactive session rather than as a script. The requests used in the chapter
are quoted in the comments under each run cell, for example:

> Give me the latest 5 news items in the Eurozone, and specify the source for
> each one.

The loop exits when the evaluator returns `score == "successful"`, or after
`max_iteration = 4` refinement rounds. Because the dates in the instructions
are computed from `datetime.now()`, the news window moves with the day you run
it — the output will not match the one printed in the chapter.

## Why there is no `requirements.txt`

Each notebook installs its own packages, in the section that needs them:

| Lab | Installed in the notebook | Assumed present in Colab |
|---|---|---|
| Lab 1 | `openai-agents`, `financetoolkit` | `pandas` |
| Lab 2 | `openai-agents`, `langchain_openai`, `chromadb` | `nest_asyncio` |
| Lab 3 | `openai-agents`, `langchain_openai`, `chromadb` | `nest_asyncio` |
| Lab 4 | `llama-index` (with `-U`) | `yfinance` |
| Lab 5 | `openai`, `openai-agents` | `nest_asyncio` |
| Lab 6 | `openai`, `openai-agents`, `financetoolkit` | `nest_asyncio`, `pandas` |

Keeping the installs in the notebooks leaves one source of truth instead of two
that drift apart, and it avoids pinning packages against the versions Colab
already ships. Running locally, install the packages in both columns for the
lab you want to run.

## Known rough edges

Three cells need a small manual fix if you run a notebook top to bottom:

- **Lab 3** calls `json.loads` / `json.dumps` in the "Method 2: Responses API"
  cells, but the only `import json` in the notebook is inside a commented-out
  block. Add `import json` before running them.
- **Lab 3**, same section, assigns `episodic_memory = json.dumps(...)` — a
  *string* — and the "Add Memory in DB" cell then subscripts it like a dict.
  Keep the parsed object (`json.loads(...)`) if you ran Method 2, or re-run the
  LangChain cell, which already returns a dict.
- **Lab 5** opens with a cell that displays `web_news_searcher_BOT.png` from an
  undefined `path` variable. The image is the architecture diagram from the
  chapter and is not in the repo — skip the cell.
