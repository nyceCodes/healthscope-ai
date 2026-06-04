import requests

class CountryService:

    BASE_URL = "https://restcountries.com/v3.1/name"

    @staticmethod
    def get_country(country):

        response = requests.get(
            f"{CountryService.BASE_URL}/{country}"
        )

        return response.json()