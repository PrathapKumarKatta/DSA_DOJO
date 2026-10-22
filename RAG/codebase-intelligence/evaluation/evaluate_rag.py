import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import uuid

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User
from app.models.source_file import SourceFile
from app.models.code_chunk import CodeChunk
from app.rag.vector_store import VectorStore
from app.rag.hybrid_search import HybridRetriever
from app.rag.reranker import CrossEncoderReranker
from app.services.ingestion_service import IngestionService
from app.core.security import get_password_hash


def ensure_evaluated_project(db) -> uuid.UUID:
    """Ensure sample microservice is indexed in database for evaluation."""
    user = db.query(User).filter(User.email == "evaluator@codebase.ai").first()
    if not user:
        user = User(
            email="evaluator@codebase.ai",
            password_hash=get_password_hash("EvalPassword123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    project = (
        db.query(Project)
        .filter(Project.user_id == user.id, Project.name == "Evaluation Benchmark")
        .first()
    )

    if not project or project.status != "ready":
        if not project:
            project = Project(user_id=user.id, name="Evaluation Benchmark", status="processing")
            db.add(project)
            db.commit()
            db.refresh(project)

        from app.repositories.job_repo import JobRepository
        job_repo = JobRepository(db)
        job = job_repo.create(project_id=project.id)

        zip_path = Path("/Users/charan/RAG/sample_projects/microservice.zip")
        temp_dir = Path("/tmp/eval_ingestion")
        temp_dir.mkdir(parents=True, exist_ok=True)

        IngestionService.run_ingestion_pipeline(
            project_id=project.id,
            job_id=job.id,
            zip_path=zip_path,
            temp_dir=temp_dir,
        )
        db.refresh(project)

    return project.id


def run_benchmark():
    db = SessionLocal()
    try:
        project_id = ensure_evaluated_project(db)
        vector_store = VectorStore(db)
        hybrid_retriever = HybridRetriever(db, vector_store)
        reranker = CrossEncoderReranker.get_instance()

        dataset_path = Path(__file__).parent / "dataset" / "benchmark_questions.json"
        with open(dataset_path, "r") as f:
            questions = json.load(f)

        strategies = ["vector_only", "keyword_only", "hybrid_rrf", "hybrid_reranked"]
        metrics: Dict[str, Dict[str, Any]] = {
            s: {
                "recall_at_1": 0.0,
                "recall_at_3": 0.0,
                "recall_at_5": 0.0,
                "mrr": 0.0,
                "avg_latency_ms": 0.0,
                "evaluated_queries": 0,
            }
            for s in strategies
        }

        # Filter only questions with answers for recall/MRR
        eval_questions = [q for q in questions if q.get("has_answer", True)]

        print("=" * 80)
        print("RUNNING CODEBASE INTELLIGENCE RAG EVALUATION BENCHMARK")
        print("=" * 80)
        print(f"Project ID: {project_id}")
        print(f"Total Questions: {len(questions)} (Positive: {len(eval_questions)})")
        print("-" * 80)

        for s in strategies:
            total_r1 = 0
            total_r3 = 0
            total_r5 = 0
            total_rr = 0.0
            latencies = []

            for q in eval_questions:
                query = q["question"]
                expected_files = q["expected_files"]

                start_t = time.perf_counter()

                if s == "vector_only":
                    hits = vector_store.search_vector(project_id, query, limit=5)
                    retrieved_files = [f.path for chunk, f, score in hits]

                elif s == "keyword_only":
                    hits = vector_store.search_keyword(project_id, query, limit=5)
                    retrieved_files = [f.path for chunk, f, score in hits]

                elif s == "hybrid_rrf":
                    hits = hybrid_retriever.retrieve(project_id, query, top_k=5)
                    retrieved_files = [h.file_path for h in hits]

                elif s == "hybrid_reranked":
                    candidates = hybrid_retriever.retrieve(project_id, query, top_k=15)
                    reranked = reranker.rerank(query, candidates, top_k=5)
                    retrieved_files = [h.file_path for h in reranked]

                latency_ms = (time.perf_counter() - start_t) * 1000
                latencies.append(latency_ms)

                # Check Recall@1, 3, 5
                def has_expected(items):
                    return any(any(exp in item for exp in expected_files) for item in items)

                if has_expected(retrieved_files[:1]):
                    total_r1 += 1
                if has_expected(retrieved_files[:3]):
                    total_r3 += 1
                if has_expected(retrieved_files[:5]):
                    total_r5 += 1

                # Calculate Reciprocal Rank
                rr = 0.0
                for rank, f_path in enumerate(retrieved_files, start=1):
                    if any(exp in f_path for exp in expected_files):
                        rr = 1.0 / rank
                        break
                total_rr += rr

            count = len(eval_questions)
            metrics[s]["recall_at_1"] = round(total_r1 / count, 4)
            metrics[s]["recall_at_3"] = round(total_r3 / count, 4)
            metrics[s]["recall_at_5"] = round(total_r5 / count, 4)
            metrics[s]["mrr"] = round(total_rr / count, 4)
            metrics[s]["avg_latency_ms"] = round(sum(latencies) / len(latencies), 2)
            metrics[s]["evaluated_queries"] = count

            print(
                f"[{s:16}] Recall@1: {metrics[s]['recall_at_1']:.2f} | "
                f"Recall@3: {metrics[s]['recall_at_3']:.2f} | "
                f"Recall@5: {metrics[s]['recall_at_5']:.2f} | "
                f"MRR: {metrics[s]['mrr']:.4f} | "
                f"Latency: {metrics[s]['avg_latency_ms']:6.2f}ms"
            )

        print("=" * 80)

        # Save evaluation results
        output_file = Path(__file__).parent / "evaluation_results.json"
        with open(output_file, "w") as out:
            json.dump(metrics, out, indent=2)
        print(f"Evaluation report saved to {output_file}")

    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()
