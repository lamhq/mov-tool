import requests
import urllib.parse
import json
from math import isnan
import pandas as pd
from os.path import exists
from os import makedirs
import string
import logging

logging.basicConfig(level=logging.INFO)

MOV_LST_FILE = 'data/movies.csv'
IMDB_API_KEY = 'k_e9n79f4d'

def loadMovieList():
  return pd.read_csv(MOV_LST_FILE, index_col='Netflix Id')

def saveMovieList(df):
  return df.to_csv(MOV_LST_FILE)

def updateMovieDb():
  movRecords = getNetflixMovList()
  if exists(MOV_LST_FILE):
    df = loadMovieList()
    for record in movRecords:
      if not record['Netflix Id'] in df.index:
        df = pd.concat([df, pd.DataFrame.from_records([record], index='Netflix Id')])
        logging.info(f"Adding new movie {record['Title']}")
  else:
    df = pd.DataFrame.from_records(movRecords, index='Netflix Id')

  # get rating
  for index, mov in df.iterrows():
    if not shouldGetRating(df.loc[index]):
      continue
    try:
      df.loc[index, 'Rating'] = getImdbRating(mov['Title'])
    except:
      logging.warning('Error when getting movie rating')

  # get last day to watch
  # save mov data
  df.to_csv(MOV_LST_FILE)
  return df


def getNetflixMovList():
  cacheKey = 'nflx-mov-list'
  cacheVal = getCache(cacheKey)
  if cacheVal:
    return cacheVal

  url = 'https://www.netflix.com/nq/website/memberapi/v267c6c70/pathEvaluator?avif=false&webp=true&drmSystem=widevine&isVolatileBillboardsEnabled=true&routeAPIRequestsThroughFTL=false&isTop10Supported=true&isTop10KidsSupported=true&hasVideoMerchInBob=true&hasVideoMerchInJaw=true&persoInfoDensity=false&infoDensityToggle=false&contextAwareImages=true&enableMultiLanguageCatalog=false&usePreviewModal=true&falcor_server=0.1.0&withSize=true&materialize=true&original_path=%2Fshakti%2Fv267c6c70%2FpathEvaluator'
  maxItemIndex = 1000
  payload=f'path=%5B%22mylist%22%2C%5B%22id%22%2C%22listId%22%2C%22name%22%2C%22requestId%22%2C%22trackIds%22%5D%5D&path=%5B%22mylist%22%2C%7B%22from%22%3A0%2C%22to%22%3A{maxItemIndex}%7D%2C%5B%22availability%22%2C%22episodeCount%22%2C%22inRemindMeList%22%2C%22itemSummary%22%2C%22queue%22%2C%22summary%22%5D%5D&authURL=1656735386949.ilLXtrHw22MnWNrX3jwMASMQZwQ%3D'
  headers = {
    'content-type': 'application/x-www-form-urlencoded',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    'Cookie': 'memclid=b783e450-fa77-488c-b3e2-beff624d26da; nfvdid=BQFmAAEBEEVEA6OC5bEMUUnOPrODS8pgtswkpg-fPl9nVBvzgBL6h4xcvm1AW25uw7kCk3ontTzlyk_IFIznVD7tQB97u8Sb9yS3ZTnKWCiKr7ML5MnwT0FDrZ5vU5D__d-e0TaPHF35IjWRoAUBT5CD29YZRJBC; cL=1656564126253%7C165656412298379229%7C165656412237010303%7C%7C4%7Cnull; SecureNetflixId=v%3D2%26mac%3DAQEAEQABABQ4A9El3mFYUqUKCkYGIkttFT-NGkHCdlA.%26dt%3D1656735386889; NetflixId=ct%3DBQAOAAEBEGywe9cwOTu6wOui3wdHeoyCELD3JDrWo1Ixd16GNT19-9WYxRXzn4yAqAWBe7Q8Ts6_z7ZTl93e3RYToHks-d6To43HAqQQGFeRVJrxyWtK1tGio7p5sb43hJJhw3pabc3JVABBdRFdmYuc1T69zRNl7zbaL-MoLO30ztsA8qo9G8eoYprxEYIorpnN1a4ktC_EswHyitH9oDebgmWU0OhtLUleC2sGQg0uAiOFJtrJpiljaigLopsxLjnPj2Fa9DJR4vsIDTN3hzuexkg7q_I1ta9Fc08VDC4JTOA1cRLld1fsl-sGwsCpyjxCu_2dVvRnx-L60KiAD04BdRqfuvLdDu_JACScRcZ-sAHmIAaUiX-_Tmps2mumHjGHCzl42dUjkqXL9N0q4MHC9o4xVLGZ6UMHWv8s12KihVXoaK3WXab7jPnfZ94iTLsUDbpT8Z0LwGxhLv6ckXE9gelc_Pg6GRyOZhnmrTCF_nBD8D4cA3vHhjpJ-4Mwc0eVH_sXn2XpgOSk_zel3lw5KvihnU_m32Tq5jE4Ls7FCAWDtxL9pKXOiVypICrKrIMdNYAh78kYsPgMTWJxua59n0I_FyKCfPPmM1xFcmBSj6kZKFowSYzC3nI0hM4fDB0JT13A7qhWt7DZLmW3DyPlRPGUaEZyBb_YqfV7gLN7pGI-9lVmegmKKpeEv7dJdbMFS6gE9DX58LvE9Zlzj7lIwZhQOkzv4g..%26bt%3Ddbl%26ch%3DAQEAEAABABRZ15hrwaNojow8x1xH56QfC7r5vgbKxCI.%26v%3D2%26mac%3DAQEAEAABABSlloS_xpeNFWOABqutaMm78nLruDvbw1w.; OptanonConsent=isIABGlobal=false&datestamp=Sat+Jul+02+2022+11%3A16%3A28+GMT%2B0700+(Indochina+Time)&version=6.6.0&consentId=22b81ae4-c299-4a0c-ac36-055cb8f2e01c&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1&hosts=H12%3A1%2CH13%3A1%2CH51%3A1%2CH45%3A1%2CH46%3A1%2CH52%3A1%2CH48%3A1%2CH49%3A1&AwaitingReconsent=false; profilesNewSession=0'
  }

  response = requests.request("POST", url, headers=headers, data=payload)

  if response.status_code != 200:
    raise Exception(f'Can not call API, status code: {response.status_code}, error: {response.text}')

  result = convertNetflixMoviesToRecords(response.text)
  setCache(cacheKey, result)
  return result;


def getImdbRating(title):
  cacheKey = f'imdb-rating-{title}'
  cacheVal = getCache(cacheKey)
  if cacheVal:
    data = cacheVal
  else:
    imdbId = getImdbMovId(title)
    # https://imdb-api.com/api/#Ratings-header
    # https://imdb-api.com/en/API/UserRatings/k_e9n79f4d/tt4574334
    url = f'https://imdb-api.com/en/API/UserRatings/{IMDB_API_KEY}/{imdbId}'
    logging.info(f'Getting rating of movie: "{imdbId}"')
    response = requests.request("GET", url)
    data = response.json()
    if data['errorMessage']:
      raise Exception(f"Get imdb rating error: {data['errorMessage']}")
    setCache(cacheKey, data)

  return data['totalRating']


def getImdbMovId(title):
  cacheKey = f'imdb-id-{title}'
  cacheVal = getCache(cacheKey)
  if cacheVal:
    data = cacheVal
  else:
    encodedTitle = urllib.parse.quote(title);
    # https://imdb-api.com/en/API/Search/k_e9n79f4d/stranger%20things
    url = f'https://imdb-api.com/en/API/Search/{IMDB_API_KEY}/{encodedTitle}'
    logging.info(f'Finding movie with title: "{title}"')
    response = requests.request("GET", url)
    data = response.json()
    if data['errorMessage']:
      raise Exception(f"Get imdb movie id error: {data['errorMessage']}")
    setCache(cacheKey, data)

  if len(data['results']) < 1:
    raise Exception(f'Movie with title {title} not found')

  return data['results'][0]['id']


def convertNetflixMoviesToRecords(apiRespText):
  # jsonGraph / videos / {80229873}
  data = json.loads(apiRespText)
  videos = data['jsonGraph']['videos']
  movies = [ convertMovieItemToRecord(videos[mvId]) for mvId in videos]
  return movies


def convertMovieItemToRecord(video):
  # itemSummary / value {
  #     episodeCount, seasonCount, isOriginal, releaseYear
  #     boxArt / { url, width, height }
  #     maturity / rating / { value, specificRatingReason, maturityLevel }
  #   }
  return {
    'Netflix Id': video['itemSummary']['value']['id'],
    'Title': video['itemSummary']['value']['title'],
    'Release Year': video['itemSummary']['value']['releaseYear'],
    'Netflix Original': video['itemSummary']['value']['isOriginal'],
    'Episode Count': video['itemSummary']['value']['episodeCount'] if 'episodeCount' in video['itemSummary']['value'] else None,
    'Season Count': video['itemSummary']['value']['seasonCount'] if 'seasonCount' in video['itemSummary']['value'] else None,
    'Maturity': video['itemSummary']['value']['maturity']['rating']['value'],
    'Maturity Level': video['itemSummary']['value']['maturity']['rating']['maturityLevel'],
    'Maturity Detail': video['itemSummary']['value']['maturity']['rating']['specificRatingReason'],
    'Image': video['itemSummary']['value']['boxArt']['url'],
  }

def shouldGetRating(mov):
  isNotNlfxOrg = not mov['Netflix Original']
  doNotHaveRating = ('Rating' not in mov) or (isnan(mov['Rating']))
  return isNotNlfxOrg and doNotHaveRating


CACHE_DIR = 'cache'


def sanitizeFileName(s):
  valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
  return ''.join(c for c in s.replace(" ", "-").lower() if c in valid_chars)

def getCache(key):
  cacheFile = f'{CACHE_DIR}/{sanitizeFileName(key)}.json'

  if not exists(cacheFile):
    return None

  f = open(cacheFile)
  data = json.load(f)
  f.close()
  return data


def setCache(key, value):
  cacheFile = f'{CACHE_DIR}/{sanitizeFileName(key)}.json'

  if not exists(CACHE_DIR):
    makedirs(CACHE_DIR)

  out_file = open(cacheFile, "w", encoding='utf-8')
  json.dump(value, out_file, indent = 2)
  out_file.close()

# updateMovieDb()
