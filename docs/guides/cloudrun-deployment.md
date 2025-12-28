# Google Cloud Run Deployment Guide

Deploy Retriever to Google Cloud Run with Secret Manager.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI configured and authenticated
- Docker installed
- API keys ready:
  - OpenRouter API key ([get here](https://openrouter.ai/keys))
  - OpenAI API key ([get here](https://platform.openai.com/api-keys))

## Data Persistence Note

**Data is ephemeral** - SQLite and Chroma data reset when containers restart. This is acceptable for demos. For production, migrate to Cloud SQL and persistent storage.

---

## Step 1: Set Environment Variables

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
```

## Step 2: Enable APIs

```bash
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project="$PROJECT_ID"
```

## Step 3: Create Artifact Registry Repository

```bash
gcloud artifacts repositories create retriever \
    --repository-format=docker \
    --location="$REGION" \
    --description="Retriever container images" \
    --project="$PROJECT_ID"
```

## Step 4: Create Secrets

```bash
# Create secrets with placeholder values
echo -n "placeholder" | gcloud secrets create retriever-openrouter-api-key --data-file=- --project="$PROJECT_ID"
echo -n "placeholder" | gcloud secrets create retriever-openai-api-key --data-file=- --project="$PROJECT_ID"
echo -n "placeholder" | gcloud secrets create retriever-jwt-secret --data-file=- --project="$PROJECT_ID"
```

## Step 5: Update Secrets with Real Values

```bash
# OpenRouter API key
echo -n 'sk-or-v1-your-key-here' | gcloud secrets versions add retriever-openrouter-api-key --data-file=- --project="$PROJECT_ID"

# OpenAI API key
echo -n 'sk-your-key-here' | gcloud secrets versions add retriever-openai-api-key --data-file=- --project="$PROJECT_ID"

# JWT secret (generate random)
openssl rand -base64 32 | gcloud secrets versions add retriever-jwt-secret --data-file=- --project="$PROJECT_ID"
```

## Step 6: Grant Cloud Run Access to Secrets

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding retriever-openrouter-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID"

gcloud secrets add-iam-policy-binding retriever-openai-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID"

gcloud secrets add-iam-policy-binding retriever-jwt-secret \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID"
```

## Step 7: Build Container Image

```bash
docker build --platform linux/amd64 -t $REGION-docker.pkg.dev/$PROJECT_ID/retriever/retriever:latest .
```

## Step 8: Authenticate Docker with Artifact Registry

```bash
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin $REGION-docker.pkg.dev
```

## Step 9: Push Image

```bash
docker push $REGION-docker.pkg.dev/$PROJECT_ID/retriever/retriever:latest
```

## Step 10: Deploy to Cloud Run

```bash
gcloud run deploy retriever \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/retriever/retriever:latest \
    --region $REGION \
    --project $PROJECT_ID \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 60 \
    --concurrency 80 \
    --set-env-vars "DEBUG=false,AUTH_ENABLED=true,SAFETY_ENABLED=true,CACHE_ENABLED=true,HYBRID_RETRIEVAL_ENABLED=true" \
    --set-secrets "OPENROUTER_API_KEY=retriever-openrouter-api-key:latest,EMBEDDING_API_KEY=retriever-openrouter-api-key:latest,OPENAI_API_KEY=retriever-openai-api-key:latest,JWT_SECRET_KEY=retriever-jwt-secret:latest"
```

## Step 11: Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe retriever --region $REGION --project $PROJECT_ID --format="value(status.url)")
echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl $SERVICE_URL/health
```

## Step 12: Create Admin User

```bash
curl -X POST "${SERVICE_URL}/auth/register" \
    -H "Content-Type: application/json" \
    -d '{
      "email": "admin@example.com",
      "password": "your-secure-password",
      "is_admin": true
    }'
```

---

## Redeployment

After code changes, repeat steps 7-10:

```bash
docker build --platform linux/amd64 -t $REGION-docker.pkg.dev/$PROJECT_ID/retriever/retriever:latest .
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin $REGION-docker.pkg.dev
docker push $REGION-docker.pkg.dev/$PROJECT_ID/retriever/retriever:latest
gcloud run deploy retriever \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/retriever/retriever:latest \
    --region $REGION \
    --project $PROJECT_ID
```

---

## Useful Commands

```bash
# View logs
gcloud run services logs read retriever --region $REGION --project $PROJECT_ID --limit 50

# Get service URL
gcloud run services describe retriever --region $REGION --project $PROJECT_ID --format="value(status.url)"

# Delete service
gcloud run services delete retriever --region $REGION --project $PROJECT_ID

# Update a secret
echo -n 'new-value' | gcloud secrets versions add retriever-openrouter-api-key --data-file=- --project=$PROJECT_ID
```

---

## Cost Estimate

Cloud Run free tier includes:
- 2M requests/month
- 360,000 GB-seconds/month

Estimated monthly cost for demo workload: **$5-15**

Scales to zero when idle (no cost).
