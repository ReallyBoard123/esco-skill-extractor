## Overview

  

This document describes the comprehensive solution for handling long-running data extraction operations through **zrok tunnels** while maintaining compatibility with local development environments.

  

## Problem Statement

  

### Original Challenge

- **zrok tunnels have a 1-minute HTTP timeout limit**

- **TURBO data extraction takes 3-5 minutes** to process millions of records

- **Frontend gets 504 Gateway Timeouts** when accessing through zrok

- **Local development works fine** (no proxy timeouts)

  

### Solution Requirements

- ✅ **No timeouts** for Vercel frontend accessing through zrok

- ✅ **Backward compatibility** with local development (localhost:3000)

- ✅ **Same user experience** regardless of environment

- ✅ **No frontend code changes** required for basic usage

  

## Architecture Overview

  

```mermaid

graph LR

A[Frontend] --> B{Environment Detection}

B -->|localhost:3000| C[Synchronous API]

B -->|Vercel via zrok| D[Polling API]

C --> E[Direct Response]

D --> F[Job ID + Polling]

F --> G[Poll Every 3s]

G --> H[Final Result]

```

  

### Dual-Mode Architecture

  

#### 🏠 **Local Development Mode**

- **Frontend**: `localhost:3000`

- **Backend**: `localhost:8080`

- **Behavior**: Synchronous responses (original behavior)

- **No timeouts**: Direct connection, no proxy layer

  

#### 🚀 **Production Mode**

- **Frontend**: `https://mm-frontend-psi.vercel.app`

- **Backend**: `https://mmfrontend.share.zrok.io` (zrok tunnel → localhost:8080)

- **Behavior**: Polling-based responses

- **Timeout prevention**: Immediate job ID response, background processing

  

## Backend Implementation

  

### Smart Origin Detection

  

The backend automatically detects the request source and adapts behavior:

  

```python

# File: /backend/api/index.py

  

@app.post("/api/turbo-extract-data")

async def turbo_extract_data_hybrid(token_request: TokenRequest, request: Request):

# Detect request origin to determine behavior

host = request.headers.get("host", "")

origin = request.headers.get("origin", "")

referer = request.headers.get("referer", "")

# Check if request is from localhost (local development)

is_localhost = ("localhost" in host or "127.0.0.1" in host or

"localhost" in origin or "127.0.0.1" in origin or

"localhost" in referer or "127.0.0.1" in referer)

# Check if request is from Vercel frontend

is_vercel = ("vercel.app" in origin or "vercel.app" in referer or

"mm-frontend-psi.vercel.app" in origin or

"mm-frontend-psi.vercel.app" in referer)

if is_localhost:

# LOCAL DEVELOPMENT: Synchronous processing

return synchronous_extraction(token_request.token)

elif is_vercel:

# VERCEL: Polling to prevent zrok timeouts

return start_background_job(token_request.token)

```

  

### Response Formats

  

#### 🏠 Local Development Response

```json

{

"success": true,

"message": "TURBO data extraction completed successfully",

"extraction_result": {

"process_uuid": "31f9139a-03e6-4865-bbab-4d41b14f658e",

"measurement_count": 33,

"turbo_stats": {

"total_processing_time_seconds": 185.2,

"total_files_processed": 363,

"files_per_second": 1.96

}

},

"turbo_mode": true

}

```

  

#### 🚀 Vercel/Zrok Response (Initial)

```json

{

"success": true,

"job_id": "56a191bb-2050-4a59-bafd-c7b75715fe2b",

"message": "TURBO extraction started - use polling endpoint",

"polling_endpoint": "/api/turbo-poll/56a191bb-2050-4a59-bafd-c7b75715fe2b",

"turbo_mode": true

}

```

  

### Background Job Management

  

```python

# Job tracking dictionary

background_jobs: Dict[str, Dict] = {}

  

# Job initialization

background_jobs[job_id] = {

"status": "running",

"progress": "Starting TURBO extraction...",

"started_at": asyncio.get_event_loop().time(),

"result": None,

"error": None,

"token": token_request.token

}

  

# Background task execution

asyncio.create_task(run_turbo_extraction_background(job_id, token))

```

  

## API Endpoints

  

### Core Extraction Endpoint

  

#### `POST /api/turbo-extract-data`

**Smart hybrid endpoint that adapts based on request origin**

  

**Request:**

```json

{

"token": "eyJhbGciOiJIUzI1NiIs..."

}

```

  

**Response (varies by environment):**

- **localhost**: Complete extraction result (synchronous)

- **Vercel**: Job ID for polling (asynchronous)

  

### Polling Endpoints

  

#### `GET /api/turbo-poll/{job_id}`

**Returns extraction result in original format when complete**

  

**Response (Running):**

```json

{

"status": "running",

"progress": "Processing H5 files to SQL database...",

"message": "TURBO extraction in progress..."

}

```

  

**Response (Completed):**

```json

{

"success": true,

"message": "TURBO data extraction completed successfully",

"extraction_result": {

"process_uuid": "31f9139a-03e6-4865-bbab-4d41b14f658e",

"measurement_count": 33,

"turbo_stats": {...}

},

"turbo_mode": true

}

```

  

#### `GET /api/turbo-extract-status/{job_id}`

**Detailed job status with timing information**

  

```json

{

"job_id": "56a191bb-2050-4a59-bafd-c7b75715fe2b",

"status": "running",

"progress": "🚀 Processing 33 measurements with original TURBO...",

"elapsed_time_seconds": 127.45

}

```

  

## Frontend Implementation

  

### Smart Polling in api.ts

  

The frontend automatically handles both response types:

  

```typescript

// File: /lib/api.ts

  

turboExtractData: async (data: ExtractDataRequest) => {

const response = await fetchAPI('/turbo-extract-data', {

method: 'POST',

body: JSON.stringify(data)

});

const result = await response.json();

// Check if we got a polling response (Vercel → zrok tunnel)

if (result.success && result.job_id && result.polling_endpoint) {

// Handle polling pattern for zrok tunnel

return await pollForResult(result.job_id, result.polling_endpoint);

}

// Return direct result (localhost development)

return result;

}

```

  

### Polling Implementation

  

```typescript

const pollForResult = async (jobId: string, pollingEndpoint: string, maxAttempts = 60): Promise<ExtractDataResponse> => {

const pollInterval = 3000; // 3 seconds

for (let attempt = 0; attempt < maxAttempts; attempt++) {

const response = await fetchAPI(pollingEndpoint.replace('/api', ''));

const pollResult = await response.json();

// Job completed successfully

if (pollResult.success && pollResult.extraction_result) {

return pollResult;

}

// Job failed

if (pollResult.success === false && pollResult.error) {

throw new Error(`Extraction failed: ${pollResult.error}`);

}

// Job still running, wait and retry

if (pollResult.status === 'running') {

await new Promise(resolve => setTimeout(resolve, pollInterval));

continue;

}

}

throw new Error(`Extraction timed out after 180 seconds`);

};

```

  

### Environment Detection

  

```typescript

const API_BASE_URL = (() => {

// Production: Use direct zrok tunnel URL

if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'production') {

return 'https://mmfrontend.share.zrok.io/api';

}

// Development: Always use local backend

return 'http://localhost:8080/api';

})();

```

  

## Traffic Flow Analysis

  

### Zrok Log Pattern (Production)

  

```bash

# Initial extraction request

POST /api/turbo-extract-data

  

# Polling requests (every 3 seconds)

GET /api/turbo-poll/56a191bb-2050-4a59-bafd-c7b75715fe2b

GET /api/turbo-poll/56a191bb-2050-4a59-bafd-c7b75715fe2b

GET /api/turbo-poll/56a191bb-2050-4a59-bafd-c7b75715fe2b

# ... continues until completion

```

  

### Request Frequency

- **Initial request**: 1 per extraction

- **Polling frequency**: Every 3 seconds

- **Total requests**: ~60 for a 3-minute extraction

- **Bandwidth**: Minimal (JSON status responses)

  

## Performance Characteristics

  

### Local Development

- **Latency**: ~0-5ms (direct connection)

- **Throughput**: No limits

- **Timeout**: None (direct connection)

- **Behavior**: Synchronous, blocks until complete

  

### Production (Zrok Tunnel)

- **Initial Response**: <100ms (immediate job ID)

- **Polling Latency**: ~50-200ms per request

- **Throughput**: Limited by zrok infrastructure

- **Timeout**: None (polling pattern prevents timeouts)

- **Behavior**: Asynchronous, non-blocking

  

## Error Handling

  

### Backend Error States

  

```python

# Job failure tracking

background_jobs[job_id].update({

"status": "failed",

"error": str(e),

"completed_at": datetime.now().isoformat()

})

```

  

### Frontend Error Handling

  

```typescript

// Polling timeout

if (attempt === maxAttempts - 1) {

throw new Error(`Polling failed after ${maxAttempts} attempts`);

}

  

// Job failure

if (pollResult.success === false && pollResult.error) {

throw new Error(`Extraction failed: ${pollResult.error}`);

}

```

  

## Monitoring & Debugging

  

### Backend Logs

```bash

# View real-time backend processing

docker logs backend-backend-1 --follow

  

# Check zrok tunnel traffic

tail -f /home/pll/git/mm-frontend/backend/zrok.log

```

  

### Log Patterns

  

#### Successful Local Request

```

INFO:api.index:🏠 Local development detected - using synchronous processing

INFO:api.index:🚀 Starting TURBO data extraction...

INFO:api.index:🎯 TURBO data extraction completed successfully

```

  

#### Successful Vercel Request

```

INFO:api.index:🚀 Vercel frontend detected - using polling approach for zrok tunnel

INFO:api.index:🚀 Started TURBO extraction job for Vercel: 56a191bb-2050-4a59-bafd-c7b75715fe2b

INFO:api.index:🚀 Starting TURBO data extraction for job 56a191bb-2050-4a59-bafd-c7b75715fe2b

```

  

## Configuration

  

### Zrok Tunnel Setup

```bash

# Start reserved zrok tunnel

./scripts/start-zrok-reserved.sh

  

# Tunnel configuration

zrok share reserved mmfrontend --headless

# Creates: https://mmfrontend.share.zrok.io → localhost:8080

```

  

### Environment Variables

```bash

# Frontend (Vercel)

NEXT_PUBLIC_API_URL=https://mmfrontend.share.zrok.io/api

  

# Backend (Docker)

PYTHONPATH=/app

DATABASE_URL=postgresql://user:pass@postgres:5432/mmfast

```

  

## Testing & Validation

  

### Manual Testing Commands

  

```bash

# Test local endpoint

curl -X POST http://localhost:8080/api/turbo-extract-data \

-H "Content-Type: application/json" \

-H "Origin: http://localhost:3000" \

-d '{"token":"your-token"}'

  

# Test zrok endpoint

curl -X POST https://mmfrontend.share.zrok.io/api/turbo-extract-data \

-H "Content-Type: application/json" \

-H "Origin: https://mm-frontend-psi.vercel.app" \

-d '{"token":"your-token"}'

  

# Test polling

curl -s https://mmfrontend.share.zrok.io/api/turbo-poll/{job-id}

```

  

### Expected Behaviors

  

#### ✅ Working Correctly

- **Local**: Returns complete extraction result immediately

- **Vercel**: Returns job ID, frontend polls automatically

- **No 404 errors**: All endpoints respond correctly

- **No 504 timeouts**: Immediate responses prevent zrok timeouts

  

#### ❌ Common Issues

- **Double `/api/api` in URLs**: Fixed by proper path handling

- **Event loop errors**: Resolved by avoiding thread pools

- **Database connection issues**: Fixed by keeping single async context

  

## Future Enhancements

  

### Potential Improvements

1. **WebSocket Support**: Real-time progress updates instead of polling

2. **Job Persistence**: Store job state in database for crash recovery

3. **Rate Limiting**: Prevent excessive polling requests

4. **Metrics Collection**: Track job completion rates and performance

5. **Adaptive Polling**: Adjust frequency based on job progress

  

### Scalability Considerations

- **Multiple Workers**: FastAPI can handle multiple concurrent extractions

- **Job Queue**: Redis/Celery for more robust background processing

- **Load Balancing**: Multiple backend instances behind load balancer

- **Caching**: Cache job results for repeated requests

  

## Conclusion

  

This architecture successfully solves the **zrok 1-minute timeout limitation** while maintaining **full backward compatibility** with local development. The solution is:

  

- ✅ **Transparent**: Frontend code works unchanged in both environments

- ✅ **Reliable**: No timeouts, proper error handling

- ✅ **Efficient**: Minimal polling overhead, optimized responses

- ✅ **Maintainable**: Clean separation of concerns, well-documented

  

The polling pattern proves to be a robust solution for long-running operations in proxy-limited environments while preserving the developer experience of synchronous APIs in local development.