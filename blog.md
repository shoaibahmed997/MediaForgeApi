## architecture decision

### some things we decided on for the backend:

1. we will not use cors as we will be using nginx as a reverse proxy to serve both frontend and backend from the same origin. This will simplify our architecture and avoid potential issues with cross-origin requests.

2. rate limiter is not required as this will be hosted on my homelab server. i don't need to worry about the ddos attacks from my family members. if you are planning to host this for public use, you might want to consider implementing a rate limiter to protect your server from potential abuse. maybe i will add it later if i find it necessary.

Studying the main express server imputnet/cobalt/api/src/core/api.js

## a request lifecycle goes like this

client -> CORS -> header validation -> api key auth -> jwt auth -> rate limit -> json body parser -> service extraction -> media matching -> response

we will implement the same lifecycle in our fastapi server. few things will be different like we will not implement cors and rate limiter asd they will be handled by nginx.
Express has a next function to pass the control to the next middleware, in fastapi we can achieve the same by using dependencies.
middleware are applied to all routes, while dependencies can be applied to specific routes.

let's clearify the order of middleware applied in cobalt:

1. Middlware applied to all routes:

- CORS `app.use('/', cors({...}))`
- Json body parser `app.use('/', express.json({ limit: 1024 }))`
- body parser error handler -> catches json parsing errors globally. `app.use('/', (err, _, res, next) => { ... })`
- global error handler -> catches all unhandled errors globally.

```
app.use((_, __, res, ___) => {
   return fail(res, "error.api.generic");
})
```

2. Middleware applied only to POST /

- Header validation

- API key auth -> if valid req.authType = "key"
- JWT auth -> if valid req.authType = "session"
- Rate limiting

3. Middleware applied to specific endpoints:

- session endpoint `app.post("/session", sessionLimiter, handler)`
- tunnel endpoint `app.get('/tunnel', apiTunnelLimiter, handler)`

## Lets Build

Let's start by creating these middlware functions, i'm skipping the cors and starting with header validation.
the header validation checks for if the incoming request has the correct accept header and if the content-type header is correct for post requests
it checks for these two things using regax.
Accept: application/json
Content-Type: application/json

this is the neive way of checking the headers. this works but it doesn't scale well.

```
@app.post('/')
def home(request:Request,response:Response):
    if not accept_regax.match(request.headers.get('accept','')):
        return fail(response,406,"Not Acceptable")
    if not accept_regax.match(request.headers.get('content-type','')):
        return fail(response,415,"Unsupported Media Type")
    return {"message": "Hello World"}

```

## validation headers

here is the function for validation header.

```
async def validate_headers(request:Request):
    accept = request.headers.get("accept","")
    content_type = request.headers.get("content-type","")
    if not accept_regax.match(accept):
        raise HTTPException(status_code=406, detail="Not Acceptable")
    if not accept_regax.match(content_type):
        raise HTTPException(status_code=406,detail='Unsupported type')

```

now we can use this function as a dependency for our post route.

```
@app.post('/',dependencies=[Depends(validate_headers)])
def home(request:Request,response:Response):
    return {"message": "Hello World"}
```

in fastapi we need to raise HTTPException to return an error response, we can't return a custom response like in express. this is because fastapi uses the status code and detail from the exception to generate the response.

we will continue with the rest of post function and add the necesssary middleware functions in the next few commits.
