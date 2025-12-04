# Phase 3: Cloud Deployment

## Overview

**Goal:** Deploy Greg to the cloud so it's accessible without local setup.

**Status:** Pending

**Why This Matters:**
- Portfolio pieces need live demos
- "Here's the link" beats "clone this repo and run 12 commands"
- Forces handling of production concerns (secrets, persistence)

---

## Deployment Options

| Platform | Pros | Cons | Cost |
|----------|------|------|------|
| **Hugging Face Spaces** | Free, ML-focused | Limited compute, cold starts | Free |
| **Railway** | Simple, good DX | Starts at $5/mo | $5+/mo |
| **Render** | Free tier available | Cold starts on free | Free-$7/mo |
| **Fly.io** | Fast, global | More complex setup | $0-5/mo |

**Recommendation:** Start with Hugging Face Spaces (free, ML-native).

---

## Tasks

### 1. Prepare for Deployment

- [ ] Create deployment-ready app version
- [ ] Handle secrets via environment variables
- [ ] Add health check endpoint
- [ ] Create deployment requirements.txt

### 2. Handle Persistence

Options:
- **Accept ephemerality** - Users re-upload each session (simplest)
- **Use HF Datasets** - Store indexes in Hugging Face
- **Add database** - PostgreSQL for metadata (Railway/Render)

### 3. Deploy

- [ ] Set up Hugging Face Space (or alternative)
- [ ] Configure secrets (API keys)
- [ ] Test document upload and Q&A
- [ ] Verify cost tracking works

### 4. Monitor

- [ ] Add logging
- [ ] Set up cost alerts
- [ ] Monitor health checks

---

## Key Considerations

### Secrets Management

Never commit secrets. Use platform-specific secret management:
- HF Spaces: Settings → Repository secrets
- Railway: `railway variables set KEY=value`
- Render: Dashboard → Environment

### Cost Protection

```python
DAILY_LIMIT = 5.00  # $5/day

def check_cost_limit():
    today_cost = tracker.get_today_cost()
    if today_cost > DAILY_LIMIT:
        # Switch to cheaper model or disable API
        pass
```

---

## Learning Objectives

After completing this phase, you should understand:

- How to handle secrets in cloud deployments
- Difference between ephemeral and persistent storage
- How to monitor a deployed ML application
- Tradeoffs between deployment platforms

---

## Success Criteria

- [ ] App accessible via public URL
- [ ] API keys configured as secrets
- [ ] Document upload and Q&A works
- [ ] Cost tracking functional
- [ ] README updated with demo link

---

## Next Phase

→ After deployment, proceed to **PHASE_4_ADVANCED_RAG.md** for advanced features.
