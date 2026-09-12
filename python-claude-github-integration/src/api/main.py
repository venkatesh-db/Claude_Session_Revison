from fastapi import FastAPI

app = FastAPI(title="github-claude-integration-py")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
