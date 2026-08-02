from functools import wraps
from json import JSONDecodeError

import requests
from requests import RequestException
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
                print(
                    f"[bold red][{class_name}] Forbidden (403): "
                    f"Possible block of IP or User-Agent.[/]"
                )
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
