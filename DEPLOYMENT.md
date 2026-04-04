cce# Deployment Guide

This guide covers deploying the OmniPro 220 Expert to production.

## Option 1: Docker (Recommended)

### Local with Docker Compose

```bash
# Build and run locally
docker-compose up

# Backend will be at http://localhost:8000
# Frontend will be at http://localhost:3000
```

### Deploy to Cloud

#### Railway.app

1. Push code to GitHub
2. Create new project on railway.app
3. Connect GitHub repo
4. Add environment variable: `ANTHROPIC_API_KEY`
5. Set start command:
   ```
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app:app
   ```
6. Deploy

#### Fly.io

```bash
# Install CLI
curl -L https://fly.io/install.sh | sh

# Create app
fly launch

# Deploy
fly deploy
```

#### Heroku

```bash
# Install CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Create app
heroku create my-omnipro-expert

# Set environment
heroku config:set ANTHROPIC_API_KEY=sk-...

# Deploy
git push heroku main
```

## Option 2: Traditional Virtual Machine

### AWS EC2

```bash
# SSH into instance
ssh -i key.pem ec2-user@your-instance.amazonaws.com

# Clone repo
git clone <your-repo-url>
cd prox-challenge

# Setup
python3 -m venv venv
source venv/bin/activate
cd backend && pip install -r requirements.txt

# Extract knowledge
python scripts/extract.py

# Start with screen or systemd
screen -S omnipro
python app.py

# Or use systemd:
# Create /etc/systemd/system/omnipro.service
```

### DigitalOcean

Similar to EC2 - use their docs for initial setup, then follow AWS steps.

## Option 3: Serverless

Note: Serverless is NOT recommended for this project because:
- Knowledge base stays in memory (expensive to load per request)
- Streaming responses need persistent connections
- Better to use traditional containerization

If you must use serverless, consider Lambda + RDS to persist state.

## Environment Variables

```
ANTHROPIC_API_KEY      # Required - your Anthropic API key
MODEL                  # Optional - defaults to claude-3-5-sonnet-20241022
MAX_TOKENS             # Optional - defaults to 8096
PORT                   # Optional - defaults to 8000
```

## Production Checklist

- [ ] Set `DEBUG = False` in config
- [ ] Use production Anthropic API key (not test)
- [ ] Enable CORS only for your frontend domain
- [ ] Use SSL/TLS (HTTPS)
- [ ] Set up monitoring/alerting
- [ ] Enable logging
- [ ] Test with real PDFs
- [ ] Load testing
- [ ] Backup knowledge base
- [ ] Set up CI/CD pipeline

## Health Monitoring

```bash
# Check backend status
curl https://your-backend.com/api/health
```

Response:
```json
{
  "status": "ok",
  "knowledge_loaded": true,
  "chunks_count": 150,
  "images_count": 25
}
```

## Scaling Considerations

### Current Limits
- Single backend instance can handle ~100 concurrent users
- Knowledge base: ~150 chunks + 25 images = ~10MB memory
- API calls: ~$0.01-0.05 per user query

### To Scale
1. **Multiple Instances**
   - Use load balancer (nginx, HAProxy)
   - Share knowledge base via shared storage
   - Session affinity recommended

2. **Database**
   - Store conversation history
   - Cache frequently asked questions
   - Analytics

3. **Caching**
   - Cache tool responses
   - Redis for session storage
   - CDN for static content

4. **Async Workers**
   - Use Celery for long-running extraction jobs
   - Queue incoming messages during spikes

## Troubleshooting

### Backend won't start
```
Error: ANTHROPIC_API_KEY not set
```
Make sure environment variable is set: `export ANTHROPIC_API_KEY=sk-...`

### Knowledge base loading fails
```
Error loading knowledge base
```
Ensure `backend/knowledge/data/` directory exists and has correct JSON files.

### API responses slow
- Check internet connection to Anthropic API
- Monitor token usage
- Consider response caching

### Frontend can't reach backend
- Check CORS headers
- Verify backend is running and accessible
- Check firewall rules

## Monitoring & Logs

### Backend Logs
```bash
# View logs
tail -f backend.log

# Or with Docker
docker-compose logs -f backend
```

### Key Metrics
- API response time
- Claude API calls (count, tokens, cost)
- Knowledge base query performance
- User engagement

### Error Tracking
- Set up Sentry for error reporting
- CloudWatch / DataDog for monitoring
- Slack alerts for failures

## Backup & Recovery

### Backup knowledge base
```bash
tar -czf omnipro-kb-backup.tar.gz backend/knowledge/data/
```

### Restore
```bash
tar -xzf omnipro-kb-backup.tar.gz
```

## Updates & Maintenance

### Update dependencies
```bash
pip install --upgrade -r backend/requirements.txt
```

### Re-extract knowledge from PDFs
```bash
python backend/scripts/extract.py
```

### Rolling updates (zero downtime)
1. Deploy new version to separate instance
2. Point load balancer to new instance
3. Drain old instance connections
4. Stop old instance

---

## Cost Estimation

### API Costs
- **Knowledge Extraction**: ~$0.10 (one-time per set of PDFs)
- **Per User Query**: $0.01-0.05 average
- **100 queries/month**: $1-5/month

### Infrastructure
- **Docker**: Free to ~$5/month (small instance)
- **Railway/Fly**: $5-20/month
- **AWS/DigitalOcean**: $5-50/month depending on traffic

### Total
Typical small deployment: $10-50/month

---

## Getting Help

- Check [README_IMPLEMENTATION.md](README_IMPLEMENTATION.md) for architecture details
- Review logs for specific errors
- Test locally with [QUICKSTART.md](QUICKSTART.md) first
- Check deployment provider's documentation
