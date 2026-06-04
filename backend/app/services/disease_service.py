import requests

class DiseaseService:

    BASE_URL = "https://disease.sh/v3/covid-19"

    @staticmethod
    def get_country_health(country):

        response = requests.get(
            f"{DiseaseService.BASE_URL}/countries/{country}"
        )

        return response.json()