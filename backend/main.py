from fastapi import FastAPI

app = FastAPI()

@app.get("/") #go to http://127.0.0.1:8000
def read_root():
    return {"message": "Artem LOX"}
