import requests

class NutritionService:

    BASE_URL = "https://world.openfoodfacts.org/api/v2"

    @staticmethod
    def search_food(product_name):

        response = requests.get(
            f"{NutritionService.BASE_URL}/search",
            params={
                "search_terms": product_name
            }
        )

        return response.json()