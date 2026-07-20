from abc import ABC, abstractmethod
import requests
from pipeline.extract.models import JobRoomSwissRequestTemplate,FranceTravailRequestTemplate,USAJOBSRequestTemplate
from json import JSONDecodeError
from requests import RequestException
from functools import wraps
import os
from dotenv import load_dotenv
from rich import print

def handle_api_errors(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        class_name = self.__class__.__name__
        
        try:
            return func(self, *args, **kwargs)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 403:
                print(f"[bold red][{class_name}] Forbidden (403): Possible block of IP or User-Agent.[/]")
            elif status == 429:
                print(f"[bold red][{class_name}] Too Many Requests (429)[/]")
            else:
                print(f"[bold red][{class_name}] HTTP Error {status}: {e}[/]")
            return []
        except JSONDecodeError:
            print(f"[bold red][{class_name}] Error: response is not a valid JSON.[/]")
            return []
        except RequestException as e:
            print(f"[bold red][{class_name}] Error: {e}[/]")
            return []
        except (KeyError, TypeError) as e:
            print(f"[bold red][{class_name}] Error on response structure: {e}[/]")
            return []
    return wrapper

class BaseExtractor(ABC):
    def __init__(self,configuration):
        self.session = requests.Session()
        self.configuration = configuration

    @abstractmethod
    def get_ids(self):
        """Method wich gets ids from job offers"""
        pass

    @abstractmethod
    def get_detail(self):
        """Method wich gets details from a job offer with a specific ID"""
        pass

class SwissJobRoomExtractor(BaseExtractor):

    @handle_api_errors
    def get_ids(self, keyword, page):
        url = f"https://www.job-room.ch/jobadservice/api/jobAdvertisements/_search?size=15&page={page}"
        payload = JobRoomSwissRequestTemplate(keywords=[keyword]).model_dump()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": "https://www.job-room.ch/"
            })

        res = self.session.post(url, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        found_ids = [item['jobAdvertisement']['id'] for item in data if 'jobAdvertisement' in item]

        return found_ids

    @handle_api_errors
    def get_detail(self, job_id):
        url = f"https://www.job-room.ch/jobadservice/api/jobAdvertisements/{job_id}"

        res = self.session.get(url, timeout=10)
        res.raise_for_status() 

        if res.status_code == 204:
            return None
        
        return res.text
            
class FranceTravailExtractor(BaseExtractor):
    def __init__(self,configuration):
        super().__init__(configuration=configuration)
        self.client_id = self.configuration.france_travail_client_id
        self.client_secret = self.configuration.france_travail_client_secret
        self.access_token = self._get_access_token()
        
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}"
            })

    def _get_access_token(self):
        url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre" 
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                raise Exception(f"ERROR: unable to get access token on FranceTravail\n response text: {response.text}")
            
        except Exception as e:
            print(e)
            
    @handle_api_errors
    def get_ids(self, keyword, page):
        url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
        range = f"{20*page}-{20*page+19}"
        params = FranceTravailRequestTemplate(motsCles=keyword,range=range).model_dump(exclude_none=True)
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        })
        
        res = self.session.get(url, params=params, timeout=10)
        res.raise_for_status()
        
        if res.status_code == 204:
            return []
            
        if res.status_code == 200 or res.status_code == 206:
            data = res.json()
            return [item['id'] for item in data.get('resultats', [])]

    @handle_api_errors
    def get_detail(self, job_id):
        url = f"https://api.francetravail.io/partenaire/offresdemploi/v2/offres/{job_id}"

        res = self.session.get(url, timeout=10)
        res.raise_for_status() 
        
        if res.status_code == 204:
            return None
        return res.text
        
class USAJOBExtractor(BaseExtractor):
    def __init__(self,configuration):
        super().__init__(configuration=configuration)
        self.api_key = self.configuration.usajobs_api_key
        self.email = self.configuration.usajobs_email
        
        self.session.headers.update({
            "Host": "data.usajobs.gov",
            "User-Agent": self.email,
            "Authorization-Key": self.api_key,
            "Accept": "application/json"
        })

    @handle_api_errors
    def get_ids(self, keyword, page):
        url = "https://data.usajobs.gov/api/search"
        params = USAJOBSRequestTemplate(
            Keyword=keyword, 
            ResultsPerPage=20,
            WhoMayApply="Public",
            Page=page+1
        ).model_dump(exclude_none=True)
        
        res = self.session.get(url, params=params, timeout=10)
        res.raise_for_status() 
        data = res.json()

        found_ids = [job["MatchedObjectId"] for job in data["SearchResult"]["SearchResultItems"]]
        
        return found_ids
    
    @handle_api_errors
    def get_detail(self, job_id):
        url = "https://data.usajobs.gov/api/search"
        params = USAJOBSRequestTemplate(
            Keyword=job_id
        ).model_dump(exclude_none=True)
        
        res = self.session.get(url, params=params, timeout=10)
        res.raise_for_status()
        if res.status_code == 204:
            return None
        return res.text
            