import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .agent import DA_agent
import io
import json
import pandas as pd


app = FastAPI(title='AI agent for data analysis')

@app.post('/generate')
async def data_analysis(
    prompt = Form(...),
    file = File(None)
):
    df = None
    if file is not None:
        try:
            contents = await file.read()
            if file.filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(contents))
            elif file.filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка при чтении файла: {e}")
    
    result = DA_agent(user_request=prompt, df=df, max_attempts=1)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=500, 
            detail={
                "message": result.get("detail", "Агент не смог выполнить запрос"),
                "trajectory": result.get("trajectory", "")
            }
        )

    return JSONResponse(content={
        "plot": result.get("data"),   
        "trajectory": result.get("trajectory"),
        "attempts": result.get("attempts_used")
    })