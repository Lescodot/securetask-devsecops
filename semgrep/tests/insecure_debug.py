# This file intentionally contains insecure debug configuration for Semgrep testing.

from fastapi import FastAPI
import uvicorn

app = FastAPI(debug=True)

app.run(debug=True)

uvicorn.run(app, reload=True)
