import requests
from bs4 import BeautifulSoup
import urllib.parse
from typing import Optional, List
import imdb
import re
import datetime

class MovieInfo:
  rating: float
  genres: List[str]

  def __init__(self, rating: float, genres: List[str]) -> None:
    self.rating = rating
    self.genres = genres

  def __str__(self):
    return f"rating: {self.rating}, genres: {','.join(self.genres)}"


class ApiKeyImdbStrategy:
  api_key: str

  def __init__(self, api_key: str):
    self.api_key = api_key

  def find_movie(self, title: str, year: Optional[int]) -> Optional[str]:
    q = urllib.parse.quote(title) + '%20' +str(year)
    url = f'https://v3.sg.media-imdb.com/suggestion/x/{q}.json?includeVideos=0'
    response = requests.get(url)

    if response.status_code != 200:
      raise Exception(f'Can not call API, status code: {response.status_code}, error: {response.text}')

    resp_data = response.json()
    if len(resp_data['d']) == 0:
      return None

    movie = resp_data['d'][0]
    return movie['id'] if movie['y'] == year else None

  def get_movie_info(self, title: str, year: Optional[int]) -> Optional[MovieInfo]:
    # https://imdb-api.com/api/
    # https://imdb-api.com/en/API/UserRatings/k_e9n79f4d/tt4574334
    mov_id = self.find_movie(title, year)
    url = f'https://imdb-api.com/en/API/UserRatings/{self.api_key}/{mov_id}'
    response = requests.request("GET", url)
    data = response.json()
    if data['errorMessage']:
      raise Exception(f"Get imdb rating error: {data['errorMessage']}")

    return  MovieInfo(data['totalRating'], [])


class HttpImdbStrategy:

  def find_movie(self, title: str, year: Optional[int]) -> Optional[str]:
    q = urllib.parse.quote(title) + '%20' +str(year)
    url = f'https://v3.sg.media-imdb.com/suggestion/x/{q}.json?includeVideos=0'
    response = requests.get(url)

    if response.status_code != 200:
      raise Exception(f'Can not call API, status code: {response.status_code}, error: {response.text}')

    resp_data = response.json()
    if len(resp_data['d']) == 0:
      return None
    movie = resp_data['d'][0]
    return movie['id'] if movie['y'] == year else None

  def get_movie_info(self, title: str, year: Optional[int]) -> Optional[MovieInfo]:
    mov_id = self.find_movie(title, year)

    # https://www.imdb.com/title/tt1959490/
    url = f'https://www.imdb.com/title/{mov_id}'
    headers = {
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
      raise Exception(f'Can not crawl genres data: {response.status_code}, error: {response.text}')

    soup = BeautifulSoup(response.text, 'html.parser')
    genres = [genreTag.get_text().strip() for genreTag in soup.find_all(class_='iPPPLI')]
    ratingTag = soup.find(class_='gvYTvP')
    rating = None if ratingTag is None else float(ratingTag.get_text().strip())
    return  MovieInfo(rating, genres)

class CinemagoerImdbStrategy:
  ia = None

  def __init__(self):
    self.ia = imdb.Cinemagoer()

  def find_movie(self, title: str, year: Optional[int]) -> Optional[str]:
    movies = self.ia.search_movie(f'{title} {year}')
    return movies[0].movieID if len(movies) > 0 else None

  def get_movie_info(self, title: str, year: Optional[int]) -> Optional[MovieInfo]:
    mov_id = self.find_movie(title, year)
    movie = self.ia.get_movie(mov_id)
    rating = None if 'rating' not in movie else movie['rating']
    genres = None if 'genre' not in movie else movie['genre']
    return  MovieInfo(rating=rating, genres=genres)


class HttpNetflixStrategy:
  cookie = None

  def __init__(self, cookie: str):
      self.cookie = cookie

  def get_my_list(self):
    url = 'https://www.netflix.com/nq/website/memberapi/vc6b505ac/pathEvaluator?avif=false&webp=true&drmSystem=widevine&isVolatileBillboardsEnabled=true&routeAPIRequestsThroughFTL=false&isTop10Supported=true&isTop10KidsSupported=true&hasVideoMerchInBob=true&hasVideoMerchInJaw=true&persoInfoDensity=false&infoDensityToggle=false&contextAwareImages=true&enableMultiLanguageCatalog=false&usePreviewModal=true&falcor_server=0.1.0&withSize=true&materialize=true&original_path=%2Fshakti%2Fmre%2FpathEvaluator'
    maxItemIndex = 1000
    payload=f'path=%5B%22mylist%22%2C%5B%22id%22%2C%22listId%22%2C%22name%22%2C%22requestId%22%2C%22trackIds%22%5D%5D&path=%5B%22mylist%22%2C%7B%22from%22%3A0%2C%22to%22%3A{maxItemIndex}%7D%2C%5B%22availability%22%2C%22episodeCount%22%2C%22inRemindMeList%22%2C%22itemSummary%22%2C%22queue%22%2C%22summary%22%5D%5D&authURL=1656735386949.ilLXtrHw22MnWNrX3jwMASMQZwQ%3D'
    headers = {
      'content-type': 'application/x-www-form-urlencoded',
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
      'Cookie': self.cookie
    }
    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 200:
      raise Exception(f'Can not call API, status code: {response.status_code}, error: {response.text}')
    myListData = response.json()
    items = []
    for movId in myListData['jsonGraph']['videos']:
      # itemSummary / value {
      #     episodeCount, seasonCount, isOriginal, releaseYear
      #     boxArt / { url, width, height }
      #     maturity / rating / { value, specificRatingReason, maturityLevel }
      #   }
      video = myListData['jsonGraph']['videos'][movId]
      episode_cnt = video['itemSummary']['value']['seasonCount'] if 'seasonCount' in video['itemSummary']['value'] else None
      item = {
        'Netflix Id': video['itemSummary']['value']['id'],
        'Title': video['itemSummary']['value']['title'],
        'Release Year': video['itemSummary']['value']['releaseYear'],
        'Netflix Original': video['itemSummary']['value']['isOriginal'],
        'Episode Count': video['itemSummary']['value']['episodeCount'] if 'episodeCount' in video['itemSummary']['value'] else None,
        'Season Count': episode_cnt,
        'Maturity': video['itemSummary']['value']['maturity']['rating']['value'],
        'Maturity Level': video['itemSummary']['value']['maturity']['rating']['maturityLevel'],
        'Maturity Detail': video['itemSummary']['value']['maturity']['rating']['specificRatingReason'],
        'Image': video['itemSummary']['value']['boxArt']['url'],
        'Movie Type': 'Movie' if episode_cnt is None else 'TV Series'
      }
      items.append(item)
    return items

  def get_last_date_to_watch(self, movie_id):
    print(f'getting last date to watch for movie {movie_id}')
    url = f'https://www.netflix.com/title/{movie_id}'
    # url = f'https://www.netflix.com/title/60020686'
    headers = {
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
      'Cookie': self.cookie
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
      raise Exception(f'Can not call API, status code: {response.status_code}, error: {response.text}')

    pattern = r'Last\\x20day\\x20to\\x20watch\\x20on\\x20Netflix:\\x20([A-Za-z]+)\\x20(\d+)'
    match = re.search(pattern, response.text)
    expire_date = None
    if match:
        month_name = match.group(1)
        day = int(match.group(2))
        month = datetime.datetime.strptime(month_name, "%B").month
        current_date_time = datetime.date.today()
        expire_date = current_date_time.replace(month=month, day=day)
    return expire_date

# def getImdbMovId(mov):
#   # https://imdb-api.com/api/
#   title = mov['Title']

#   cacheKey = f'imdb-id-{title}'
#   cacheVal = getCache(cacheKey)
#   if cacheVal:
#     data = cacheVal
#   else:
#     search = urllib.parse.quote(f"{title} {mov['Release Year']}")
#     # search = urllib.parse.quote(title)
#     if mov['Movie Type'] == 'Movie':
#       url = f'https://imdb-api.com/en/API/SearchMovie/{IMDB_API_KEY}/{search}'
#     else:
#       url = f'https://imdb-api.com/en/API/SearchSeries/{IMDB_API_KEY}/{search}'
#     logging.info(f'Finding movie with title: "{title}"')
#     response = requests.request("GET", url)
#     data = response.json()

#     # TODO: check release year in movie description

#     if data['errorMessage']:
#       raise Exception(f"Get imdb movie id error: {data['errorMessage']}")
#     setCache(cacheKey, data)

#   if len(data['results']) < 1:
#     raise Exception(f'Movie with title {title} not found')

#   mov['Imdb Id'] = data['results'][0]['id']
