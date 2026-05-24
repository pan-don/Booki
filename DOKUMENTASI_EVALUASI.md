# MODUL EVALUASI DAN QUALITY ASSURANCE

**Dokumentasi Teknis: RAGAS Metrics, Precision@K, dan Performance Testing**

---

## Ikhtisar

Modul evaluasi mengukur kualitas RAG system menggunakan:
1. **RAGAS Metrics**: Faithfulness, answer relevancy, context precision
2. **Precision@K**: Akurasi rekomendasi vs ground truth
3. **Performance Testing**: Latency, throughput, resource usage

---

## 📁 Folder: `evaluation/`

**Fungsi**: Comprehensive evaluation framework untuk RAG performance assessment.

---

### File: `ragas.py`

**Tujuan**: Implementasi RAGAS (Retrieval-Augmented Generation Assessment) metrics.

#### Kelas: `RagasEvaluator`

```python
class RagasEvaluator:
    """
    Evaluates RAG system menggunakan RAGAS metrics.
    Requires: ragas, datasets, langchain-google-genai libraries
    """
    
    AVAILABLE_METRICS = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "answer_correctness": answer_correctness,
        "answer_similarity": answer_similarity,
    }
```

**Initialization**:
```python
evaluator = RagasEvaluator(
    model_name="gemini-1.5-flash",
    embedding_model="models/text-embedding-004",
    metrics=["faithfulness", "answer_relevancy"],
    retriever=retriever,
    reranker=reranker,
    answer_generator=answer_generator,
    max_samples=100
)
```

---

#### RAGAS Metrics Definitions

| Metrik | Deskripsi | Rentang | Interpretasi |
|--------|-----------|---------|--------------|
| **Faithfulness** | Seberapa factual jawaban terhadap retrieved context | 0-1 | Tinggi = jawaban akurat per context |
| **Answer Relevancy** | Seberapa relevant jawaban terhadap pertanyaan | 0-1 | Tinggi = jawaban sesuai intent user |
| **Context Precision** | Seberapa banyak context item yang relevan di top-k | 0-1 | Tinggi = minimal noise dalam retrieval |
| **Context Recall** | Seberapa banyak relevant context yang di-retrieve | 0-1 | Tinggi = comprehensive information |
| **Answer Correctness** | Akurasi jawaban vs ground truth (semantic) | 0-1 | Tinggi = jawaban correct secara semantic |
| **Answer Similarity** | Similarity jawaban vs reference answer | 0-1 | Tinggi = similar ke expected answer |

**Example Metric Scores**:
```
Ideal RAG system:
- Faithfulness: 0.85-0.95 (answers grounded dalam context)
- Answer Relevancy: 0.80-0.90 (answers relevant ke question)
- Context Precision: 0.75-0.85 (retrieved context mostly relevant)
- Context Recall: 0.70-0.80 (covers enough relevant content)
Overall Score: (0.85 + 0.85 + 0.80 + 0.75) / 4 = 0.81
```

---

#### Method: `evaluate()`

```python
def evaluate(
    self,
    eval_dataset: Dataset,  # dari ground_truth/
    metrics: Optional[List[str]] = None
) -> Dict[str, float]
```

**Fungsi**: Evaluate RAG system terhadap eval dataset menggunakan selected metrics.

**Input Dataset Format**:
```json
{
    "question": "Apa rumus gaya sentripetal?",
    "ground_truth": "F = m × v² / r adalah rumus gaya sentripetal",
    "reference_answer": "Gaya sentripetal adalah gaya yang menarik benda...",
    "contexts": [
        "Retrieved chunk 1 dari fulltext index",
        "Retrieved chunk 2 dari fulltext index"
    ]
}
```

**Processing Pipeline**:
```
For each sample dalam eval_dataset:
    1. Get question + contexts
    2. Generate answer menggunakan RAG pipeline
    3. Calculate metrics:
       - faithfulness(answer, contexts)
       - answer_relevancy(answer, question)
       - context_precision(relevant_items, retrieved_items)
       - context_recall(relevant_items, retrieved_items)
       - answer_correctness(answer, ground_truth)
       - answer_similarity(answer, reference_answer)
    4. Aggregate scores across all samples

Return:
{
    "faithfulness": 0.87,
    "answer_relevancy": 0.84,
    "context_precision": 0.82,
    "context_recall": 0.76,
    "answer_correctness": 0.89,
    "answer_similarity": 0.85,
    "overall_score": 0.84
}
```

---

### File: `precision_k.py`

**Tujuan**: Implementasi Precision@K metric untuk evaluasi recommendation quality.

#### Function: `precision_at_k()`

```python
def precision_at_k(
    recommended_books: List[str],  # book_ids dari recommendation result
    relevant_books: List[str],      # book_ids dari ground truth
    k: int = 5
) -> float
```

**Definisi**:
```
Precision@K = (# of relevant items dalam top-K recommendations) / K

Contoh:
recommended = ['book_1', 'book_2', 'book_3', 'book_4', 'book_5']
relevant = ['book_1', 'book_5', 'book_8', 'book_12']
precision@5 = 2 / 5 = 0.40  (books 1 dan 5 ada di top-5)
```

**Use Cases**:
- ✅ Evaluate `/recommend` endpoint accuracy
- ✅ Benchmark terhadap baseline recommendations
- ✅ Track performance improvements over time

---

#### Function: `recall_at_k()`

```python
def recall_at_k(
    recommended_books: List[str],
    relevant_books: List[str],
    k: int = 5
) -> float
```

**Definisi**:
```
Recall@K = (# of relevant items dalam top-K recommendations) / (total relevant items)

Contoh:
recommended = ['book_1', 'book_2', 'book_3', 'book_4', 'book_5']
relevant = ['book_1', 'book_5', 'book_8', 'book_12']  (4 total)
recall@5 = 2 / 4 = 0.50  (cover 50% dari relevant items)
```

---

#### Function: `mean_average_precision()`

```python
def mean_average_precision(
    recommendations_list: List[List[str]],  # Multiple recommendation results
    relevant_list: List[List[str]],         # Corresponding ground truth
    k: int = 5
) -> float
```

**Definisi**:
```
AP = (1/min(m, k)) × Σ P(i) × rel(i)
where m = # relevant items, k = recommendation top-k

MAP = mean(AP) across all queries
```

**Example**:
```
Query 1: precision@5 = 0.4 (2 relevant dalam 5)
Query 2: precision@5 = 0.6 (3 relevant dalam 5)
Query 3: precision@5 = 0.5 (2 relevant dalam 4, capped at k=5)

MAP@5 = (0.4 + 0.6 + 0.5) / 3 = 0.50
```

---

### File: `run_evaluation.py`

**Tujuan**: Script untuk menjalankan full evaluation pipeline dengan ground truth dataset.

#### Structure:

```python
if __name__ == "__main__":
    # 1. Load ground truth dataset
    eval_data = load_ground_truth_dataset("data/ground_truth/ragas_queries.jsonl")
    
    # 2. Initialize RAG components
    embedder = GeminiEmbedder()
    retriever = Retriever(summary_store, fulltext_store)
    reranker = Reranker()
    answer_generator = AnswerGenerator()
    
    # 3. Run RAGAS evaluation
    ragas_evaluator = RagasEvaluator(
        metrics=["faithfulness", "answer_relevancy", "context_precision"]
    )
    ragas_results = ragas_evaluator.evaluate(eval_data)
    
    # 4. Run Precision@K evaluation
    precision_evaluator = PrecisionEvaluator()
    precision_results = precision_evaluator.evaluate(eval_data)
    
    # 5. Generate report
    report = generate_evaluation_report(ragas_results, precision_results)
    save_report(report, "reports/evaluation_result.json")
    
    print(report)
```

---

## Ground Truth Dataset Format

### File: `data/ground_truth/ragas_queries.jsonl`

**Format**: JSONL (one JSON object per line)

**Schema**:
```json
{
    "id": "query_001",
    "query": "Apa rumus gaya sentripetal dan aplikasinya dalam kehidupan sehari-hari?",
    "reference_answer": "Gaya sentripetal adalah gaya yang bekerja pada benda yang bergerak melingkar...",
    "ground_truth": "F = m × v² / r dimana F adalah gaya sentripetal dalam Newton",
    "relevant_book_ids": ["book_123", "book_124"],
    "relevant_chunks": [
        {
            "book_id": "book_123",
            "chunk_id": "chunk_0",
            "chunk_text": "Gaya sentripetal adalah..."
        }
    ]
}
```

**Contoh Dataset**:
```jsonl
{"id": "q001", "query": "Fisika gelombang SMA", "relevant_book_ids": ["book_123", "book_456"], ...}
{"id": "q002", "query": "Matematika aljabar kelas 8", "relevant_book_ids": ["book_789"], ...}
{"id": "q003", "query": "IPA tumbuhan kelas 6 SD", "relevant_book_ids": ["book_111", "book_222"], ...}
```

---

## Evaluation Report Output

```json
{
    "timestamp": "2026-05-23T10:30:00Z",
    "dataset_size": 50,
    "metrics": {
        "ragas": {
            "faithfulness": {
                "mean": 0.87,
                "std": 0.08,
                "min": 0.65,
                "max": 0.98,
                "samples": 50
            },
            "answer_relevancy": {
                "mean": 0.84,
                "std": 0.10,
                "min": 0.52,
                "max": 0.96
            },
            "context_precision": {
                "mean": 0.82,
                "std": 0.11,
                "min": 0.40,
                "max": 1.00
            },
            "overall_ragas_score": 0.84
        },
        "precision": {
            "precision@5": {
                "mean": 0.76,
                "std": 0.18
            },
            "recall@5": {
                "mean": 0.68,
                "std": 0.20
            },
            "map@5": 0.72
        }
    },
    "performance": {
        "avg_latency_ms": 1240,
        "throughput_req_per_sec": 0.81
    }
}
```

---

## Performance Testing

### Latency Testing

```python
import time

def test_latency(num_queries=100):
    times = []
    for query in test_queries[:num_queries]:
        start = time.time()
        
        # Run full /recommend pipeline
        query_vector = embedder.embed_text(query)
        results = retriever.search_summary(query, query_vector)
        reranked = reranker.rerank_results(query, results)
        answer = answer_generator.generate_recommendation(query, reranked)
        
        elapsed = time.time() - start
        times.append(elapsed)
    
    return {
        "mean_latency": np.mean(times),
        "p50": np.percentile(times, 50),
        "p95": np.percentile(times, 95),
        "p99": np.percentile(times, 99),
        "min": np.min(times),
        "max": np.max(times)
    }

# Output:
# mean_latency: 1.24s
# p50: 1.15s
# p95: 1.65s
# p99: 1.89s
```

### Throughput Testing

```python
import concurrent.futures

def test_throughput(num_concurrent=5, duration_sec=60):
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = []
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_sec:
            query = random.choice(test_queries)
            future = executor.submit(make_recommendation_request, query)
            futures.append(future)
            request_count += 1
        
        # Wait for all to complete
        concurrent.futures.wait(futures)
    
    elapsed = time.time() - start_time
    throughput = request_count / elapsed
    return {"requests_per_sec": throughput, "total_requests": request_count}

# Output:
# requests_per_sec: 4.2
# total_requests: 252
```

---

## Best Practices

### Evaluation Strategy

1. ✅ **Regular Evaluation**: Run evaluation setelah significant code changes
2. ✅ **Baseline Comparison**: Track metrics over time untuk detect regressions
3. ✅ **Multi-Metric Assessment**: Jangan rely pada single metric
4. ✅ **Human Review**: Periodically review recommendations untuk qualitative assessment

### Ground Truth Creation

1. ✅ **Domain Expert Annotation**: Gunakan teacher/subject matter expert
2. ✅ **Quality Control**: Validate annotations untuk consistency
3. ✅ **Diverse Coverage**: Include queries dari different jenjang/mapel
4. ✅ **Version Control**: Track dataset versions untuk reproducibility

### Metric Interpretation

| Score | Interpretation | Action |
|-------|-----------------|--------|
| > 0.85 | Excellent | Monitor untuk potential issues |
| 0.70-0.85 | Good | Acceptable performance |
| 0.50-0.70 | Moderate | Needs improvement |
| < 0.50 | Poor | Investigate root cause |

---

