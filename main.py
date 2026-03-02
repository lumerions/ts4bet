from fastapi import FastAPI, Form, Request, Response, Cookie, status, Query, Header
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse,FileResponse
from fastapi.templating import Jinja2Templates
from upstash_redis import Redis
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
import json,requests,time,uvicorn,certifi,base64,math,random,string,secrets,os,bcrypt,psycopg,hmac,secrets,hashlib,urllib.parse,traceback,re
from pydantic import BaseModel
from pymongo import MongoClient,UpdateOne,ReturnDocument
from typing import List, Dict, Any
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
place_id = 81033157158500
NOWPAYMENTS_WEBHOOK_SECRET = "/adA+ZQs/8aZPVdsW6bNwFl+l+VXEoVJ"
SessionIdCSRFTokens = {}

app = FastAPI(
    title="AH Gambling",
    description="AH Gambling",
    version="1.0.0",
)

app.mount("/javascript", StaticFiles(directory="javascript"), name="javascript")

def LimiterFunction(request):
    return request.cookies.get('SessionId')  
    
limiter = Limiter(key_func=LimiterFunction)
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter

def getCSRFTokens(sessionid : str,ttl = 1800):
    now = time.time()
    if sessionid in SessionIdCSRFTokens:
        token, expiry = SessionIdCSRFTokens[sessionid]
        if expiry > now:
            return token
    token = secrets.token_urlsafe(32)
    SessionIdCSRFTokens[sessionid] = (token, now + ttl)
    return token

def getMongoClient(ConnectionURI = None):
    if not ConnectionURI:
        ConnectionURI = os.environ["MONGO_CONNECTIONURI"]
    client = MongoClient(
        ConnectionURI,
        serverSelectionTimeoutMS=20000,
        tls=True,
        tlsCAFile=certifi.where()
    )
    return client

Mongo_Client = getMongoClient()

def getMainMongo():
    db = Mongo_Client["main"]
    collection = db["main"]
    return {"db": db,"collection":collection}

def getCoinflipMongo():
    db = Mongo_Client["main"]
    collection = db["coinflips"]
    return {"db": db,"collection":collection}

def getSiteItemsMongo():
    db = Mongo_Client["main"]
    collection = db["siteitems"]
    return {"db": db,"collection":collection}

def returnTemplate(error,request,errortype,htmlfile,statuscode):
    return templates.TemplateResponse(
        htmlfile,
        {"request": request, errortype: error},
        status_code=statuscode
    )

def MoreWithdraw(pagetype,request):
    if pagetype == "towers":
        return returnTemplate("You are trying to play more then you have!",request,"towers_error", "towers.html",status.HTTP_400_BAD_REQUEST)

    if pagetype == "mines":
        return returnTemplate("You are trying to play more then you have!",request,"mines_error", "mines.html",status.HTTP_400_BAD_REQUEST)

def getCurrentUser(SessionId):
    try:
        conn = getPostgresConnection() 

        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM accounts WHERE sessionid = %s", (SessionId,))
            result = cursor.fetchone()  

            if result is None:
                return {"error": "Invalid session"}

            return {"username": result[0]}
    except Exception as error:
        return error
    
def giveCancelCoinflipItems(Field : str,document,SessionId):
    return UpdateOne(
        {"SessionId": SessionId},
            {
                "$push": {
                    "items": {
                        "$each": document.get(Field)
                    }
                }
        },
    )

def getMarketplaceData():
    database = Mongo_Client["Catalog"]
    collection = database["Items"]
    try:
        MarketplaceData = collection.find(
            {},
        )

        MarketplaceData = list(MarketplaceData)
        return MarketplaceData
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

class deposit(BaseModel):
    robloxusername: str
    siteusername : str
    sessionid : str
    amount : int
    Deposit : bool

class DepositItems(BaseModel):
    robloxusername: str
    userid : int
    siteusername : str
    sessionid : str
    itemdata : List[Dict[str, Any]]
    Deposit : bool

class MinesClick(BaseModel):
    tileIndex: int
    Game : str
class Config:
    extra = "allow"

class Cashout(BaseModel):
    amount: int

redis = Redis(
    url=os.environ["REDIS_URL"],
    token=os.environ["REDIS_TOKEN"]
)

def getPostgresConnection():
    return psycopg.connect(os.environ["POSTGRES_DATABASE_URL"], autocommit=True)

templates = Jinja2Templates(directory="templates")

def CheckIfUserIsLoggedIn(request,htmlfile,htmlfile2,returnusername = None):
    SessionId = request.cookies.get('SessionId')  
    if not SessionId:
        return templates.TemplateResponse(htmlfile, {"request": request})
    else:
        CSRFToken = getCSRFTokens(SessionId)

        try:
            conn = getPostgresConnection() 
            with conn.cursor() as cursor:
                cursor.execute("SELECT sessionid,username,robloxusername FROM accounts WHERE sessionid = %s", (SessionId,))
                
                result = cursor.fetchone()  
                
                if result and result[0] == SessionId:
                    if returnusername is None:
                        return templates.TemplateResponse(htmlfile2, {"request": request,"X-CSRF-Token":CSRFToken})
                    else:
                        return {"siteuser":result[1],"robloxuser":result[2]}
                else:
                    response = templates.TemplateResponse(htmlfile, {"request": request,"X-CSRF-Token":CSRFToken})
                    response.delete_cookie("SessionId")
                    return response
        
        except Exception as error:
            return templates.TemplateResponse(
                htmlfile,
                {"request": request, "error": f"{error}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"}
    )

@app.get("/register", response_class=HTMLResponse)
@limiter.limit("50/minute")
def readregister(request: Request):
    return CheckIfUserIsLoggedIn(request,"register.html","home.html")


@app.get("/login",response_class =  HTMLResponse)
@limiter.limit("50/minute")
def readlogin(request: Request):
    SessionId = request.cookies.get('SessionId')  
    if not SessionId:
        return templates.TemplateResponse("login.html", {"request": request})
    else:
        try:
            conn = getPostgresConnection() 
            with conn.cursor() as cursor:
                cursor.execute("SELECT sessionid FROM accounts WHERE sessionid = %s", (SessionId,))
                
                result = cursor.fetchone()  
                
                if result and result[0] == SessionId:
                    return templates.TemplateResponse("home.html", {"request": request})
                else:
                    response = templates.TemplateResponse("login.html", {"request": request})
                    response.delete_cookie("SessionId")
                    return response
        
        except Exception as error:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": f"{error}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
@app.get("/mines",response_class =  HTMLResponse)
@limiter.limit("50/minute")
def loadmines(request: Request):
    return CheckIfUserIsLoggedIn(request,"register.html","mines.html")

@app.get("/towers",response_class =  HTMLResponse)
@limiter.limit("50/minute")
def towers(request: Request):
    return CheckIfUserIsLoggedIn(request,"register.html","towers.html")

@app.get("/dice",response_class =  HTMLResponse)
@limiter.limit("50/minute")
def dice(request: Request):
    return CheckIfUserIsLoggedIn(request,"register.html","dice.html")


@app.get("/coinflipfdddeere", response_class=HTMLResponse)
@limiter.limit("50/minute")
def GetActiveCoinflips(request : Request,SessionId: str = Cookie(None)):
    if not SessionId:
        return JSONResponse({"error": "SessionId missing"}, status_code=400)
 
    try:
        conn = getPostgresConnection() 
        with conn.cursor() as cursor:
            cursor.execute("SELECT sessionid,username,robloxusername FROM accounts WHERE sessionid = %s", (SessionId,))
            
            result = cursor.fetchone()  
            
            if result and result[0] != SessionId:
                response = templates.TemplateResponse("register.html", {"request": request})
                response.delete_cookie("SessionId")
                return response
            else:
                 siteusername = result[1]
    
    
        CoinflipCollection = getCoinflipMongo()["collection"]
    
        Documents = CoinflipCollection.find(
            {},
        )

        Documents = list(Documents)

        redisData = redis.get("CoinflipEnds")
        if redisData:
            OldCoinflipData = json.loads(redisData)
        else:
            OldCoinflipData = []

        print("Mongo:", Documents)
        print("Redis:", OldCoinflipData)

        Documents = Documents + OldCoinflipData

        CSRFToken = getCSRFTokens(SessionId)

        if not Documents:
            return templates.TemplateResponse(
                    "coinflip.html",
                    {"request": request, "matches": [], "username": siteusername,"X-CSRF-Token":CSRFToken},
                )

        UserIds = ",".join(
            str(v[key])
            for v in Documents
            for key in ("UserId", "UserId2")
            if key in v and v[key] != ""
        )
            
        AssetIdParam = ",".join(
            str(itemid)
            for itemid in {
                item["itemid"] 
                for v in Documents 
                for item in v.get("CoinflipItems", []) + v.get("CoinflipItems2", [])
            }
        )
    
        # bandwidth might be insane if theres lots of data ill optimize it later trust
        print(AssetIdParam)
        print(UserIds)
        if AssetIdParam:
            try:
                response = requests.get(f"https://thumbnails.roproxy.com/v1/assets?assetIds={AssetIdParam}&size=512x512&format=Png")
                decodedResponse = response.json()
                decodedResponseData = decodedResponse.get("data",[])
                thumbnailsDict = {int(v["targetId"]): v["imageUrl"] for v in decodedResponseData}
            except Exception as e:
                print(str(e))
                return JSONResponse({"error": str(e)}, status_code=400)
        if UserIds:
            try:
                RobloxThumbnailEndpoint = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={UserIds}&size=420x420&format=Png&isCircular=false"
                RobloxThumbnailEndpointResponse = requests.get(RobloxThumbnailEndpoint)
                RobloxThumbnailUrls = RobloxThumbnailEndpointResponse.json().get("data",[])
                avatarDict = {int(v["targetId"]): v["imageUrl"] for v in RobloxThumbnailUrls}
            except Exception as e:
                print(str(e))
                return JSONResponse({"error": str(e)}, status_code=400)

        response = requests.get("https://express-js-on-vercel-blue-sigma.vercel.app/GetItem")
        MarketplaceData = response.json()
        ItemData = MarketplaceData["data"]
        CSRFToken = getCSRFTokens(SessionId)

        for v in Documents:
            MatchId = v.get("MatchId", "nil")
            CoinflipItems = v.get("CoinflipItems", [])
            CoinflipItems2 = v.get("CoinflipItems2", [])
            Winner = v.get("Winner")
            v["id"] = MatchId
            v["side"] = v.get("Side", "nil")
            v["total_value"] = 0

            itemLookup = {int(item["itemId"]): item for item in ItemData}

            for cfitem in CoinflipItems:
                item = itemLookup.get(cfitem["itemid"])
                if item:
                    v["total_value"] += int(item["value"])

            for cfitem in CoinflipItems2:
                item = itemLookup.get(cfitem["itemid"])
                if item:
                    v["total_value"] += int(item["value"])

            v["total_items"] = len(CoinflipItems) + len(CoinflipItems2)
            if "_id" in v:
                v["_id"] = str(v["_id"])
            user1_raw = v.get("UserId")
            user2_raw = v.get("UserId2")
    
            try:
                UserId = int(user1_raw) if user1_raw not in (None, "") else 0
            except (ValueError, TypeError):
                UserId = 0
    
            try:
                UserId2 = int(user2_raw) if user2_raw not in (None, "") else 0
            except (ValueError, TypeError):
                UserId2 = 0
            avatarUrl = avatarDict.get(UserId, "")
            avatarUrl2 = avatarDict.get(UserId2, "")
            v["ImageUrl"] = avatarUrl
            if Winner:
                v["Winner"] = Winner
            v["player1"] = {"username": v.get("Username", "Unknown"), "avatar": avatarUrl}
            v["player2"] = {"username": v.get("Username2", "Unknown"), "avatar": avatarUrl2}
            v["items"] = [{"image": thumbnailsDict.get(int(item["itemid"]), "")} for item in CoinflipItems]
            v["items2"] = [{"image": thumbnailsDict.get(int(item["itemid"]), "")} for item in CoinflipItems2]

        return templates.TemplateResponse(
                "coinflip.html",
                {"request": request, "matches": Documents, "username": siteusername,"X-CSRF-Token":CSRFToken},
            )

    except Exception as error:
        return templates.TemplateResponse(
            "coinflip.html",
            {"request": request, "error": str(error), "X-CSRF-Token": CSRFToken},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/", response_class=HTMLResponse)
@limiter.limit("50/minute")
def readroot(request: Request):
    Result = CheckIfUserIsLoggedIn(request,"register.html","home.html")
    return Result

@app.get("/home")
@limiter.limit("50/minute")
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/logout")
@limiter.limit("50/minute")
def logout(request : Request):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="SessionId")
    return response


@app.get("/getbalance")
@limiter.limit("50/minute")
def get(request : Request,SessionId: str = Cookie(None)):

    RedisGet = redis.get(SessionId)

    if not RedisGet:
        mainMongo = getMainMongo()
        mainCollection = mainMongo["collection"]

        try:
            doc = mainCollection.find_one({"sessionid": SessionId})
            
        except Exception as error:
            return {"error": str(error)}
        
        if not doc:
            return 0 
        
        redis.set(SessionId,int(doc["balance"]),ex = 2628000)

        return int(doc["balance"])
    else:
        return int(RedisGet)

@app.get("/deposit")
@limiter.limit("50/minute")
async def depositget(request : Request,amount: float, SessionId: str = Cookie(None)):
    if not SessionId:
        return {"error": "No cookie provided"}
    
    sitename = getCurrentUser(SessionId)

    if sitename.get("error"):
        return sitename

    launch_data = {
        "sitename": str(sitename["username"]),
        "sessionid": SessionId,
        "amount": amount,
        "deposit" : True
    }

    json_data = json.dumps(launch_data)
    b64_data = base64.b64encode(json_data.encode()).decode()

    roblox_url = (
        f"https://www.roblox.com/games/start"
        f"?placeId={place_id}"
        f"&launchData={urllib.parse.quote(b64_data)}"
    )

    return RedirectResponse(roblox_url)

@app.get("/withdraw",response_class =  HTMLResponse)
@limiter.limit("50/minute")
async def withdrawget(request: Request,amount: float, page: str, SessionId: str = Cookie(None)):
    if not SessionId:
        return {"error": "No cookie provided"}
    
    sitename = getCurrentUser(SessionId)

    if sitename.get("error"):
        return sitename

    mainMongo = getMainMongo()
    mainCollection = mainMongo["collection"]
    RedisBalance = redis.get(SessionId)

    if not RedisBalance:
        return MoreWithdraw(page)

    if amount > int(RedisBalance):
        return MoreWithdraw(page)

    launch_data = {
        "sitename": str(sitename["username"]),
        "sessionid": SessionId,
        "amount": amount,
        "deposit" : False
    }

    json_data = json.dumps(launch_data)
    b64_data = base64.b64encode(json_data.encode()).decode()

    roblox_url = (
        f"https://www.roblox.com/games/start"
        f"?placeId={place_id}"
        f"&launchData={urllib.parse.quote(b64_data)}"
    )

    return RedirectResponse(roblox_url)


@app.post("/withdrawitems",response_class =  HTMLResponse)
@limiter.limit("50/minute")
async def withdrawget(request: Request, SessionId: str = Cookie(None)):
    if not SessionId:
        return {"error": "No cookie provided"}
    
    data = await request.json()
    itemdata = data.get("itemdata")

    sitename = getCurrentUser(SessionId)

    if sitename.get("error"):
        return sitename

    SiteItemsCollection = getSiteItemsMongo()["collection"]

    try:
        document = SiteItemsCollection.find_one({"SessionId": SessionId})
        if not document:
            return JSONResponse({"error": "Unknown error"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": "Unknown error"}, status_code=400)
    
    itemsData = document["items"]
    ItemsVerifiedCount = 0

    for item_name, serials in itemdata.items():
        for serial in serials:
            for i,v in enumerate(itemsData):
                if str(v["itemname"]) == str(item_name) and int(serial.replace("#","")) == int(v["serial"]):
                    ItemsVerifiedCount += 1
                    break

    if ItemsVerifiedCount != len(itemdata):
        return JSONResponse({"error": "Item verification failed!"}, status_code=400)
    
    print(itemdata)

    launch_data = {
        "sitename": str(sitename["username"]),
        "sessionid": SessionId,
        "items": itemdata,
        "itemdeposit" : False
    }

    json_data = json.dumps(launch_data)
    b64_data = base64.b64encode(json_data.encode()).decode()

    roblox_url = (
        f"https://www.roblox.com/games/start"
        f"?placeId={place_id}"
        f"&launchData={urllib.parse.quote(b64_data)}"
    )

    return JSONResponse({"redirect": roblox_url})

@app.post("/cashinearnings")
@limiter.limit("50/minute")
def depositearnings(request : Request,data: deposit):

    if not data.robloxusername:
        return JSONResponse({"error": "Roblox username missing"}, status_code=400)

    if not data.siteusername:
        return JSONResponse({"error": "Site username missing"}, status_code=400)

    if not data.sessionid:
        return JSONResponse({"error": "Session ID missing"}, status_code=400)

    if data.Deposit is None:
        return JSONResponse({"error": "Deposit flag missing"}, status_code=400)

    try:
        amount = abs(int(data.amount))
        if amount <= 0:
            return JSONResponse({"error": "Invalid amount"}, status_code=400)
    except Exception:
        return JSONResponse({"error": "Amount must be an integer"}, status_code=400)

    try:
        conn = getPostgresConnection() 

        with conn.cursor() as cur:
            cur.execute(
                "SELECT username FROM accounts WHERE username = %s AND sessionid = %s",
                (data.siteusername, data.sessionid)
            )
            row = cur.fetchone()

            if not row:
                return JSONResponse({"error": "Invalid session"}, status_code=403)

            cur.execute(
                "UPDATE accounts SET robloxusername = %s WHERE username = %s",
                (data.robloxusername, data.siteusername)
            )
            conn.commit()

    except Exception as e:
        return JSONResponse({"error": f"{str(e)}"}, status_code=400)

    mainCollection = getMainMongo()["collection"]

    if data.Deposit:
        newDocument = mainCollection.find_one_and_update(
            {"username": data.siteusername, "sessionid": data.sessionid},
            {"$inc": {"balance": amount}},
            return_document = ReturnDocument.AFTER,
            upsert=True
        )

        newBalance = int(newDocument["balance"])

        redis.set(data.sessionid,newBalance,ex = 2628000)

        return {"success": True, "type": "deposit", "amount": amount}
    else:
        newDocument = mainCollection.find_one_and_update(
            {
                "username": data.siteusername,
                "sessionid": data.sessionid,
                "balance": {"$gte": amount}
            },
            {
                "$inc": {"balance": -amount}
            },
            return_document = ReturnDocument.AFTER
        )

        if not newDocument:
            return JSONResponse(
                {"error": "Insufficient funds or wallet not found"},
                status_code=400
            )
        
        NewBalance = newDocument["balance"]
        redis.set(data.sessionid,NewBalance,ex = 2628000)

        return {"success": True, "type": "withdraw", "amount": amount}
    
@app.post("/cashinearningsitems")
@limiter.limit("50/minute")
def depositearnings(request : Request,data: DepositItems):

    if not data.robloxusername:
        return JSONResponse({"error": "Roblox username missing"}, status_code=400)

    if not data.siteusername:
        return JSONResponse({"error": "Site username missing"}, status_code=400)

    if not data.sessionid:
        return JSONResponse({"error": "Session ID missing"}, status_code=400)

    if data.Deposit is None:
        return JSONResponse({"error": "Deposit flag missing"}, status_code=400)
    
    if data.userid is None:
        return JSONResponse({"error": "userid missing"}, status_code=400)
    
    if data.itemdata is None:
        return JSONResponse({"error": "Item data missing"}, status_code=400)

    try:
        conn = getPostgresConnection() 

        with conn.cursor() as cur:
            cur.execute(
                "SELECT username FROM accounts WHERE username = %s AND sessionid = %s",
                (data.siteusername, data.sessionid)
            )
            row = cur.fetchone()

            if not row:
                return JSONResponse({"error": "Invalid session"}, status_code=403)

            cur.execute(
                "UPDATE accounts SET robloxusername = %s WHERE username = %s",
                (data.robloxusername, data.siteusername)
            )
            conn.commit()

    except Exception as e:
        return JSONResponse({"error": f"{str(e)}"}, status_code=400)
    

    database = Mongo_Client["Catalog"]
    collection = database["Items"]

    if data.Deposit:
        getInventoryUrl =  "https://express-js-on-vercel-blue-sigma.vercel.app/GetInventory?id=" + str(data.userid)
        Response = requests.get(getInventoryUrl)
        decodedResponse = Response.json()
        DataGet = decodedResponse.get("data")
        profile = {
            "Data": {
                "Inventory": {}
            }
        }

        depo = data.itemdata
        ItemsVerified = 0

        for item_id, serials in DataGet.items():
            if item_id not in profile["Data"]["Inventory"]:
                profile["Data"]["Inventory"][item_id] = {}

            for sn in serials:
                profile["Data"]["Inventory"][item_id][sn] = {}

        for i in depo:
            inv = profile["Data"]["Inventory"]
            item_id = str(i["itemid"])

            if item_id in inv:
                inv2 = profile["Data"]["Inventory"][item_id]
                serial = str(i["serial"])
                if serial in inv2:
                    ItemsVerified += 1

        if int(ItemsVerified) != len(data.itemdata):
            return JSONResponse({"error": "Item ownership verification failed!"}, status_code=400)
        
        operations = []

        for item in depo:
            serial = int(item["serial"]) - 1

            newslot = {
                "$set": {
                    f"serials.{serial}.u": 1,
                    f"serials.{serial}.t": int(time.time())
                },
                "$unset": {
                    f"reselling.{serial}.u": ""
                }
            }

            operations.append(
                UpdateOne(
                    {"itemId": int(item["itemid"])},  
                    newslot
                )
            )

        if len(operations) > 0 :
            collection.bulk_write(operations)
        else:   
            return JSONResponse({"error": "No operations found!"}, status_code=400)


        SiteItemsCollection = getSiteItemsMongo()["collection"]

        response = SiteItemsCollection.update_one(
            {"SessionId": data.sessionid, "Username": data.siteusername},
            {
                "$push": {
                    "items": {
                        "$each": depo
                    }
                }
            },
            upsert=True
        )

        return {"success": True}
    else:
        try:
            SiteItemsCollection = getSiteItemsMongo()["collection"]

            try:
                document = SiteItemsCollection.find_one({"SessionId": data.sessionid})
                if not document:
                    return JSONResponse({"error": "No document found for site items!"}, status_code=400)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=400)

            profile = {
                "Data": {
                    "Inventory": {}
                }
            }

            withdraw = data.itemdata
            ItemsVerified = 0

            print(document["items"])

            for i in document["items"]:
                itemid = str(i["itemid"])
                serial = str(i["serial"])

                if itemid not in profile["Data"]["Inventory"]:
                    profile["Data"]["Inventory"][itemid] = {}

                profile["Data"]["Inventory"][itemid][serial] = {}

            for i in withdraw:
                inv = profile["Data"]["Inventory"]
                item_id = str(i["itemid"])

                if item_id in inv:
                    inv2 = profile["Data"]["Inventory"][item_id]
                    serial = str(i["serial"])
                    if serial in inv2:
                        ItemsVerified += 1

            print("Inventory map:", profile["Data"]["Inventory"])
            print("Withdraw items:", withdraw)


            if int(ItemsVerified) != len(withdraw):
                return JSONResponse({"error": "Item ownership verification failed!"}, status_code=400)
            
            bulk_ops = []
            operations = []

            for item in withdraw:
                itemid = int(item["itemid"])
                serial = int(item["serial"])

                bulk_ops.append(
                    UpdateOne(
                        {"SessionId": data.sessionid},
                        {"$pull": {"items": {"itemid": itemid, "serial": serial}}}
                    )
                )

                operations.append(
                    UpdateOne(
                        {"itemId": itemid},
                        {
                            "$set": {
                                f"serials.{serial - 1}.u": data.userid,
                                f"serials.{serial - 1}.t": int(time.time())
                            }
                        }
                    )
                )


            if len(bulk_ops) > 0 and len(operations) > 0:
                try:
                    SiteItemsCollection.bulk_write(bulk_ops)
                    collection.bulk_write(operations)
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=400)
            else:
                return JSONResponse({"error": "Operation or bulk ops is empty!"}, status_code=400)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

        return {"success": True}


@app.get("/games/getCurrentData")
@limiter.limit("50/minute")
def get(request : Request,Game : str,SessionId: str = Cookie(None)):
    if not SessionId:
        return JSONResponse({"error": "SessionId missing"}, status_code=400)
    keys = [
        "ClickData." + SessionId,
        SessionId + "TowersActive"
    ]

    data_raw, towersactive = redis.mget(*keys)

    if towersactive == "1" and Game == "Mines":
        return []

    existing_array = json.loads(data_raw) if data_raw else []
    return existing_array

@app.get("/games/cashoutamount")
@limiter.limit("50/minute")
def getcashoutAmount(request : Request,Game: str, Row: int = 0, SessionId: str = Cookie(None)):
    if not SessionId:
        return JSONResponse({"error": "SessionId missing"}, status_code=400)
    
    if not Game:
        return JSONResponse({"error": "Page missing"}, status_code=400)

    keys = [
        SessionId + "minesdata",
        SessionId + "GameActive",
        SessionId + "Cleared",
        SessionId + "BetAmount",
        SessionId + "Cashout",
        SessionId + "TowersActive"
    ]

    mines_raw, game_active, cleared_raw, bet_amount_raw,CurrentUserAmount,TowerActive = redis.mget(*keys)

    if not mines_raw:
        return JSONResponse({"error": "No mines found"}, status_code=400)

    if not game_active:
        return {"amount": 0, "amountafter": 0, "multiplier": 1}

    try:
        mines = json.loads(mines_raw.decode() if isinstance(mines_raw, bytes) else mines_raw)
        if not isinstance(mines, list):
            mines = []
    except Exception:
        mines = []

    tilescleared = int(cleared_raw) if cleared_raw else 0
    bet_amount = int(bet_amount_raw) if bet_amount_raw else 0

    if Game == "Towers":
        return {
            "amount": CurrentUserAmount,
            "betamount": bet_amount,
            "minescount":len(mines)
        }
    elif Game == "Mines":
        if TowerActive == "1":
            return {
                "amount": 0,
                "amountafter": 0,
                "multiplier": 0
            }
        total_tiles = 25
    else:
        return JSONResponse({"error": "Unknown game"}, status_code=400)

    multiplier_per_click = total_tiles / max(total_tiles - len(mines), 1)
    current_multiplier = multiplier_per_click ** tilescleared
    next_multiplier = multiplier_per_click ** (tilescleared + 1)

    currentamount = int(bet_amount * current_multiplier)
    amountafternexttile = int(bet_amount * next_multiplier)

    return {
        "amount": currentamount,
        "amountafter": amountafternexttile,
        "multiplier": current_multiplier
    }

@app.get("/GetInventory")
@limiter.limit("50/minute")
def getInventory(request : Request,SessionId: str = Cookie(None)):
    if not SessionId:
        return JSONResponse({"error": "SessionId missing"}, status_code=400)
    
    SiteItemsCollection = getSiteItemsMongo()["collection"]

    try:
        document = SiteItemsCollection.find_one({"SessionId": SessionId})
        if not document:
            return JSONResponse({"error": "document not found"}, status_code=400)

    except Exception as e:
        return JSONResponse({"error": "Unknown error"}, status_code=400)
    
    AssetIdParam = ""

    for i,v in enumerate(document["items"]):
        AssetIdParam = AssetIdParam + str(v["itemid"]) + ","

    AssetIdParam = AssetIdParam[:-1]

    MarketplaceData = getMarketplaceData()

    try:
        response = requests.get(f"https://thumbnails.roproxy.com/v1/assets?assetIds={AssetIdParam}&size=512x512&format=Png")
        decodedResponse = response.json()
        decodedResponseData = decodedResponse.get("data")
        for v in document["items"]: 
            for thumb in decodedResponseData:
                if int(thumb["targetId"]) == int(v["itemid"]):
                    v["ImageUrl"] = thumb["imageUrl"]
                    break

            for market in MarketplaceData:
                if int(market["itemId"]) == int(v["itemid"]):  
                    v["Value"] = market["value"]
                    break

        return document["items"]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/deposititems")
@limiter.limit("50/minute")
async def depositget(request : Request, SessionId: str = Cookie(None)):
    if not SessionId:
        return {"error": "No cookie provided"}
    
    sitename = getCurrentUser(SessionId)

    if sitename.get("error"):
        return sitename
    
    launch_data = {
        "sitename": str(sitename["username"]),
        "sessionid": SessionId,
        "itemdeposit" : True
    }

    json_data = json.dumps(launch_data)
    b64_data = base64.b64encode(json_data.encode()).decode()

    roblox_url = (
        f"https://www.roblox.com/games/start"
        f"?placeId={place_id}"
        f"&launchData={urllib.parse.quote(b64_data)}"
    )

    return RedirectResponse(url=roblox_url, status_code=303)


@app.post("/games/click")
@limiter.limit("50/minute")
def gameclick(request: Request,data: MinesClick, SessionId: str = Cookie(None)):
    if not SessionId:
        return JSONResponse({"error": "No session"}, status_code=400)

    try:

        tile_index = int(data.tileIndex)
        Game = str(data.Game)
        currentMaxTileIndex = 0


        if Game == "Towers":
            htmlFile = "towers.html"
            htmlErrorType = "towers_error"
            currentMaxTileIndex = 24
        elif Game == "Mines":
            htmlFile = "mines.html"
            htmlErrorType = "mines_error"
            currentMaxTileIndex = 25
        else:
            return JSONResponse({"error": "Unknown game"}, status_code=400)

        keys = [
            SessionId + "minesdata",
            SessionId + "TowersActive",
            SessionId + "GameActive",
            SessionId + "Row",
            SessionId + ":cashed",
            SessionId + "BetAmount",
            "ClickData." + SessionId,
            SessionId + "Cleared",
            SessionId + "Cashout",
        ]

        mines_raw, towers_active, GameActive, currentRow, cashedAlready, bet_amount, data_raw, tilescleared,CashoutAvailable =  redis.mget(*keys)

        CashoutAvailable = CashoutAvailable or 0
        towers_active = str((towers_active))
        GameActive = str((GameActive))
        cashedAlready = str((cashedAlready))
        currentRow = int(currentRow or 0)
        tilescleared = int(tilescleared or 0)
        bet_amount = int(bet_amount or 0)

        if towers_active == "1" and Game != "Towers":
            return JSONResponse({"error": "Towers game is currently ongoing!"}, status_code=400)

        if GameActive is None:
            return JSONResponse({"error": "No active game"}, status_code=400)
        
        try:
            value = float(tile_index)
            if not value.is_integer():
                raise ValueError
            tile_index = int(tile_index)
        except (TypeError, ValueError):
                return returnTemplate("Request body must be whole numbers.", request, htmlErrorType, htmlFile,status.HTTP_400_BAD_REQUEST)
        
        if tile_index < 0 or tile_index > currentMaxTileIndex:
            return JSONResponse({"error": "Invalid tile"}, status_code=400)
        
        if mines_raw is None:
            return JSONResponse({"error": "No mines found"}, status_code=400)

        if Game == "Towers":
            row = 7 - (tile_index // 3)
            if row > currentRow:
                return JSONResponse(
                    {"error": "Row cannot be higher than current row!"},
                    status_code=400
                )
            
        lock_key = SessionId + ":click_lock"
        if not redis.set(lock_key, "1", nx=True,px=200):
            return JSONResponse({"error": "Processing click"}, status_code=400)

        clicks_key = SessionId + ":clicks"
        added =  redis.sadd(clicks_key, tile_index)
        if added == 0:
            return JSONResponse({"error": "Tile already clicked"}, status_code=400)

        if cashedAlready == "1":
            return JSONResponse({"error": "Game already cashed out"}, status_code=400)

        try:
            if isinstance(mines_raw, bytes):
                mines_raw = mines_raw.decode()
            mines = json.loads(mines_raw)
        except Exception:
            return JSONResponse({"error": "Invalid mines data"}, status_code=400)

        is_mine = tile_index in mines
        if is_mine:
            redis.delete(
                "ClickData." + SessionId,
                SessionId + "Cashout",
                SessionId + "BetAmount",
                SessionId + "Cleared",
                SessionId + ":clicks",
                SessionId + "GameActive",
                SessionId + "TowersActive"
            )
            return JSONResponse({"ismine": True, "mines": mines, "betamount": bet_amount})

        if data_raw:
            if isinstance(data_raw, bytes):
                data_raw = data_raw.decode()
            try:
                existing_array = json.loads(data_raw)
            except Exception:
                existing_array = []
        else:
            existing_array = []

        existing_array.append(tile_index)

        tilescleared += 1

        if Game == "Towers":
            mine_multiplier = ((len(mines) / 23) ** 1.5) + 0.1
            payout = bet_amount * (row + 1) * mine_multiplier * 0.3
            payout = math.floor(payout * 0.98)
            payoutset = int(CashoutAvailable) + int(payout)
            rowset = currentRow + 1
            redis.mset({
                "ClickData." + SessionId: json.dumps(existing_array),
                SessionId + "Cashout": str(payoutset),
                SessionId + "Row": str(rowset)
            })
            return JSONResponse({"ismine": False, "betamount": bet_amount, "minescount": len(mines)})
        elif Game == "Mines":
            total_tiles = 25
            multiplier_per_click = total_tiles / (total_tiles - len(mines))
            total_multiplier = multiplier_per_click ** tilescleared
            winnings = int(bet_amount * total_multiplier)
            winnings = math.floor(winnings * 0.98)
            redis.mset({
                SessionId + "Cashout": str(winnings),
                "ClickData." + SessionId: json.dumps(existing_array),
                SessionId + "Cleared": str(tilescleared)
            })
            return JSONResponse({"ismine": False})
        else:
            return JSONResponse({"error": "Unknown error"}, status_code=400)
    except Exception as e:
        print(str(e))
        traceback.print_exc()
        return JSONResponse({"error": "Error with click."}, status_code=400)


@app.post("/games/dice/play")
@limiter.limit("50/minute")
async def dicePlay(request : Request,SessionId : str = Cookie(None)):
    try:
        requestjson = await request.json()
        prediction = requestjson.get("prediction")
        betamount = requestjson.get("BetAmount")
        targetNumber = requestjson.get("targetNumber")
        mainMongo = getMainMongo()
        mainCollection = mainMongo["collection"]
        username = getCurrentUser(SessionId)

        if username.get("error"):
            return username
        
        RedisBalance = redis.get(SessionId)

        if not RedisBalance:
            return JSONResponse({"error": "Insufficient Funds."})
        
        try:
            betamount = int(betamount)
            RedisBalance = int(RedisBalance)
        except (TypeError, ValueError):
            return JSONResponse({"error": "Invalid bet amount or balance."})
        if int(RedisBalance) < int(betamount):
            return JSONResponse({"error": "Insufficient Funds."})
        if int(betamount) <= 0:
            return JSONResponse({"error": "Bet amount is negative or zero."})
        if prediction not in ["over","under"]:
            return JSONResponse({"error": "Invalid Prediction."})
        if int(targetNumber) < 2 or int(targetNumber) > 99:
            return JSONResponse({"error": "Invalid Target Number."})
        lock_key = f"DiceLock:{SessionId}"
        
        lock_acquired = redis.set(lock_key, 1, nx=True, px=500)  

        if not lock_acquired:
            return JSONResponse({"error": "Please wait a moment before trying again."})
        
        newDocument = mainCollection.find_one_and_update(
            {
                "username": username["username"], 
                "balance": {"$gte": betamount}  
            },
            {"$inc": {"balance": -betamount}},
            return_document=ReturnDocument.AFTER,
        )

        if not newDocument:
            return JSONResponse({"error": "Insufficient Funds."})
        
        RedisPipeline = redis.pipeline()
        newBalance = int(newDocument["balance"])
        RedisPipeline.set(SessionId,newBalance,ex = 2628000)

        randomInt = random.randint(0,100)

        if prediction == "under":
            Won = randomInt < targetNumber
            WinCount = targetNumber
        else:
            Won = randomInt > targetNumber
            WinCount = 100 - targetNumber

        WinChance = WinCount / 101

        if WinChance > 0:
            multiplier = 0.98 / WinChance
        else:
            multiplier = 0

        if Won:
            Payout = int(math.floor(betamount * multiplier))
            newDocument = mainCollection.find_one_and_update(
                {"username": username["username"]},
                {"$inc": {"balance": Payout}},
                return_document=ReturnDocument.AFTER,
            )

        if not newDocument:
            RedisPipeline.exec()
            return JSONResponse({"error": "User not found."})
            
        newBalance = int(newDocument["balance"])
        RedisPipeline.set(SessionId,newBalance,ex = 2628000)
        RedisPipeline.delete(lock_key)
        RedisPipeline.exec()
        return JSONResponse({"win": Won,"roll":randomInt})

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        return JSONResponse({"error": "Error playing dice."})

@app.post("/games/start",response_class=HTMLResponse)
@limiter.limit("50/minute")
async def gamestart(request : Request,SessionId: str = Cookie(None)):
    try:
        data = await request.json()
        bet_amount = data.get("betAmount")
        mine_count = data.get("mineCount")
        Game = data.get("Game")
        htmlFile = None
        htmlErrorType = None
        total_tiles = None

        def errorOut():
            return returnTemplate("",request,htmlErrorType,"login.html",status.HTTP_400_BAD_REQUEST)

        if not SessionId:
            return errorOut()
            
        if Game == "Towers":
            htmlFile = "towers.html"
            htmlErrorType = "towers_error"
            total_tiles = 24
        elif Game == "Mines":
            htmlFile = "mines.html"
            htmlErrorType = "mines_error"
            total_tiles = 25
        else:
            return returnTemplate("This game does not exist.",request,htmlErrorType,htmlFile,status.HTTP_400_BAD_REQUEST)

        if bet_amount is None or mine_count is None:
            return returnTemplate("Bet amount or mine count is none!",request,htmlErrorType,htmlFile,status.HTTP_400_BAD_REQUEST)
        
        try:
            if isinstance(bet_amount, float) or isinstance(mine_count, float):
                raise ValueError("No decimals allowed")
            
            mine_count = int(mine_count)
            bet_amount = int(bet_amount)
        except (TypeError, ValueError):
            return returnTemplate("Request body must be whole numbers.", request, htmlErrorType, htmlFile,status.HTTP_400_BAD_REQUEST)

        if int(mine_count) < 1:
            return returnTemplate("Must be over or equal to 1!",request,htmlErrorType,htmlFile,status.HTTP_400_BAD_REQUEST)
        
        if int(bet_amount) < 1:
            return returnTemplate("Cannot be a negative number!",request,htmlErrorType,htmlFile,status.HTTP_400_BAD_REQUEST)

        if int(mine_count) >= total_tiles:
            return returnTemplate("Mines cant be equal to or over the total tile count!",request,htmlErrorType,htmlFile,status.HTTP_400_BAD_REQUEST)

        def IfInsufficientFunds():
            return returnTemplate("Insufficient Funds!",request,htmlErrorType,htmlFile,status.HTTP_400_BAD_REQUEST)
        
        mainMongo = getMainMongo()
        mainCollection = mainMongo["collection"]

        username = getCurrentUser(SessionId)

        print(username)

        if username.get("error"):
            return username
        
        RedisBalance = redis.get(SessionId)

        if not RedisBalance:
            return IfInsufficientFunds()
        if int(RedisBalance) < int(bet_amount):
            return IfInsufficientFunds()

        mine_count = min(mine_count, total_tiles)  

        mines = random.sample(range(total_tiles), mine_count)

        newDocument = mainCollection.find_one_and_update(
            {"username": username["username"]},
            {"$inc": {"balance": -int(bet_amount)}},
            return_document=ReturnDocument.AFTER,
        )

        newBalance = int(newDocument["balance"])

        RedisPipeline = redis.pipeline()

        RedisPipeline.delete(
            SessionId + ":clicks",
            SessionId + ":cashed",
            "ClickData." + SessionId
        )

        RedisPipeline.set(SessionId,newBalance,ex = 2628000)

        if Game == "Towers":
            RedisPipeline.mset({
                SessionId + "GameActive": "1",
                SessionId + "Cleared": 0,
                SessionId + "Cashout": bet_amount,
                SessionId + "BetAmount": bet_amount,
                SessionId + "minesdata": json.dumps(mines),
                SessionId + "TowersActive": "1",
                SessionId + "Row": 0
            })
            result = RedisPipeline.exec()
            return RedirectResponse(url="/towers", status_code=303)
        elif Game == "Mines":
            RedisPipeline.mset({
                SessionId + "GameActive": "1",
                SessionId + "Cleared": 0,
                SessionId + "Cashout": 0,
                SessionId + "BetAmount": bet_amount,
                SessionId + "minesdata": json.dumps(mines),
            })
            result = RedisPipeline.exec()
            return RedirectResponse(url="/mines", status_code=303)
    except Exception as e:
        return RedirectResponse(url="/mines", status_code=303)


@app.post("/games/cashout")
@limiter.limit("50/minute")
def cashout(request: Request,SessionId: str = Cookie(None)):
    if not SessionId:
        return JSONResponse({"error": "No session"}, status_code=400)
    
    keys = [
        SessionId + "Cashout",
        SessionId + "minesdata",
        SessionId + "BetAmount",
        SessionId + "GameActive"
    ]

    tocashout,mines_raw,betamount,GameActive = redis.mget(*keys)

    if not GameActive:
        return JSONResponse({"error": "No active game"}, status_code=400)
    
    if mines_raw is None:
        return JSONResponse({"error": "No mines found"}, status_code=400)

    cashed_key = SessionId + ":cashed"
    if not redis.set(cashed_key, "1", nx=True,ex = 4):
        return JSONResponse({"error": "Already cashed out"}, status_code=400)

    tocashout = int(tocashout) or 0
    if tocashout <= 0:
        return JSONResponse({"error": "Nothing to cash out"}, status_code=400)

    redisPipeline = redis.pipeline()
    username = getCurrentUser(SessionId)

    if username.get("error"):
        return username

    mainCollection = getMainMongo()["collection"]
    newDocument = mainCollection.find_one_and_update(
        {"username": username["username"]},
        {"$inc": {"balance": tocashout}},
        return_document = ReturnDocument.AFTER
    )

    newBalance = int(newDocument["balance"])

    redisPipeline.set(SessionId,newBalance,ex = 2628000)

    if isinstance(mines_raw, bytes):
        mines_raw = mines_raw.decode()

    mines = json.loads(mines_raw)

    redisPipeline.delete(
        SessionId + "GameActive",
        SessionId + "Cleared",
        SessionId + "Cashout",
        SessionId + "BetAmount",
        "ClickData." + SessionId,
        SessionId + ":clicks",
        SessionId + "TowersActive"
    )

    redisPipeline.exec()

    return JSONResponse({"success": True, "amount": tocashout,"mines": mines,"betamount":betamount})


@app.post("/crypto/buy")
@limiter.limit("50/minute")
def buycurrency(request: Request):

    try:
        body_bytes = request.body()
        signature = request.headers.get("x-nowpayments-sig", "")

        expected_signature = hmac.new(
            NOWPAYMENTS_WEBHOOK_SECRET.encode().strip(),
            body_bytes,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return {"status": "ignored", "reason": "invalid signature"}

        payload = json.loads(body_bytes)


        if payload.get("payment_status") == "finished":
            user_id = payload.get("order_id")  
            amount_received = float(payload.get("pay_amount", 0))  
            amount_usd = float(payload.get("price_amount", 0))    
            CurrencyAmount  = math.floor(amount_usd) * 29000000

            if amount_usd >= 1:

                mainMongo = getMainMongo()
                mainCollection = mainMongo["collection"]
                OrderId = payload.get("order_id",None)
                if OrderId:
                    splitData = str(OrderId).split("_;")
                    SiteUserName = str(splitData[1])
    
                    try:
                        conn = getPostgresConnection() 
    
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT sessionid FROM accounts WHERE username = %s", (SiteUserName,))
    
                            result = cursor.fetchone()  
    
                            if not result:
                                return {"status": "ok"}
    
                            CurrentSessionId = str(result[0])
    
                    except Exception as error:
                        print("Error:", error)
    
                    newDocument = mainCollection.find_one_and_update(
                        {"username": SiteUserName, "sessionid": CurrentSessionId},
                        {"$inc": {"balance": int(CurrencyAmount)}},
                        return_document = ReturnDocument.AFTER,
                        upsert=True
                    )
    
                    newBalance = int(newDocument["balance"])
                    redis.set(CurrentSessionId,newBalance,ex = 2628000)
            else:
                print(f"Payment too small: ${amount_usd}, not credited.")
    except Exception as e:
        print("Error:", e)

    return {"status": "ok"}


@app.post("/register", response_class=HTMLResponse)
@limiter.limit("50/minute")
def register(request: Request,  username: str = Form(...),password: str = Form(...),confirm_password: str = Form(...)):

    SessionId = request.cookies.get("SessionId")

    if SessionId:
        return templates.TemplateResponse("home.html", {"request": request})

    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    if len(password) < 8:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password must be at least 8 characters long"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not re.fullmatch(r"^\w{3,20}$", username):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Username can only contain letters, numbers, and underscores (3-20 characters).", "username": username},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    session_id = secrets.token_urlsafe(32)

    email = ""  
    robloxusername = ""

    try:
        conn = getPostgresConnection() 
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    sessionid TEXT NOT NULL,
                    username VARCHAR(20) UNIQUE NOT NULL,
                    email VARCHAR(50) NOT NULL,
                    password VARCHAR(60) NOT NULL,
                    robloxusername VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

            cur.execute("""
                INSERT INTO accounts (username, email, password, sessionid,robloxusername)
                VALUES (%s, %s, %s, %s,%s)
                ON CONFLICT (username) DO NOTHING
                RETURNING id;
            """, (username, email, hashed_password, session_id,robloxusername))

            row = cur.fetchone()
            if row is None:
                return templates.TemplateResponse(
                    "register.html",
                    {"request": request, "error": "Username already exists", "username": username},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

    except Exception as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"{str(e)}", "username": username},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    ten_years_seconds = 10 * 365 * 24 * 60 * 60

    response = RedirectResponse(url="/home", status_code=303)
    response.set_cookie(
        key="SessionId",
        value=session_id,
        max_age=ten_years_seconds,
        httponly=True,
        path="/"
    )
    return response

@app.post("/login")
@limiter.limit("50/minute")

def login_post( request: Request,  username: str = Form(...),password: str = Form(...),):
    SessionId = request.cookies.get("SessionId")

    if SessionId:
        return templates.TemplateResponse("home.html", {"request": request})

    try:
        conn = getPostgresConnection() 

        with conn.cursor() as cursor:
            cursor.execute("SELECT password, sessionid FROM accounts WHERE username = %s", (username,))

            result = cursor.fetchone()  

            if result and bcrypt.checkpw(password.encode("utf-8"), result[0].encode("utf-8")):

                ten_years_seconds = 10 * 365 * 24 * 60 * 60

                response = RedirectResponse(url="/home", status_code=303)
                response.set_cookie(
                    key="SessionId",
                    value=result[1],
                    max_age=ten_years_seconds,
                    httponly=True,
                    path="/"
                )
                return response
            else:
                raise ValueError("Incorrect Password or username!")
        
    except Exception as error:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"{error}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.post("/createcoinflip", response_class=HTMLResponse)
@limiter.limit("50/minute")
async def CreateCoinflip(request : Request,  X_CSRF_Token: str = Header(None),SessionId: str = Cookie(None)):
    if not SessionId:
        return JSONResponse({"error": "No session"}, status_code=400)

    try:
        data = await request.json()
        coinflipData = data.get("coinflipData")
        Side = data.get("Side") 
        CSRFToken = getCSRFTokens(SessionId)
        if X_CSRF_Token != CSRFToken:
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Invalid CSRF token"}
            )

        Side = str(Side).capitalize()
        if Side not in ("Heads", "Tails"):
            raise ValueError("Not heads or tails")

        Username = CheckIfUserIsLoggedIn(
            request, "register.html", "coinflip.html", True
        )
        if Username is None:
            raise ValueError("No username")

        RobloxUsername = str(Username["robloxuser"])
        Username = str(Username["siteuser"])

        SiteItemsCollection = getSiteItemsMongo()["collection"]
        CoinflipCollection = getCoinflipMongo()["collection"]

        print(coinflipData)

        coinflipData = [
            {
                "itemid": int(item["itemid"]),
                "serial": int(str(item["serial"]).replace("#", "")),
                "itemname": str(item["itemname"]),
            }
            for item in coinflipData
        ]

        print(coinflipData)
        print(SessionId)

        document = SiteItemsCollection.find_one(
            {"SessionId": SessionId, "Username": Username}
        )

        if document is None:
            return JSONResponse(
                {"error": "You do not own any items!"},
                status_code=400
            )

        profile = {
            "Data": {
                "Inventory": {}
            }
        }

        ItemsVerified = 0

        for i in document["items"]:
            itemid = str(i["itemid"])
            serial = str(i["serial"])

            if itemid not in profile["Data"]["Inventory"]:
                profile["Data"]["Inventory"][itemid] = {}

            profile["Data"]["Inventory"][itemid][serial] = {}

        for i in coinflipData:
            inv = profile["Data"]["Inventory"]
            item_id = str(i["itemid"])

            if item_id in inv:
                inv2 = profile["Data"]["Inventory"][item_id]
                serial = str(i["serial"])
                if serial in inv2:
                    ItemsVerified += 1

        if ItemsVerified != len(coinflipData):
            return JSONResponse(
                {"error": "Item ownership verification failed!"},
                status_code=400
            )

        was_set = redis.set("CoinflipActive" + SessionId, True, nx=True)

        if not was_set:
            return JSONResponse(
                {"error": "Coinflip already active"},
                status_code=400
            )

        Operations = []

        for item in coinflipData:
            Operations.append(
                UpdateOne(
                    {"SessionId": SessionId, "Username": Username},
                    {
                        "$pull": {
                            "items": {
                                "itemid": item["itemid"],
                                "serial": item["serial"]
                            }
                        }
                    },
                )
            )

        if len(Operations) > 0:
            UpdateResult = SiteItemsCollection.bulk_write(Operations)
        else:
            return JSONResponse(
                {"error": "Bulk write operations list had no items!"},
                status_code=400
            )

        url = f"https://www.roblox.com/users/profile?username={RobloxUsername}"
        response = requests.get(url, allow_redirects=False)
        redirect_url = response.headers.get("Location")

        if redirect_url:
            UserId = int(redirect_url.split("/")[4])
            matchId = secrets.token_urlsafe(16)

            CoinflipCollection.insert_one({
                "MatchId": matchId,
                "SessionId": SessionId,
                "Username": Username,
                "UserId": UserId,
                "Side": Side,              
                "CoinflipItems": coinflipData,
                "CoinflipItems2": [],
                "UserId2": "",
                "Username2": "",
                "SessionId2": "",
            })

        else:
            return JSONResponse(
                {"error": "Redirect url not found!"},
                status_code=400
            )

        return JSONResponse({"success": True}, status_code=200)

    except Exception as e:
        print(e)
        return JSONResponse({"error": "Unknown error"}, status_code=400)


    
@app.post("/cancelcoinflip", response_class=HTMLResponse)
@limiter.limit("50/minute")
async def cancelCoinflip(request : Request,SessionId: str = Cookie(None)):

    data = await request.json()
    matchId = data.get("matchId")
    CoinflipCreator = data.get("CoinflipCreator")

    if not SessionId:
        return JSONResponse({"error": "No session"}, status_code=400)
    
    if not matchId:
        return JSONResponse({"error": "No matchid provided."}, status_code=400)
    
    if not CoinflipCreator:
        return JSONResponse({"error": "No cf creator provided."}, status_code=400)

    if not redis.set("CancelCF" + matchId, 1, nx=True, ex=4):
        return {"error": "Processing another request."}

    CoinflipCollection = getCoinflipMongo()["collection"]
    isCreator = CoinflipCreator == "true"
    Operations = []

    try:
        if isCreator:
            deleteddoc = CoinflipCollection.find_one_and_delete(
                    {"MatchId": matchId,"SessionId":SessionId}
                )

            if not deleteddoc:
                return JSONResponse({"error": "Coinflip no longer exists!"}, status_code=400)
            if deleteddoc and deleteddoc.get("CoinflipItems"):
                Operations.append(giveCancelCoinflipItems("CoinflipItems",deleteddoc,SessionId))
                Operations.append(giveCancelCoinflipItems("CoinflipItems2",deleteddoc,deleteddoc["SessionId2"]))
                if Operations:
                    SiteItemsCollection = getSiteItemsMongo()["collection"]
                    SiteItemsCollection.bulk_write(Operations)

                redis.delete("CoinflipActive" + SessionId)
                return JSONResponse({"success": True}, status_code=200)
        else:
            coinflipDocument = CoinflipCollection.find_one(
                {"MatchId": matchId,"SessionId2":SessionId}
            ) 

            if not coinflipDocument:
                return JSONResponse({"error": "Coinflip no longer exists!"}, status_code=400)
    
            giveCancelCoinflipItems("CoinflipItems2",coinflipDocument,SessionId)
            CoinflipCollection.update_one(
                {"MatchId": matchId},
                {
                    "$set": {
                        "CoinflipItems2": [],   
                        "UserId2": "",
                        "Username2": "",
                        "SessionId2": "",
                    }
                }
            )
            return JSONResponse({"success": True}, status_code=200)
        
    except Exception as e:
        print(str(e))
        return JSONResponse({"error": "Unknown error"}, status_code=400)


@app.post("/AcceptMatch",response_class =  HTMLResponse)
@limiter.limit("50/minute")
async def AcceptMatch(request: Request, SessionId: str = Cookie(None)):
    if not SessionId:
        return {"error": "No cookie provided"}
    
    data = await request.json()
    matchId = data.get("matchId")
    randomInt = random.randint(1,2)
    CoinflipCollection = getCoinflipMongo()["collection"]
    Updates = []

    if not redis.set("AcceptMatch." + SessionId, 1, nx=True, ex=4):
        return {"error": "Processing another request."}

    coinflipDocument = CoinflipCollection.find_one(
            {"MatchId": matchId,"SessionId":SessionId}
        )
    
    if not coinflipDocument:
        return JSONResponse({"error": "Coinflip no longer exists!"}, status_code=400)

    if coinflipDocument["UserId2"] != "":
        deleteResult =  CoinflipCollection.find_one_and_delete(
            {"MatchId": matchId,"SessionId":SessionId}
        )

        if deleteResult is None:
            return JSONResponse({"error": "Delete found no results."}, status_code=400)

        if randomInt == 1: # means p1 won shit system i know but ill make it better later
            Updates.append(giveCancelCoinflipItems("CoinflipItems",deleteResult,SessionId))
            Updates.append(giveCancelCoinflipItems("CoinflipItems2",deleteResult,SessionId))
            redis.delete("CoinflipActive" + SessionId)
        else:  # means p2 won shit system i know but ill make it better later
            Updates.append(giveCancelCoinflipItems("CoinflipItems",deleteResult,deleteResult["SessionId2"]))
            Updates.append(giveCancelCoinflipItems("CoinflipItems2",deleteResult,deleteResult["SessionId2"]))

        SiteItemsCollection = getSiteItemsMongo()["collection"]
        SiteItemsCollection.bulk_write(Updates)
    else:
        return JSONResponse({"error": "The other person who joined the match left unexpectedly."}, status_code=400)


    redisData = redis.get("CoinflipEnds")

    if redisData:
        if isinstance(redisData, bytes):
            redisData = redisData.decode()
        try:
            existing_array = json.loads(redisData)
        except Exception:
            existing_array = []
    else:
        existing_array = []

    if "_id" in deleteResult:
        deleteResult["_id"] = str(deleteResult["_id"])
    deleteResult["Winner"] = randomInt
    existing_array.append(deleteResult)

    creatorSide = str(deleteResult["Side"]).capitalize()
    WinningSide = None

    if randomInt == 1:
        WinningSide = creatorSide
    else:
        if creatorSide == "Heads":
            WinningSide = "Tails"
        else:
            WinningSide = "Heads"
            
    redis.set("CoinflipEnds",json.dumps(existing_array),ex=2000)

    return JSONResponse({"success": True,"winnerside": WinningSide})


@app.post("/JoinMatch",response_class =  HTMLResponse)
@limiter.limit("50/minute")
async def JoinMatch(request: Request, SessionId: str = Cookie(None)):
    try:
        if not SessionId:
            return {"error": "No cookie provided"}
        
        data = await request.json()

        if not redis.set("JoinMatch." + SessionId, 1, nx=True, ex=4):
            return {"error": "You are already joining another match"}

        print(data)

        rawitemdata = data.get("items", [])
        matchId = data.get("matchId")

        if not rawitemdata:
            return JSONResponse({"error": "No items provided"}, status_code=400)
                
        itemdata = {}
        
        for item in rawitemdata:
            if "#" not in item:
                continue
            name, serial = item.split("#")
            itemdata.setdefault(name, []).append(serial)

        sitename = getCurrentUser(SessionId)

        if sitename.get("error"):
            return sitename

        SiteItemsCollection = getSiteItemsMongo()["collection"]

        try:
            document = SiteItemsCollection.find_one({"SessionId": SessionId})
            if not document:
                return JSONResponse({"error": "Unknown error"}, status_code=400)
        except Exception as e:
            return JSONResponse({"error": "Unknown error"}, status_code=400)
        
        itemsData = document["items"]
        ItemsVerifiedCount = 0
        ItemDataFormatted = []

        for item_name, serials in itemdata.items():
            for serial in serials:
                for i,v in enumerate(itemsData):
                    if str(v["itemname"]) == str(item_name) and int(serial) == int(v["serial"]):
                        ItemsVerifiedCount += 1
                        ItemDataFormatted.append({
                            "itemname": item_name.strip(),
                            "serial": int(serial),
                            "itemid": int(v["itemid"])
                        })
                        break

        totalitems = sum(len(serials) for serials in itemdata.values())

        if ItemsVerifiedCount != totalitems:
            return JSONResponse({"error": "Item verification failed!"}, status_code=400)

        Username = CheckIfUserIsLoggedIn(
            request, "register.html", "coinflip.html", True
        )
        
        if Username is None:
            raise ValueError("No username")

        RobloxUsername = str(Username["robloxuser"])
        Username = str(Username["siteuser"])
        
        Operations = []

        for itemname,serials in itemdata.items():
            for serial in serials:
                Operations.append(
                    UpdateOne(
                        {"SessionId": SessionId},
                        {"$pull": {"items": {"itemname": itemname.strip(), "serial": int(serial)}}},
                    )
                )

        if len(Operations) > 0:
            print(itemdata)
            print(ItemDataFormatted)
            UpdateResult = SiteItemsCollection.bulk_write(Operations)
            CoinflipCollection = getCoinflipMongo()["collection"]
            url = f"https://www.roblox.com/users/profile?username={RobloxUsername}"
            response = requests.get(url, allow_redirects=False)
            redirect_url = response.headers.get("Location")
            UserId = int(redirect_url.split("/")[4])
            CoinflipCollection.update_one(
                {"MatchId": matchId},
                {
                    "$push": {
                        "CoinflipItems2": {
                            "$each": ItemDataFormatted
                        }
                    },
                    "$set": {
                        "UserId2": UserId,
                        "Username2": Username,
                        "SessionId2": SessionId,
                    }
                }
            )
        else:
            return JSONResponse({"error": "Bulk write operations list had no items!"}, status_code=400)
        
    except Exception as e:
        print(e)
        return JSONResponse({"error" : str(e)})

    return JSONResponse({"success": True})
