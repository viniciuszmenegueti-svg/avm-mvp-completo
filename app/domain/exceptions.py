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


class CityDataMismatchError(Exception):
    def __init__(
        self,
        city_ibge_code: str,
        expected_city: str,
        expected_state: str,
    ) -> None:
        self.city_ibge_code = city_ibge_code
        self.expected_city = expected_city
        self.expected_state = expected_state

        super().__init__(
            "O nome da cidade ou a UF não corresponde "
            "ao código IBGE informado."
        )
