# Anime Image Generator API

Production-ready FastAPI backend serving a pre-trained PyTorch DCGAN
generator. The model is loaded once at startup and reused for every
request.

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── health.py        # GET / , GET /health
│   │   └── routes.py        # POST /generate , GET /generated/{filename}
│   ├── core/
│   │   ├── config.py         # Pydantic settings (env-driven)
│   │   ├── logging.py        # Loguru setup, intercepts uvicorn logs
│   │   ├── model_loader.py   # Singleton: loads model once, thread-safe
│   │   ├── generator_arch.py # DCGAN Generator (must match training)
│   │   ├── exceptions.py     # Domain exceptions -> HTTP status mapping
│   │   └── rate_limiter.py   # In-memory per-client rate limiter
│   ├── services/
│   │   └── generator_service.py  # Inference + save orchestration
│   ├── schemas/
│   │   ├── generate_request.py
│   │   └── generate_response.py
│   ├── utils/
│   │   └── image_utils.py    # Tensor->image, filename/path-traversal safety
│   ├── generated/             # Saved output images (gitignored)
│   └── main.py                # App factory, lifespan, CORS, error handlers
├── models/
│   └── generator_final.pth    # <-- place your trained checkpoint here
├── tests/
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env
└── README.md
```

## Setup

1. Place your trained checkpoint at `models/generator_final.pth`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open http://localhost:8000/docs for interactive Swagger UI.

If the checkpoint is missing or corrupted, the app still starts;
`/health` reports `model_loaded: false` and `/generate` returns
`503 Service Unavailable` until a valid checkpoint is provided and the
process is restarted.

## API

| Method | Path                     | Description                          |
|--------|--------------------------|---------------------------------------|
| GET    | `/`                      | Service liveness banner               |
| GET    | `/health`                | Model load status + active device     |
| POST   | `/generate`              | Generate one image (`{}` or `{"seed": int}`) |
| GET    | `/generated/{filename}`  | Fetch a previously generated PNG      |

### Example

```bash
curl -X POST http://localhost:8000/generate -H "Content-Type: application/json" -d '{"seed": 123}'
# {"success":true,"filename":"7d8810d3.png","image_url":"/generated/7d8810d3.png","generation_time_ms":42.7,"seed":123}

curl http://localhost:8000/generated/7d8810d3.png --output out.png
```

## Configuration

All settings are environment-driven (see `.env`). Key variables:

| Variable                     | Default                        | Purpose                              |
|-------------------------------|---------------------------------|----------------------------------------|
| `MODEL_PATH`                 | `models/generator_final.pth`   | Checkpoint location                    |
| `FORCE_CPU`                  | `false`                        | Force CPU even if CUDA is available    |
| `MAX_CONCURRENT_GENERATIONS` | `2`                             | Concurrent inference cap (asyncio.Semaphore) |
| `RATE_LIMIT_PER_MINUTE`      | `20`                            | Per-client request cap on `/generate`  |
| `CORS_ORIGINS`               | `*`                             | Comma-separated allowed origins        |

## Design Notes

- **Model lifecycle**: loaded once in `app.main.lifespan` via the
  `ModelLoader` singleton (`app/core/model_loader.py`); never reloaded
  per-request.
- **Thread safety**: `ModelLoader` exposes a `threading.Lock` that
  serializes the seed-set + forward-pass critical section, since
  `torch.manual_seed` is global process state.
- **Non-blocking**: `/generate` runs the synchronous PyTorch call via
  `asyncio.to_thread`, so it never blocks the event loop; an
  `asyncio.Semaphore` bounds how many inferences run concurrently.
- **Security**: generated filenames are server-generated UUID hex
  strings; `image_utils.validate_filename` rejects anything else
  (blocks path traversal on `GET /generated/{filename}`).
- **Extensibility**: `GeneratorService` and `ModelLoader` depend only
  on an `nn.Module` interface (forward pass in, tensor out). Swapping
  in StyleGAN2/3 or a diffusion pipeline later means adding a new
  architecture module and loader branch — the API contract
  (`POST /generate` -> `GenerateResponse`) does not change.

## Testing

```bash
pytest
```

Tests inject a randomly-initialized `Generator` in place of the real
checkpoint, so they run without a trained `.pth` file present.

## Docker

```bash
docker build -t anime-generator-api .
docker run -p 8000:8000 -v $(pwd)/models:/app/models:ro anime-generator-api
```

The image uses a multi-stage build, a non-root user, and a container
`HEALTHCHECK` against `/health`.
