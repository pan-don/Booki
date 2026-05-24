# LAYER GENERASI JAWABAN

**Dokumentasi Teknis: LLM-Based Answer Generation dengan Guardrails**

---

## Ikhtisar

Layer generasi menggunakan Large Language Models (LLM) untuk:
1. **Recommendation Generation**: Membuat jawaban rekomendasi buku yang personal
2. **Answer Generation**: Menjawab pertanyaan spesifik dengan konteks dari chunks
3. **Personalization**: Mengadaptasi tone dan language untuk audience (SD-SMA)
4. **Guardrails**: Menolak pertanyaan non-edukatif atau berbahaya

---

## 📁 Folder: `generation/`

**Fungsi**: Pembuatan jawaban akhir menggunakan LLM dengan context-aware prompting.

---

### File: `answer_generator.py`

**Tujuan**: Wrapper around Google Gemini API untuk intelligent answer generation.

#### Kelas: `AnswerGenerator`

```python
class AnswerGenerator:
    """
    Generates answers menggunakan Google Gemini API.
    Supports both recommendations dan detailed Q&A dengan context.
    """
    
    def __init__(
        self,
        api_key_manager: Optional[APIKeyManager] = None,
        model: str = "gemini-2.5-pro",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 1000
    )
```

**Initialization Parameters**:

| Parameter | Type | Default | Deskripsi |
|-----------|------|---------|-----------|
| `api_key_manager` | Optional[APIKeyManager] | Auto-created | Manager untuk Gemini API keys |
| `model` | str | `gemini-2.5-pro` | Model identifier untuk answer generation |
| `system_prompt` | str | DEFAULT_SYSTEM_PROMPT | System prompt untuk personalization |
| `temperature` | float | 0.7 | Sampling temperature (0.0-1.0) |
| `max_tokens` | int | 1000 | Maximum tokens dalam response |

**System Prompt** (DEFAULT_SYSTEM_PROMPT):
```
Anda adalah asisten pintar untuk Sistem Rekomendasi & Eksplorasi Buku Pelajaran. 
Anda sangat ramah, suportif, kreatif, ceria, dan menyenangkan! 
Gaya bahasa Anda disesuaikan untuk anak-anak sekolah dan remaja (SD, SMP, SMA).

Gunakan bahasa Indonesia yang baku namun santai, 
selipkan pujian penyemangat (contoh: "Wah, pertanyaan yang bagus sekali, Sobat Belajar!"), 
dan gunakan emoticon sewajarnya (📚, ✨, 🚀, 😊) untuk menghidupkan suasana.

GUARDRAILS:
1. Fokus hanya pada materi pendidikan, buku pelajaran, ilmu pengetahuan, 
   dan rekomendasi bahan bacaan.
2. TOLAK SECARA HALUS jika pertanyaan:
   - Tidak relevan dengan dunia pendidikan atau buku pelajaran
   - Mengandung unsur SARA
   - Terkait dengan politik, kekerasan, pornografi, peretasan
   - Bersifat provokasi, cyberbullying, atau berkata kasar
   
   Cara menolak: "Maaf ya, teman! Aku dirancang khusus untuk membantu kamu 
   mengeksplorasi buku pelajaran dan ilmu pengetahuan. Yuk, kita kembali bahas 
   buku atau materi sekolah saja! 📚✨"

3. Jangan berhalusinasi. Jika informasi tidak ada dalam konteks, 
   beritahu pengguna dengan jujur.
4. Jawab rapi menggunakan paragraf pendek atau poin-poin agar mudah dibaca.
```

---

#### Method: `generate_recommendation()`

```python
def generate_recommendation(
    self,
    user_query: str,
    retrieved_books: List[Dict[str, Any]]
) -> str
```

**Fungsi**: Generate friendly recommendation answer berdasarkan top-5 reranked books.

**Parameters**:
- `user_query`: Original query dari user
- `retrieved_books`: Top-5 books dari retriever + reranker (with metadata)

**Return**: Recommendation answer text (string, 200-300 words)

**Prompt Template**:
```
Based on this user query: "{user_query}"

Here are the top recommended books:

[For each book]:
- {title} ({jenjang}, Kelas {kelas})
  Mata Pelajaran: {mata_pelajaran}
  Ringkasan: {summary_text}

Please generate a friendly, encouraging recommendation response in Indonesian:
1. Acknowledge the user's learning interests
2. Explain why these books are good matches
3. Suggest how to use these books (read cover-to-cover, reference, practice)
4. Encourage them to explore and learn!

Keep the tone friendly, use encouraging phrases like "Wah, bagus sekali!", 
and add relevant emojis.
```

**Example Output**:
```
Wah, pertanyaan yang bagus sekali, Sobat Belajar! 📚✨

Saya menemukan 5 buku yang sangat cocok untuk kamu:

🌟 Fisika SMA Kelas X - Tim Gemilang
Ini adalah buku fisika yang komplit untuk kelas X SMA. Buku ini menjelaskan 
konsep-konsep dasar fisika dengan cara yang mudah dipahami. Cocok banget 
untuk mempersiapkan ujian atau belajar mandiri!

🌟 Sains Terpadu SMA Kelas X - Penerbit Erlangga
...

Saran saya: Mulai dari buku pertama yang paling relevan dengan topik yang 
kamu minati, baca dengan teliti, dan jangan ragu untuk mengulangi bagian 
yang sulit. Semangat! 🚀
```

---

#### Method: `generate_deep_answer()`

```python
def generate_deep_answer(
    self,
    user_question: str,
    selected_books: List[Dict[str, Any]],
    retrieved_chunks: List[Dict[str, Any]]
) -> str
```

**Fungsi**: Generate detailed answer untuk specific question menggunakan retrieved chunks sebagai context.

**Parameters**:
- `user_question`: Detailed question dari user
- `selected_books`: Metadata dari 1-5 selected books
- `retrieved_chunks`: Top-5 most relevant chunks dengan chunk_text

**Return**: Detailed answer text dengan source references

**Prompt Template**:
```
User Question: "{user_question}"

Selected Books: {book_titles}

Relevant Context from Books:
[For each chunk]:
---
{chunk_text}
---

Please provide a detailed, educational answer based on the context above:
1. Answer the question directly and thoroughly
2. Use examples from the provided context
3. Explain in simple terms suitable for {jenjang} level
4. If information is not in the context, say "Informasi ini tidak tersedia 
   dalam buku yang dipilih"
5. Add relevant emojis and encouraging language

Keep the response 150-300 words and well-structured with paragraphs.
```

**Example Output**:
```
Pertanyaan bagus, Sobat Belajar! 🤔

Gaya sentripetal adalah gaya yang menarik benda menuju pusat lingkaran 
ketika benda bergerak melingkar. Rumus gaya sentripetal adalah:

F_s = m × v² / r

Dimana:
- F_s = gaya sentripetal (Newton)
- m = massa benda (kg)
- v = kecepatan linier (m/s)
- r = jari-jari lingkaran (m)

Contoh dari Fisika SMA Kelas X:
Jika sebuah bola dengan massa 0.5 kg bergerak melingkar dengan kecepatan 4 m/s 
dalam lingkaran berjari-jari 2 m, maka:
F_s = 0.5 × (4²) / 2 = 0.5 × 16 / 2 = 4 Newton

Sekarang kamu sudah tahu rumusnya! Coba praktikkan di soal-soal lain ya! 💪
```

---

#### Method: `_call_gemini()`

```python
def _call_gemini(self, messages: List[Dict[str, str]]) -> Optional[str]
```

**Internal Method**: Make API call ke Google Gemini dengan error handling.

**Parameters**:
- `messages`: List of message dicts `{'role': 'user'|'assistant'|'system', 'content': 'text'}`

**Return**: Generated text atau None jika error

**Implementation Details**:
```python
def _call_gemini(self, messages):
    try:
        # Combine system prompt + user message
        full_prompt = f"{self.system_prompt}\n\n{messages[-1]['content']}"
        
        # Call Gemini API
        response = self.client.generate_content(
            contents=full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )
        )
        
        if response.text:
            return response.text
        else:
            return None
            
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        # Try fallback key rotation
        self.api_key_manager.report_error(current_key, str(e))
        return None
```

**Error Handling**:
- ✅ API timeout (retry dengan backoff)
- ✅ Rate limiting (rotate API keys)
- ✅ Invalid input (log dan return None)
- ✅ Network errors (graceful fallback)

---

## Personalization & Tone Adaptation

### Jenjang-Based Personalization

| Jenjang | Vocabulary | Example Phrases | Complexity |
|---------|-----------|-----------------|-----------|
| SD/MI | Simple, concrete | "Halo teman!", "Asyik!", "Mudah sekali!" | Basic concepts |
| SMP/MTs | Intermediate | "Bagus sekali pertanyaanmu!", "Konsep penting ini", "Coba praktek" | Intermediate theory |
| SMA/MA/SMK | Advanced | "Analisis yang mendalam", "Komponen utama", "Penerapan praktis" | Advanced concepts |

### Tone & Style Elements

```python
ENCOURAGING_PHRASES = [
    "Wah, pertanyaan yang bagus sekali!",
    "Semangat terus belajarnya!",
    "Konsep ini penting untuk dipahami",
    "Excellent! Kamu sudah paham konsepnya",
    "Jangan menyerah, terus semangat!"
]

RELEVANT_EMOJIS = {
    'science': '🔬',
    'math': '📐',
    'language': '📖',
    'history': '📜',
    'success': '✨',
    'motivation': '🚀',
    'learning': '📚'
}
```

---

## Guardrails & Safety Mechanisms

### Content Filtering

```
DANGEROUS_KEYWORDS = [
    'peretasan', 'hacking', 'exploits',
    'kekerasan', 'violence',
    'pornografi', 'adult content',
    'SARA', 'suku agama ras',
    'politik', 'politics',
    'cyberbullying', 'bullying'
]

def check_safety(text):
    if any(keyword in text.lower() for keyword in DANGEROUS_KEYWORDS):
        return False  # Unsafe
    return True
```

### Rejection Response Template

```python
REJECTION_MESSAGE = """
Maaf ya, teman! Aku dirancang khusus untuk membantu kamu mengeksplorasi 
buku pelajaran dan ilmu pengetahuan. 

Yuk, kita kembali bahas buku atau materi sekolah saja! 📚✨

Ada pertanyaan lain tentang pelajaran atau buku yang ingin kamu tanyakan?
"""
```

### Hallucination Prevention

```python
# Check if context supports the answer
if retrieved_chunks is empty or insufficient:
    response = "Maaf, informasi ini tidak tersedia di dalam buku yang 
    kamu pilih. Coba pertanyaan lain atau pilih buku berbeda ya! 😊"
```

---

## Integration dalam RAG Pipeline

### Recommendation Flow

```
Top 5 Books dari Reranker
    ↓
AnswerGenerator.generate_recommendation(query, books)
    ↓
LLM Call (Gemini 2.5 Pro)
    ↓
Recommendation Answer (200-300 words)
    ↓
Return to API endpoint
```

### Deep Dive Flow

```
Selected Books + Question
    ↓
Top 5 Chunks dari Reranker
    ↓
AnswerGenerator.generate_deep_answer(question, books, chunks)
    ↓
LLM Call dengan context
    ↓
Detailed Answer (150-300 words) + Source References
    ↓
Return to API endpoint
```

---

## Performance & Cost Optimization

### Token Usage Estimation

| Operation | Input Tokens | Output Tokens | Total |
|-----------|--------------|---------------|-------|
| Recommendation (5 books) | 800 | 250 | 1050 |
| Deep dive (5 chunks) | 1500 | 200 | 1700 |
| Average per request | 1000 | 200 | 1200 |

### Cost per Request

```
Gemini 2.5 Pro pricing (as of May 2026):
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens

Cost per recommendation: ~0.09 cents
Cost per deep dive: ~0.15 cents
```

### Optimization Strategies

1. ✅ Use `max_tokens=1000` untuk limit output size
2. ✅ Cache similar responses (jika user asks same question)
3. ✅ Batch multiple requests dalam single API call (jika applicable)
4. ✅ Monitor token usage untuk cost tracking

---

## Best Practices

### Prompting

1. ✅ **Clear instruction**: Explicit about what model should do
2. ✅ **System prompt**: Define role, tone, boundaries
3. ✅ **Examples**: Provide example outputs untuk better guidance
4. ✅ **Constraints**: Set clear output format (word count, structure)

### Error Handling

1. ✅ **Graceful degradation**: Return meaningful fallback jika API fails
2. ✅ **User transparency**: Tell user jika dapat't find info
3. ✅ **Logging**: Log all API calls untuk debugging
4. ✅ **Retry logic**: Exponential backoff untuk transient errors

### Safety

1. ✅ **Input validation**: Check user query untuk safety before API call
2. ✅ **Output filtering**: Validate response before returning to user
3. ✅ **Guardrails**: Implement explicit rejection for unsafe content
4. ✅ **Monitoring**: Alert pada suspicious patterns

---

