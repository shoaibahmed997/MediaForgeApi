from fastapi import FastAPI, Request, Depends,HTTPException,status
import re
from core.url import extract
from models import RequestModel
app = FastAPI()

accept_regax = re.compile(r'^(?:application|text)\/(?:json|plain)$')

@app.get("/")
def read_root():
    return {"Hello": "World"}

async def validate_headers(request:Request):
    accept = request.headers.get("accept","")
    content_type = request.headers.get("content-type","")
    if not accept_regax.match(accept):
        raise HTTPException(status_code=406, detail="Not Acceptable")
    if not accept_regax.match(content_type):
        raise HTTPException(status_code=406,detail='Unsupported type')
    

@app.post('/',dependencies=[Depends(validate_headers)])
def home(data:RequestModel):
    # checks for host 
    parsed = extract(data.url)
    if "error" in parsed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,'error parsing url')
    
    return ""

