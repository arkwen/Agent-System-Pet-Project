import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .agent import DA_agent

app = FastAPI(title='AI agent for data analysis')

class DataRequest(BaseModel):
    prompt: str

@app.post('/generate')
async def data_analysis(request: DataRequest):
    result_status = DA_agent(request.prompt)
    print(f'Статус: {result_status}')

    if "Ошибка" in result_status:
        raise HTTPException(status_code=500, detail=result_status)
    
    image_path = 'output.png'
    if not os.path.exists(image_path):
        raise HTTPException(status_code=500, detail="График не был создан")
    
    return FileResponse(image_path, media_type='image/png')
