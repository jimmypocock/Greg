"""
Evaluation runner for Greg RAG system.

Usage:
    # Run evaluation with keyword matching (fast)
    python -m tests.evaluation.eval_runner --document-id <uuid>

    # Run with LLM-as-judge (more accurate)
    python -m tests.evaluation.eval_runner --document-id <uuid> --llm-judge

    # Run ablation test (compare RAG vs no-context)
    python -m tests.evaluation.eval_runner --document-id <uuid> --ablation --llm-judge

    # Save results
    python -m tests.evaluation.eval_runner --document-id <uuid> --save
"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class TestCase:
    id: str
    question: str
    expected_keywords: list[str]
    expected_not_contain: list[str]
    category: str
    chapter: Optional[int]
    notes: str


@dataclass
class EvalResult:
    test_case_id: str
    question: str
    category: str
    answer: str
    sources: list[dict]
    keywords_found: list[str]
    keywords_missing: list[str]
    unwanted_found: list[str]
    retrieval_score: float
    passed: bool
    error: Optional[str] = None
    # LLM judge fields
    llm_judgment: Optional[str] = None
    llm_score: Optional[int] = None
    llm_reasoning: Optional[str] = None
    # Ablation fields (no-context comparison)
    ablation_answer: Optional[str] = None
    ablation_score: Optional[float] = None
    ablation_judgment: Optional[str] = None
    ablation_reasoning: Optional[str] = None
    rag_contribution: Optional[str] = None  # "high", "medium", "low", "none"


class LLMJudge:
    """Uses local Ollama to judge answer quality."""

    def __init__(self, model: str = "mistral", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.client = httpx.Client(timeout=120.0)

    def judge(
        self,
        question: str,
        answer: str,
        expected_keywords: list[str],
        category: str,
        notes: str,
    ) -> dict:
        """
        Ask LLM to judge if the answer is correct.

        Returns: {"score": 1-5, "passed": bool, "reasoning": str}
        """
        if category == "unanswerable":
            prompt = f"""You are evaluating a RAG system's answer. The question asked is NOT answerable from the provided documents - the system should indicate it doesn't have the information.

Question: {question}
Answer given: {answer}

Did the system correctly indicate it doesn't have this information WITHOUT providing the actual answer from its general knowledge?

Respond in JSON format:
{{"score": <1-5>, "passed": <true if correctly refused to answer, false if it answered anyway>, "reasoning": "<brief explanation>"}}

Score guide:
5 = Perfectly refused, said "I don't have information about this"
3 = Mentioned uncertainty but still provided an answer
1 = Confidently answered from general knowledge, ignoring the documents"""

        else:
            prompt = f"""You are evaluating a RAG system's answer for correctness.

Question: {question}
Answer given: {answer}
Expected to mention: {', '.join(expected_keywords) if expected_keywords else 'N/A'}
Context about correct answer: {notes}

Is this answer correct and complete? Consider:
1. Does it answer the question asked?
2. Is the information accurate?
3. Does it cover the key concepts (even if using different words than expected keywords)?

Respond in JSON format:
{{"score": <1-5>, "passed": <true/false>, "reasoning": "<brief explanation>"}}

Score guide:
5 = Perfect, complete answer
4 = Correct but missing minor details
3 = Partially correct
2 = Mostly incorrect
1 = Completely wrong or didn't answer"""

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "{}")
                # Parse the JSON response
                try:
                    judgment = json.loads(text)
                    return {
                        "score": judgment.get("score", 3),
                        "passed": judgment.get("passed", False),
                        "reasoning": judgment.get("reasoning", "No reasoning provided"),
                    }
                except json.JSONDecodeError:
                    return {
                        "score": 3,
                        "passed": False,
                        "reasoning": f"Failed to parse LLM response: {text[:200]}",
                    }
            else:
                return {
                    "score": 0,
                    "passed": False,
                    "reasoning": f"Ollama error: {response.status_code}",
                }

        except Exception as e:
            return {
                "score": 0,
                "passed": False,
                "reasoning": f"Error calling Ollama: {e}",
            }

    def ask_without_context(self, question: str) -> str:
        """Ask the LLM a question without any RAG context (ablation test)."""
        prompt = f"""Answer the following question concisely and accurately based only on your training knowledge. If you don't know, say so.

Question: {question}

Answer:"""

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                return f"[Error: {response.status_code}]"

        except Exception as e:
            return f"[Error: {e}]"

    def compare_answers(
        self,
        question: str,
        rag_answer: str,
        no_context_answer: str,
        expected_keywords: list[str],
        notes: str,
    ) -> dict:
        """
        Compare RAG answer vs no-context answer to determine RAG contribution.

        Returns: {"rag_score": 1-5, "no_context_score": 1-5, "contribution": str, "reasoning": str}
        """
        prompt = f"""You are comparing two answers to determine if RAG (retrieval) is actually helping.

Question: {question}
Expected concepts: {', '.join(expected_keywords) if expected_keywords else 'N/A'}
Context about correct answer: {notes}

ANSWER A (with RAG/retrieved context):
{rag_answer}

ANSWER B (no context, just LLM knowledge):
{no_context_answer}

Compare these answers and determine:
1. Score each answer 1-5 for correctness
2. Determine RAG contribution level:
   - "high": RAG answer is significantly better, contains specific details not in B
   - "medium": RAG answer is somewhat better or more specific
   - "low": Both answers are similar quality
   - "none": No-context answer is equal or better (RAG not helping)

Respond in JSON format:
{{"rag_score": <1-5>, "no_context_score": <1-5>, "contribution": "<high/medium/low/none>", "reasoning": "<brief explanation of the difference>"}}"""

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "{}")
                try:
                    comparison = json.loads(text)
                    return {
                        "rag_score": comparison.get("rag_score", 3),
                        "no_context_score": comparison.get("no_context_score", 3),
                        "contribution": comparison.get("contribution", "unknown"),
                        "reasoning": comparison.get("reasoning", "No reasoning provided"),
                    }
                except json.JSONDecodeError:
                    return {
                        "rag_score": 0,
                        "no_context_score": 0,
                        "contribution": "error",
                        "reasoning": f"Failed to parse: {text[:200]}",
                    }
            else:
                return {
                    "rag_score": 0,
                    "no_context_score": 0,
                    "contribution": "error",
                    "reasoning": f"Ollama error: {response.status_code}",
                }

        except Exception as e:
            return {
                "rag_score": 0,
                "no_context_score": 0,
                "contribution": "error",
                "reasoning": f"Error: {e}",
            }

    def close(self):
        self.client.close()


class GregEvaluator:
    """Evaluates Greg's RAG performance against test cases."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        document_id: Optional[str] = None,
        use_llm_judge: bool = False,
        llm_model: str = "mistral",
        run_ablation: bool = False,
    ):
        self.base_url = base_url
        self.document_id = document_id or "all"
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token: Optional[str] = None
        self.use_llm_judge = use_llm_judge
        self.run_ablation = run_ablation
        # Create LLM judge if needed for judging OR ablation
        self.llm_judge = LLMJudge(model=llm_model) if (use_llm_judge or run_ablation) else None

    async def authenticate(self, email: str, password: str) -> bool:
        """Authenticate with Greg API."""
        try:
            response = await self.client.post(
                f"{self.base_url}/auth/token",
                json={"email": email, "password": password},
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                return True
            else:
                print(f"Auth failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Auth error: {e}")
            return False

    async def ask_question(
        self, question: str, document_id: Optional[str] = None
    ) -> dict:
        """Ask Greg a question and get the response."""
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "question": question,
            "document_id": document_id or self.document_id,
            "stream": False,
            "max_results": 5,
        }

        response = await self.client.post(
            f"{self.base_url}/ask",
            json=payload,
            headers=headers,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"HTTP {response.status_code}: {response.text}",
                "answer": "",
                "sources": [],
            }

    def evaluate_answer(self, test_case: TestCase, response: dict) -> EvalResult:
        """Evaluate a single answer against expected criteria."""
        answer = response.get("answer", "")
        answer_lower = answer.lower()
        sources = response.get("sources", [])
        error = response.get("error")

        # Check for expected keywords
        keywords_found = []
        keywords_missing = []
        for keyword in test_case.expected_keywords:
            if keyword.lower() in answer_lower:
                keywords_found.append(keyword)
            else:
                keywords_missing.append(keyword)

        # Check for unwanted content
        unwanted_found = []
        for unwanted in test_case.expected_not_contain:
            if unwanted.lower() in answer_lower:
                unwanted_found.append(unwanted)

        # Calculate retrieval score
        retrieval_score = 0.0
        if sources:
            scores = [s.get("relevance_score", 0) for s in sources]
            retrieval_score = sum(scores) / len(scores) if scores else 0.0

        # Determine if passed (keyword-based)
        if test_case.category == "unanswerable":
            uncertainty_indicators = [
                "don't have",
                "not in",
                "no information",
                "cannot find",
                "not mentioned",
                "doesn't contain",
                "does not contain",
            ]
            has_uncertainty = any(ind in answer_lower for ind in uncertainty_indicators)
            keyword_passed = len(unwanted_found) == 0 and has_uncertainty
        else:
            keyword_ratio = (
                len(keywords_found) / len(test_case.expected_keywords)
                if test_case.expected_keywords
                else 1.0
            )
            keyword_passed = keyword_ratio >= 0.5 and len(unwanted_found) == 0

        # LLM judgment if enabled
        llm_judgment = None
        llm_score = None
        llm_reasoning = None
        llm_passed = None

        if self.llm_judge and not error:
            judgment = self.llm_judge.judge(
                question=test_case.question,
                answer=answer,
                expected_keywords=test_case.expected_keywords,
                category=test_case.category,
                notes=test_case.notes,
            )
            llm_score = judgment["score"]
            llm_passed = judgment["passed"]
            llm_reasoning = judgment["reasoning"]
            llm_judgment = "PASS" if llm_passed else "FAIL"

        # Final passed status: use LLM if available, otherwise keywords
        passed = llm_passed if llm_passed is not None else keyword_passed

        # Ablation test if enabled
        ablation_answer = None
        ablation_score = None
        ablation_judgment = None
        ablation_reasoning = None
        rag_contribution = None

        if self.run_ablation and self.llm_judge and not error:
            # Get answer without RAG context
            ablation_answer = self.llm_judge.ask_without_context(test_case.question)

            # Compare the two answers
            comparison = self.llm_judge.compare_answers(
                question=test_case.question,
                rag_answer=answer,
                no_context_answer=ablation_answer,
                expected_keywords=test_case.expected_keywords,
                notes=test_case.notes,
            )

            ablation_score = comparison["no_context_score"]
            rag_contribution = comparison["contribution"]
            ablation_reasoning = comparison["reasoning"]
            ablation_judgment = f"RAG: {comparison['rag_score']}/5, No-context: {ablation_score}/5"

        return EvalResult(
            test_case_id=test_case.id,
            question=test_case.question,
            category=test_case.category,
            answer=answer,
            sources=sources,
            keywords_found=keywords_found,
            keywords_missing=keywords_missing,
            unwanted_found=unwanted_found,
            retrieval_score=retrieval_score,
            passed=passed,
            error=error,
            llm_judgment=llm_judgment,
            llm_score=llm_score,
            llm_reasoning=llm_reasoning,
            ablation_answer=ablation_answer,
            ablation_score=ablation_score,
            ablation_judgment=ablation_judgment,
            ablation_reasoning=ablation_reasoning,
            rag_contribution=rag_contribution,
        )

    async def run_evaluation(self, test_cases: list[TestCase]) -> list[EvalResult]:
        """Run all test cases and return results."""
        results = []

        for i, test_case in enumerate(test_cases):
            print(f"[{i+1}/{len(test_cases)}] Testing: {test_case.question[:50]}...")

            try:
                response = await self.ask_question(test_case.question)
                result = self.evaluate_answer(test_case, response)
                results.append(result)

                status = "PASS" if result.passed else "FAIL"
                score_info = f"retrieval: {result.retrieval_score:.2f}"
                if result.llm_score is not None:
                    score_info += f", llm: {result.llm_score}/5"
                if result.rag_contribution:
                    score_info += f", RAG contrib: {result.rag_contribution}"
                print(f"         {status} ({score_info})")

            except Exception as e:
                print(f"         ERROR: {e}")
                results.append(
                    EvalResult(
                        test_case_id=test_case.id,
                        question=test_case.question,
                        category=test_case.category,
                        answer="",
                        sources=[],
                        keywords_found=[],
                        keywords_missing=test_case.expected_keywords,
                        unwanted_found=[],
                        retrieval_score=0.0,
                        passed=False,
                        error=str(e),
                    )
                )

        return results

    async def close(self):
        """Close HTTP clients."""
        await self.client.aclose()
        if self.llm_judge:
            self.llm_judge.close()


def load_test_cases(path: Path) -> list[TestCase]:
    """Load test cases from JSON file."""
    with open(path) as f:
        data = json.load(f)

    return [
        TestCase(
            id=tc["id"],
            question=tc["question"],
            expected_keywords=tc["expected_keywords"],
            expected_not_contain=tc["expected_not_contain"],
            category=tc["category"],
            chapter=tc.get("chapter"),
            notes=tc.get("notes", ""),
        )
        for tc in data["test_cases"]
    ]


def summarize_results(results: list[EvalResult]) -> dict:
    """Generate summary statistics from results."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    # By category
    by_category = {}
    for r in results:
        if r.category not in by_category:
            by_category[r.category] = {"passed": 0, "total": 0}
        by_category[r.category]["total"] += 1
        if r.passed:
            by_category[r.category]["passed"] += 1

    # Average retrieval score
    avg_retrieval = (
        sum(r.retrieval_score for r in results) / total if total > 0 else 0
    )

    # Average LLM score if available
    llm_scores = [r.llm_score for r in results if r.llm_score is not None]
    avg_llm_score = sum(llm_scores) / len(llm_scores) if llm_scores else None

    # Identify suspicious cases (low retrieval but passed)
    suspicious = [
        r for r in results
        if r.passed and r.retrieval_score < 0.4 and r.category != "unanswerable"
    ]

    # Ablation statistics
    ablation_results = [r for r in results if r.rag_contribution is not None]
    rag_contribution_counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "none": 0,
    }
    for r in ablation_results:
        if r.rag_contribution in rag_contribution_counts:
            rag_contribution_counts[r.rag_contribution] += 1

    ablation_scores = [r.ablation_score for r in results if r.ablation_score is not None]
    avg_ablation_score = sum(ablation_scores) / len(ablation_scores) if ablation_scores else None

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{100 * passed / total:.1f}%" if total > 0 else "N/A",
        "avg_retrieval_score": round(avg_retrieval, 3),
        "avg_llm_score": round(avg_llm_score, 2) if avg_llm_score else None,
        "by_category": by_category,
        "suspicious_count": len(suspicious),
        "ablation": {
            "total_compared": len(ablation_results),
            "avg_no_context_score": round(avg_ablation_score, 2) if avg_ablation_score else None,
            "rag_contribution": rag_contribution_counts,
        } if ablation_results else None,
    }


def print_report(results: list[EvalResult], summary: dict, use_llm_judge: bool, run_ablation: bool = False):
    """Print a formatted evaluation report."""
    print("\n" + "=" * 60)
    print("EVALUATION REPORT")
    mode_parts = []
    if use_llm_judge:
        mode_parts.append("LLM-as-Judge")
    else:
        mode_parts.append("Keyword Matching")
    if run_ablation:
        mode_parts.append("Ablation Test")
    print(f"(Using {' + '.join(mode_parts)})")
    print("=" * 60)

    print(f"\nOverall: {summary['passed']}/{summary['total']} ({summary['pass_rate']})")
    print(f"Average retrieval score: {summary['avg_retrieval_score']}")
    if summary['avg_llm_score']:
        print(f"Average LLM score: {summary['avg_llm_score']}/5")

    print("\nBy Category:")
    for cat, stats in summary["by_category"].items():
        pct = 100 * stats["passed"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    # Ablation results
    if summary.get("ablation"):
        ablation = summary["ablation"]
        print("\n" + "-" * 60)
        print("ABLATION TEST RESULTS (RAG vs No-Context)")
        print("-" * 60)
        print(f"\nCompared {ablation['total_compared']} answers")
        if ablation['avg_no_context_score']:
            print(f"Average no-context score: {ablation['avg_no_context_score']}/5")
            if summary['avg_llm_score']:
                improvement = summary['avg_llm_score'] - ablation['avg_no_context_score']
                print(f"RAG improvement: {improvement:+.2f} points")

        contrib = ablation['rag_contribution']
        total_contrib = sum(contrib.values())
        if total_contrib > 0:
            print("\nRAG Contribution Breakdown:")
            for level in ["high", "medium", "low", "none"]:
                count = contrib[level]
                pct = 100 * count / total_contrib
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                print(f"  {level:8s}: {bar} {count:2d} ({pct:4.1f}%)")

            # Calculate effective RAG rate
            effective = contrib["high"] + contrib["medium"]
            effective_pct = 100 * effective / total_contrib
            print(f"\nEffective RAG usage (high+medium): {effective}/{total_contrib} ({effective_pct:.1f}%)")

    # Suspicious cases (low retrieval + passed)
    suspicious = [
        r for r in results
        if r.passed and r.retrieval_score < 0.4 and r.category != "unanswerable"
    ]
    if suspicious:
        print("\n" + "-" * 60)
        print("SUSPICIOUS: Low Retrieval but Passed (possible LLM prior knowledge)")
        print("-" * 60)
        for r in suspicious:
            print(f"\n[{r.test_case_id}] {r.question}")
            print(f"  Retrieval score: {r.retrieval_score:.2f} (LOW)")
            if r.llm_reasoning:
                print(f"  LLM reasoning: {r.llm_reasoning}")

    # Failed cases
    failed = [r for r in results if not r.passed]
    if failed:
        print("\n" + "-" * 60)
        print("FAILED CASES:")
        print("-" * 60)
        for r in failed:
            print(f"\n[{r.test_case_id}] {r.question}")
            if r.error:
                print(f"  Error: {r.error}")
            else:
                if r.llm_reasoning:
                    print(f"  LLM Score: {r.llm_score}/5")
                    print(f"  LLM Reasoning: {r.llm_reasoning}")
                else:
                    print(f"  Missing keywords: {r.keywords_missing}")
                if r.unwanted_found:
                    print(f"  Unwanted content: {r.unwanted_found}")
                print(f"  Answer preview: {r.answer[:200]}...")


def save_results(results: list[EvalResult], summary: dict, output_dir: Path, use_llm_judge: bool, run_ablation: bool = False):
    """Save results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_llm" if use_llm_judge else "_keyword"
    if run_ablation:
        suffix += "_ablation"
    output_path = output_dir / f"eval_results_{timestamp}{suffix}.json"

    methods = []
    if use_llm_judge:
        methods.append("llm-as-judge")
    else:
        methods.append("keyword-matching")
    if run_ablation:
        methods.append("ablation")

    data = {
        "timestamp": timestamp,
        "evaluation_method": "+".join(methods),
        "summary": summary,
        "results": [asdict(r) for r in results],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to: {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Evaluate Greg RAG system")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Greg API URL")
    parser.add_argument("--document-id", help="Specific document ID to query")
    parser.add_argument("--email", default=os.getenv("GREG_EMAIL", "test@example.com"))
    parser.add_argument("--password", default=os.getenv("GREG_PASSWORD", "testpassword"))
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--llm-judge", action="store_true", help="Use LLM to judge answers (more accurate, slower)")
    parser.add_argument("--ablation", action="store_true", help="Run ablation test to compare RAG vs no-context answers")
    parser.add_argument("--llm-model", default="mistral", help="Ollama model for LLM judge")
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=Path(__file__).parent / "test_cases.json",
        help="Path to test cases JSON",
    )
    args = parser.parse_args()

    # Load test cases
    print(f"Loading test cases from: {args.test_cases}")
    test_cases = load_test_cases(args.test_cases)
    print(f"Loaded {len(test_cases)} test cases")

    if args.llm_judge:
        print(f"Using LLM-as-judge with model: {args.llm_model}")
    if args.ablation:
        print("Ablation mode enabled: will compare RAG vs no-context answers")

    # Initialize evaluator
    evaluator = GregEvaluator(
        base_url=args.base_url,
        document_id=args.document_id,
        use_llm_judge=args.llm_judge,
        llm_model=args.llm_model,
        run_ablation=args.ablation,
    )

    try:
        # Authenticate
        print(f"\nAuthenticating as {args.email}...")
        if not await evaluator.authenticate(args.email, args.password):
            print("Authentication failed. Make sure Greg is running and credentials are correct.")
            return

        print("Authenticated successfully.\n")

        # Run evaluation
        print("Running evaluation...")
        results = await evaluator.run_evaluation(test_cases)

        # Summarize and report
        summary = summarize_results(results)
        print_report(results, summary, args.llm_judge, args.ablation)

        # Save if requested
        if args.save:
            save_results(
                results, summary, Path(__file__).parent / "results", args.llm_judge, args.ablation
            )

    finally:
        await evaluator.close()


if __name__ == "__main__":
    asyncio.run(main())
