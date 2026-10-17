import uvicorn

if __name__ == "__main__":
    print("Starting Garage4U server on port 8000...", flush=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

