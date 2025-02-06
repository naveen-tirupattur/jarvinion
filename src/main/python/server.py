from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
import os

app = FastAPI()

CLIENT_ID = "942018537282-r72ige34jp4e3u19mq06jnk0bup65u5r.apps.googleusercontent.com"

class TokenPayload(BaseModel):
    token: str

@app.post("/verify_token", response_class=JSONResponse)
async def verify_token(payload: TokenPayload):
    try:
        id_token_string = payload.token

        # (Optional) Verify the token using Google's server libraries
        idinfo = id_token.verify_token(id_token_string, requests.Request(), CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(status_code=401, detail="Wrong issuer.")

        userid = idinfo['sub']

        return {"name": idinfo['name'], "userid": userid }

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)