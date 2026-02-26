from fastapi import FastAPI, Request, Response, Depends,HTTPException
import re
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
def home(request:Request,response:Response):
    return {"message": "Hello World"}