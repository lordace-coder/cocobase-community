# AI Assistant Optimization Guide

## Current Status ✅
- **Updated**: System prompt now clearly states NO IMPORTS needed
- **Libraries**: Documented all pre-imported libraries (json, datetime, math, re, uuid, hashlib)
- **Token Usage**: Reduced from 22,456 to 2,250 tokens (90% reduction)
- **Documentation**: Optimized to only load essential docs

## 3 Ways to Make It Faster & Cheaper

### **Option 1: Fine-tuning (Best Quality)** ⭐

**Benefits:**
- No need to send documentation every request
- 10x faster responses
- More consistent output
- Lower cost per request

**Cost:**
- Training: ~$0.008/1K tokens (one-time)
- Inference: ~$0.012/1K tokens (vs $0.15/1K for base model)

**Steps:**
```bash
# 1. Generate training data
python app/services/ai_assistant/training_data_generator.py

# 2. Upload and fine-tune (requires OpenAI API key)
openai api fine_tunes.create \
  -t training_data.jsonl \
  -m gpt-4o-mini \
  --suffix "cocobase-cloud-functions"

# 3. Use fine-tuned model
# Update .env:
AI_PROVIDER=openai
OPENAI_API_KEY=your_key
AI_MODEL=ft:gpt-4o-mini:your-org:cocobase-cloud-functions:xxxxx
```

**Add more training examples:**
Edit `training_data_generator.py` and add more examples to the `examples` list.

---

### **Option 2: Embeddings + RAG (Most Flexible)** 🔍

**Benefits:**
- Only sends relevant docs per request
- Easy to update documentation
- Works with any model

**Cost:**
- Embeddings: $0.0001/1K tokens (one-time per doc)
- Storage: Free (local) or $70/month (Pinecone)
- Queries: Only pay for retrieved content

**Implementation:**
```python
# Install dependencies
pip install chromadb sentence-transformers

# Create vector database
from chromadb import Client
from chromadb.utils import embedding_functions

# Initialize
client = Client()
collection = client.create_collection("cocobase_docs")

# Add documents
collection.add(
    documents=[doc1, doc2, doc3],
    ids=["doc1", "doc2", "doc3"]
)

# Query relevant docs
results = collection.query(
    query_texts=["how to query users"],
    n_results=2
)
# Only send these 2 relevant docs to AI!
```

---

### **Option 3: Prompt Caching (Easiest)** ⚡

**Benefits:**
- Zero code changes needed
- 90% savings on repeated prompts
- Works with current setup

**Available in:**
- ✅ Anthropic Claude (already has caching)
- ⚠️ OpenAI (beta, not in OpenRouter)
- ✅ Groq (automatic caching)

**To use with Anthropic Claude:**
```bash
# Update .env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key
AI_MODEL=claude-3-5-sonnet-20241022
```

**Current provider (OpenRouter) doesn't support caching, but Groq does!**
```bash
# Use Groq (free + has automatic caching)
AI_PROVIDER=groq
GROQ_API_KEY=your_key
AI_MODEL=llama-3.3-70b-versatile
```

---

## Recommended Approach

### **For Development/Testing:**
Use current setup with OpenRouter free models
- ✅ No cost
- ✅ Works now
- ⚠️ Slower, uses more tokens

### **For Production (Low Budget):**
Use Groq with automatic caching
```bash
AI_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxx
AI_MODEL=llama-3.3-70b-versatile
```
- ✅ FREE
- ✅ Fast (very fast inference)
- ✅ Automatic caching
- ⚠️ Rate limits (generous)

### **For Production (Best Quality):**
Fine-tune GPT-4o-mini
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxx
AI_MODEL=ft:gpt-4o-mini:org:cocobase:xxxxx
```
- ✅ Best quality
- ✅ Fastest responses
- ✅ Lowest token usage
- 💰 ~$2-5/month for typical usage

---

## Current Configuration

**Docs loaded (9,000 chars):**
- quick-reference.md (3,000 chars)
- database-api.md (3,000 chars)
- README.md (3,000 chars)

**System prompt:**
- ✅ States NO IMPORTS allowed
- ✅ Lists all pre-imported libraries
- ✅ Emphasizes key rules

**Token usage per request:**
- System prompt: ~2,250 tokens
- User message: ~50-200 tokens
- Response: ~500-1,500 tokens
- **Total: ~3,000-4,000 tokens/request**

---

## Quick Wins (Immediate)

1. **Switch to Groq** (free + fast)
   ```bash
   AI_PROVIDER=groq
   GROQ_API_KEY=gsk_xxxxx
   AI_MODEL=llama-3.3-70b-versatile
   ```

2. **Reduce docs further** (if needed)
   Edit `bot.py` line 29:
   ```python
   if len(content) > 2000:  # Reduced from 3000
   ```

3. **Cache on client side**
   Store recent responses in Redis/memory to avoid duplicate requests

---

## Measuring Success

Track these metrics:
- **Response time**: Target < 3 seconds
- **Token usage**: Target < 3,000 tokens/request
- **Cost**: Target < $0.01/request
- **Quality**: User satisfaction, code works first try

Current performance:
- ⚠️ Response time: 5-10s (OpenRouter free tier)
- ✅ Token usage: ~3,000 tokens/request
- ✅ Cost: FREE (OpenRouter)
- ❓ Quality: To be measured

---

## Next Steps

1. ✅ Updated system prompt (DONE)
2. ⏭️ Switch to Groq when available
3. ⏭️ Generate more training examples
4. ⏭️ Fine-tune model (optional, for production)
5. ⏭️ Implement RAG (optional, for large docs)

---

## Questions?

- **"Should I fine-tune?"** → If you have budget and want best quality, yes!
- **"Should I use RAG?"** → If docs grow beyond 10K chars, yes!
- **"What's the cheapest?"** → Groq (free) with current setup
- **"What's the fastest?"** → Fine-tuned GPT-4o-mini
- **"What's easiest?"** → Keep current setup, switch to Groq
