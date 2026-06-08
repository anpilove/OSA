"""
G-Eval Prompt Templates for Docstring Quality Assessment (STRICT VERSION)

This version is calibrated to:
- Avoid rewarding verbosity
- Penalize hallucinated or speculative documentation
- Prefer usefulness over formatting
- Be robust on simple functions

Based on G-Eval (LLM-as-Judge) and RepoAgent methodology,
with additional anchoring and constraints.
"""

# =========================
# System prompt
# =========================

SYSTEM_PROMPT = """You are an expert Python developer and documentation reviewer.

You evaluate docstrings strictly based on their usefulness to a developer
who wants to USE the function.

You do NOT reward verbosity, boilerplate, or formatting by itself.
You do NOT assume undocumented behavior unless it is implied by the code.
    You are precise, conservative, and consistent in scoring.
"""

# =========================
# Evaluation prompt template
# =========================

EVALUATION_PROMPT_TEMPLATE = """Please evaluate the quality of the following Python docstring on a scale from 0 to 1, where:
- 0.0-0.2: Very poor quality
- 0.2-0.4: Poor quality
- 0.4-0.6: Acceptable quality
- 0.6-0.8: Good quality
- 0.8-1.0: Excellent quality

# Function Information

**Function Name:** {function_name}

**Function Signature:**
```python
{function_signature}
```

**Function Source Code:**

```python
{source_code}
```

**Docstring to Evaluate:**

```
{docstring}
```

# Evaluation Criteria: {criterion}

{criterion_description}

# Instructions

1. Carefully read the function source code and the docstring.
2. Evaluate the docstring based SOLELY on the criterion: **{criterion}**.
3. Provide a score between 0.0 and 1.0.
4. Explain your reasoning in 2-3 sentences, focusing on specific strengths or weaknesses.

# Output Format

Return your evaluation as a JSON object:

```json
{{
  "score": <float between 0.0 and 1.0>,
  "reasoning": "<your detailed reasoning>"
}}
```
"""

# =========================
# Criterion descriptions (IMPROVED FOR DOCSTRINGS)
# =========================

CRITERIA_DESCRIPTIONS = {
    "clarity": """Clarity measures how easily a developer can understand what the function does and how to use it from the documentation alone.

    High score (0.8-1.0) if:
    - Purpose and usage are immediately clear
    - Language is precise and unambiguous
    - Structure (sections) aids understanding when needed

    Medium score (0.5-0.8) if:
    - Generally understandable but some parts are vague
    - Could be clearer with minor improvements

    Low score (0.0-0.5) if:
    - Wording is confusing or ambiguous
    - Key information is buried in unnecessary text
    - Developer would need to read source code to understand usage""",

        "completeness": """Completeness measures whether the docstring covers all ESSENTIAL information needed to use the function correctly.

    High score (0.8-1.0) if:
    - All non-obvious parameters are documented with purpose
    - Return value is explained (if not obvious)
    - Important behavior, constraints, or side effects are mentioned
    - Default values are specified

    Medium score (0.5-0.8) if:
    - Most important information is present but some details missing
    - Missing type hints for some parameters
    - Missing information about edge cases

    Low score (0.0-0.5) if:
    - Critical information missing (e.g., required parameters not documented)
    - Returns section missing for non-None return values
    - Important behavior undocumented

    Do NOT penalize for:
    - Missing obvious information (e.g., not documenting that `print()` prints)
    - Not documenting private/internal implementation details
    - Missing examples (examples are optional)""",

        "accuracy": """Accuracy measures whether the docstring correctly describes the actual code behavior without contradictions or hallucinations.

    High score (0.8-1.0) if:
    - All statements match the code exactly
    - No false or exaggerated claims
    - Types and behavior described correctly

    Medium score (0.5-0.8) if:
    - Mostly accurate but minor discrepancies
    - Some descriptions slightly imprecise

    Low score (0.0-0.5) if:
    - Contains false information about behavior
    - Contradicts the source code
    - Hallucinates parameters or features not in code
    - Incorrect types or return values

    Score 0.0 for:
    - Complete mismatch with actual function behavior""",

        "relevance": """Relevance measures how useful the information is to someone CALLING the function, versus describing implementation details.

    High score (0.8-1.0) if:
    - Focuses on user-facing behavior
    - Explains WHAT the function does and WHY (when non-obvious)
    - Avoids internal implementation details
    - Information helps make decisions about using the function

    Medium score (0.5-0.8) if:
    - Mostly relevant but includes some implementation trivia
    - Could be more focused on user needs

    Low score (0.0-0.5) if:
    - Mostly repeats the function signature or trivial details
    - Focuses on internal implementation without user value
    - Includes irrelevant information""",

        "conciseness": """Conciseness measures whether the docstring achieves its purpose with appropriate brevity, avoiding redundancy and unnecessary text.

    High score (0.8-1.0) if:
    - Every sentence adds unique value
    - No redundancy or repetition
    - Length appropriate for function complexity
    - No boilerplate sections without content

    Medium score (0.5-0.8) if:
    - Some minor redundancies
    - Slightly longer than needed but still valuable

    Low score (0.0-0.5) if:
    - Verbose without adding information
    - Contains obvious statements
    - Boilerplate sections with no real content
    - Unnecessary formatting that doesn't aid understanding

    IMPORTANT: Conciseness is about VALUE, not just length.
    A longer docstring can be concise if every part is valuable.
    A short docstring can be non-concise if it has fluff.""",
}

# =========================
# Comparison prompt template (IMPROVED)
# =========================

COMPARISON_PROMPT_TEMPLATE = """Please compare the quality of two docstrings for the same Python function.

# Function Information

**Function Name:** {function_name}
**File Path:** {file_path}
**Class Name:** {class_name}

**Function Signature:**
```python
{function_signature}
```

**Function Source Code:**
```python
{source_code}
```

# Docstring A (Original/Baseline)
```
{docstring_a}
```

# Docstring B (Enhanced)
```
{docstring_b}
```

# Evaluation Criteria for Docstrings

Evaluate both docstrings based on these REAL-WORLD criteria:

## 1. Accuracy (20%)
Does the docstring correctly describe the code without errors or hallucinations?

## 2. Completeness (20%)
Does the docstring cover all essential information needed to use the function?

## 3. Clarity (20%)
Is the docstring easy to understand what the function does and how to use it?

## 4. Relevance (20%)
Is the information in the docstring useful to someone calling the function?

## 5. Practical Usefulness (20%)
How helpful would this docstring be in actual development work?

# Important Principles for Docstring Evaluation

1. **Docstrings are for developers, not end-users**: Evaluate from perspective of a developer using the function
2. **No examples required**: Examples in docstrings are optional and should not affect scoring
3. **Avoid verbosity**: More text ≠ better docstring
4. **Preserve technical details**: Important implementation notes that affect usage should be kept
5. **Format is secondary**: Google-style vs numpy-style doesn't matter if content is good
6. **Focus on API documentation**: Docstrings should help with correct usage, not teach concepts

# Scoring Guidelines
- 0.9-1.0: Excellent - nearly perfect for a docstring
- 0.7-0.9: Good - minor improvements possible
- 0.5-0.7: Acceptable - works but could be better
- 0.3-0.5: Poor - significant issues
- 0.0-0.3: Very poor - misleading or useless

# Output Format

Return your evaluation as a JSON object with this structure:

```json
{{
  "accuracy": {{
    "docstring_a_score": <float 0.0-1.0>,
    "docstring_b_score": <float 0.0-1.0>,
    "reasoning": "<brief explanation of accuracy comparison>"
  }},
  "completeness": {{
    "docstring_a_score": <float 0.0-1.0>,
    "docstring_b_score": <float 0.0-1.0>,
    "reasoning": "<brief explanation of completeness comparison>"
  }},
  "clarity": {{
    "docstring_a_score": <float 0.0-1.0>,
    "docstring_b_score": <float 0.0-1.0>,
    "reasoning": "<brief explanation of clarity comparison>"
  }},
  "relevance": {{
    "docstring_a_score": <float 0.0-1.0>,
    "docstring_b_score": <float 0.0-1.0>,
    "reasoning": "<brief explanation of relevance comparison>"
  }},
  "overall": {{
    "docstring_a_score": <float 0.0-1.0>,
    "docstring_b_score": <float 0.0-1.0>,
    "reasoning": "<summary explaining which docstring is better and why>"
  }},
  "overall_a": <calculated average float>,
  "overall_b": <calculated average float>,
  "overall_delta": <difference: overall_b - overall_a>
}}
```

Calculate the overall scores as weighted averages:
overall = (accuracy*0.2 + completeness*0.2 + clarity*0.2 + relevance*0.2)

The delta shows improvement: positive means B is better, negative means worse.
"""

# =========================
# Prompt builder functions
# =========================

def build_evaluation_prompt(
    function_name: str,
    function_signature: str,
    source_code: str,
    docstring: str,
    criterion: str
) -> str:
    """
    Build an evaluation prompt for a single docstring on a specific criterion.
    """
    if criterion not in CRITERIA_DESCRIPTIONS:
        raise ValueError(f"Unknown criterion: {criterion}. Must be one of {list(CRITERIA_DESCRIPTIONS.keys())}")

    return EVALUATION_PROMPT_TEMPLATE.format(
        function_name=function_name,
        function_signature=function_signature,
        source_code=source_code,
        docstring=docstring,
        criterion=criterion,
        criterion_description=CRITERIA_DESCRIPTIONS[criterion]
    )


def build_comparison_prompt(
    function_name: str,
    function_signature: str,
    source_code: str,
    docstring_a: str,
    docstring_b: str,
    file_path: str = "",
    class_name: str = None
) -> str:
    """
    Build a strict comparison prompt for two docstrings.
    """
    return COMPARISON_PROMPT_TEMPLATE.format(
        function_name=function_name,
        function_signature=function_signature,
        source_code=source_code,
        docstring_a=docstring_a,
        docstring_b=docstring_b,
        file_path=file_path or "Unknown",
        class_name=class_name or "None"
    )