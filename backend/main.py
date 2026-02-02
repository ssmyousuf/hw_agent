from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from backend.data_ingestion import load_statement
from backend.mcp_server import set_dataframe
from backend.agent import agent_instance
import shutil
import os
import pandas as pd

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

from typing import List

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...), password: str = Form(None)):
    try:
        all_dfs = []
        
        for file in files:
            # Save temporarily
            temp_path = f"temp_{file.filename}"
            with open(temp_path, "wb") as f:
                f.write(await file.read())
            
            # Load statement
            try:
                df = load_statement(temp_path, password)
                
                if df.empty:
                    os.remove(temp_path)
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Could not parse '{file.filename}'. Please check:\n"
                               "1. PDF is not password-protected (or provide correct password)\n"
                               "2. CSV has 'date', 'description', 'amount' columns\n"
                               "3. File contains valid transaction data"
                    )
                
                all_dfs.append(df)
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"Error parsing {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse '{file.filename}': {str(e)}"
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # Merge all dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        # Auto-categorize if category column missing
        if 'category' not in combined_df.columns:
            combined_df['category'] = combined_df['description'].apply(categorize_merchant)
        
        set_dataframe(combined_df)
        
        return {
            "message": f"Successfully loaded {len(files)} file(s)",
            "rows": len(combined_df)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        response, debug_logs = agent_instance.chat(request.message)
        return {"response": response, "debug_logs": debug_logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check moved or removed to allow frontend to serve at /
@app.get("/health")
def health_check():
    return {"status": "running"}

from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
