class UnsupportedCityError(Exception):
    def __init__(
        self,
        city_ibge_code: str,
    ) -> None:
        self.city_ibge_code = city_ibge_code

        super().__init__(
            "A cidade informada não está habilitada "
            "para processamento de AVM."
        )
