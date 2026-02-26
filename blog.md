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

### main post function

lets analyse whats going on when the client pastes a url i.e. the main post function.

```
app.post('/', async (req, res) => {
        const request = req.body;

        if (!request.url) { => here we check whether we have url basic url validation.
            return fail(res, "error.api.link.missing");
        }

        const { success, data: normalizedRequest } = await normalizeRequest(request); -> then we normalize the request
        if (!success) {
            return fail(res, "error.api.invalid_body");
        }

        const parsed = extract( => extracts the url and retuns hostname and a pattern match => return { host, patternMatch };
            normalizedRequest.url,
            APIKeys.getAllowedServices(req.rateLimitKey),
        );

        if (!parsed) { again validation
            return fail(res, "error.api.link.invalid");
        }

        if ("error" in parsed) { we see if we got an error while parsing i.e. if we got a valid host and pattern for the services
            let context;
            if (parsed?.context) {
                context = parsed.context;
            }
            return fail(res, `error.api.${parsed.error}`, context);
        }

        try {
            const result = await match({ => we return the result of this match function.
                host: parsed.host,
                patternMatch: parsed.patternMatch,
                params: normalizedRequest,
                authType: req.authType ?? "none",
            });

            this function returns
            return matchAction({
            r,
            host,
            audioFormat: params.audioFormat,
            isAudioOnly,
            isAudioMuted,
            disableMetadata: params.disableMetadata,
            filenameStyle: params.filenameStyle,
            convertGif: params.convertGif,
            requestIP,
            audioBitrate: params.audioBitrate,
            alwaysProxy: params.alwaysProxy || localProcessing === "forced",
            localProcessing,
        })

        the match action basically retuns the reponse type, default params and params
        defaultParams = {
            url: r.urls,
            headers: r.headers,
            service: host,
            filename: r.filenameAttributes ?
                    createFilename(r.filenameAttributes, filenameStyle, isAudioOnly, isAudioMuted) : r.filename,
            fileMetadata: !disableMetadata ? r.fileMetadata : false,
            requestIP,
            originalRequest: r.originalRequest,
            subtitles: r.subtitles,
            cover: !disableMetadata ? r.cover : false,
            cropCover: !disableMetadata ? r.cropCover : false,
        },
        params = {};

            res.status(result.status).json(result.body);
        } catch {
            fail(res, "error.api.generic");
        }
    });
```

let's start porting this to fastapi.

1. validations

- we will define a base model by importing from pydantic

```
class UrlRequest(BaseModel):
    url: str
```

this will validate the url in incoming request's body. that was simple enough, fastapi handles the validation for us. firing a simple thunder client reuqest to make sure this works

2. now the normalise requst.

- let's study what it does first and then we'll think about how to architecture this.
- the normalizeRequest takes the incoming request and does some validations and adds some other info like audioBitrate, video format etc.
- the normalizeRequest does validation with zod which is awesome. i suppose we could do the same using pydantic. for that we will have to create a request model and use it as dependency.
- the zod also transforms the url -> parses it, cleans it etc. this can be achieved by field_validator functions

```
from pydantic import BaseModel,Field, field_validator, ConfigDict,HttpUrl
from typing import Literal,Optional

class RequestModel(BaseModel):
    """
    """
    model_config = ConfigDict(extra="forbid")

    url:str
    audioBitrate: Literal["320", "256", "128", "96", "64", "8"] = "128"
    audioFormat: Literal["best", "mp3", "ogg", "wav", "opus"] = "mp3"
    downloadMode: Literal["auto", "audio", "mute"] = "auto"
    filenameStyle: Literal["classic", "pretty", "basic", "nerdy"] = "basic"
    youtubeVideoCodec: Literal["h264", "av1", "vp9"] = "h264"
    youtubeVideoContainer: Literal["auto", "mp4", "webm", "mkv"] = "auto"
    videoQuality: Literal["max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"] = "1080"
    localProcessing: Literal["disabled", "preferred", "forced"] = "disabled"

    youtubeDubLang:Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=8,
        pattern=r"^[0-9a-zA-Z\-]+$",
        description="Language code for YouTube dubbing (e.g., 'en', 'pt-BR')"
    )

    subtitleLang: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=8,
        pattern=r"^[0-9a-zA-Z\-]+$",
        description="Language code for subtitles"
    )
    disableMetadata: bool = False
    allowH265: bool = False
    convertGif: bool = True
    tiktokFullAudio: bool = False
    alwaysProxy: bool = False
    youtubeHLS: bool = False
    youtubeBetterAudio: bool = False


    @field_validator("url",mode="before")
    @classmethod
    def normalise_url_field(cls,value:str) -> str:
        """
        Runs before type validation
        Purpose:
        1. will decide.
        """

```

okay now onto the clean_url and alias url, they use psl, i will use tldextract. this should work as expected.

starting with aliasUrl

- what it does ?
  it Convert alternative/short URLs to canonical format. for example youtu.be -> youtube.

```
case "youtu":
            if (url.hostname === 'youtu.be' && parts.length >= 2) {
                /* youtu.be urls can be weird, e.g. https://youtu.be/<id>//asdasd// still works
                ** but we only care about the 1st segment of the path */
                url = new URL(`https://youtube.com/watch?v=${
                    encodeURIComponent(parts[1])
                }`)
            }
            break;

```

here is an example of the core of aliasUrl -> it converts the youtube url such as youtu.be/shorts/shortID -> youtube.com/watch?v=shortID
it does it for other services as well.

some things that are differnt from the express version.
we import urlparse, urlunparse,quote,parse_qs from urllib.parse

- urlparse -> takes in a url and gives an object with hostname, query, pathname etc.
- quote -> encodeURIComponent equivalent.
- parse_qs -> parses url query params (query strings)

now onto the cleanUrl func.

## helper functions

if we keep digging the main post request we have some helper functions that doese the processing of url in that there is one lib called psl -> public suffix list. for this they are using @imput/psl but for our usecase we will use tldextact.
what this lib does it is extract domain info from a public list of domains.

#### get_host_if_valid

#### extract

#### services_config

```

```
