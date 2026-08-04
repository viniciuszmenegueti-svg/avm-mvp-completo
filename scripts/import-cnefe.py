"""Importa um CSV municipal oficial do CNEFE/IBGE para a base local.

O importador não baixa dados nem atribui precisão métrica. Ele preserva a versão,
o SHA-256 do arquivo-fonte e o nível posicional NV_GEO_COORD informado pelo IBGE.
"""

import argparse
import csv
import hashlib
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import select

from app.domain.city_model import CityModel
from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel
from app.infrastructure.database import SessionLocal
from app.services.cnefe_import_service import (
    activate_cnefe_import,
    fail_cnefe_import,
    start_cnefe_import,
)
from app.services.geocoding_service import (
    normalize_postal_code,
    normalize_text,
)


FIELD_ALIASES = {
    "provider_record_id": ("COD_UNICO_ENDERECO", "COD_ENDERECO", "ID_ENDERECO"),
    "city_ibge_code": ("COD_MUN", "COD_MUNICIPIO"),
    "postal_code": ("COD_CEP", "CEP"),
    "locality": ("NOM_LOCALIDADE", "DSC_LOCALIDADE"),
    "street_type": ("NOM_TIPO_SEGLOGR", "DSC_TIPO_LOGRADOURO"),
    "street_title": ("NOM_TITULO_SEGLOGR", "DSC_TITULO_LOGRADOURO"),
    "street_name": ("NOM_SEGLOGR", "NOM_LOGRADOURO"),
    "number": ("NUM_ENDERECO", "NUMERO"),
    "number_modifier": ("DSC_MODIFICADOR", "MODIFICADOR"),
    "latitude": ("LATITUDE",),
    "longitude": ("LONGITUDE",),
    "geocoding_level": ("NV_GEO_COORD",),
}

COMPLEMENT_FIELDS = (
    "DSC_COMP_ENDERECO_1",
    "DSC_COMP_ENDERECO_2",
    "DSC_COMP_ENDERECO_3",
    "DSC_COMP_ENDERECO_4",
    "DSC_COMP_ENDERECO_5",
    "NOM_COMP_ELEM1",
    "VAL_COMP_ELEM1",
    "NOM_COMP_ELEM2",
    "VAL_COMP_ELEM2",
    "NOM_COMP_ELEM3",
    "VAL_COMP_ELEM3",
    "NOM_COMP_ELEM4",
    "VAL_COMP_ELEM4",
    "NOM_COMP_ELEM5",
    "VAL_COMP_ELEM5",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--city-ibge-code", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--batch-size", type=int, default=5000)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_value(row: dict[str, str], field: str, required: bool = True) -> str:
    for alias in FIELD_ALIASES[field]:
        value = (row.get(alias) or "").strip()
        if value:
            return value
    if required:
        aliases = ", ".join(FIELD_ALIASES[field])
        raise ValueError(f"Campo obrigatório ausente ({aliases}).")
    return ""


def parse_coordinate(value: str) -> float:
    return float(value.replace(",", "."))


def build_record(
    row: dict[str, str],
    *,
    import_id: str,
    dataset_version: str,
    source_hash: str,
    city_ibge_code: str,
    state: str,
) -> dict[str, object]:
    row_city = first_value(row, "city_ibge_code", required=False)
    if row_city and row_city != city_ibge_code:
        raise ValueError(
            f"Município divergente no CSV: {row_city}; esperado {city_ibge_code}."
        )

    provider_record_id = first_value(row, "provider_record_id")
    street_type = first_value(row, "street_type", required=False)
    street_title = first_value(row, "street_title", required=False)
    street_name = first_value(row, "street_name")
    street = " ".join(part for part in (street_type, street_title, street_name) if part)
    number = first_value(row, "number")
    latitude = parse_coordinate(first_value(row, "latitude"))
    longitude = parse_coordinate(first_value(row, "longitude"))
    geocoding_level = int(first_value(row, "geocoding_level"))
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Coordenada fora dos limites geográficos.")
    if geocoding_level not in range(1, 7):
        raise ValueError("NV_GEO_COORD deve estar entre 1 e 6.")

    complement = " ".join(
        value.strip()
        for field in COMPLEMENT_FIELDS
        if (value := row.get(field)) and value.strip()
    )
    canonical = "|".join(
        (
            import_id,
            dataset_version,
            provider_record_id,
            normalize_postal_code(first_value(row, "postal_code")),
            normalize_text(street),
            normalize_text(number),
            f"{latitude:.7f}",
            f"{longitude:.7f}",
        )
    )
    record_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return {
        "record_key": record_key,
        "import_id": import_id,
        "provider_record_id": provider_record_id[:100],
        "dataset_version": dataset_version[:80],
        "source_file_sha256": source_hash,
        "city_ibge_code": city_ibge_code,
        "state": state,
        "postal_code": normalize_postal_code(first_value(row, "postal_code")),
        "locality": first_value(row, "locality", required=False)[:150] or None,
        "street": street[:250],
        "street_name": street_name[:200],
        "number": number[:40],
        "number_modifier": (
            first_value(row, "number_modifier", required=False)[:40] or None
        ),
        "complement": complement[:250] or None,
        "normalized_street": normalize_text(street)[:250],
        "normalized_street_name": normalize_text(street_name)[:200],
        "normalized_number": normalize_text(number)[:40],
        "latitude": latitude,
        "longitude": longitude,
        "geocoding_level": geocoding_level,
    }


def batches(items: Iterable[dict[str, object]], size: int) -> Iterable[list[dict]]:
    batch: list[dict] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def import_records(
    records: Iterable[dict[str, object]],
    batch_size: int,
    import_id: str,
) -> int:
    imported = 0
    with SessionLocal() as session:
        for batch in batches(records, batch_size):
            unique = {str(item["record_key"]): item for item in batch}
            existing = set(
                session.scalars(
                    select(CnefeAddressModel.record_key).where(
                        CnefeAddressModel.record_key.in_(unique)
                    )
                ).all()
            )
            new_records = [
                CnefeAddressModel(**item)
                for key, item in unique.items()
                if key not in existing
            ]
            session.add_all(new_records)
            imported += len(new_records)
            registry = session.get(CnefeImportModel, import_id)
            if registry is None:
                raise ValueError("Registro da importacao CNEFE nao encontrado.")
            registry.record_count = imported
            session.commit()
            print(f"Importados: {imported}", end="\r", flush=True)
    return imported


def main() -> None:
    args = parse_arguments()
    path = args.csv_file.resolve(strict=True)
    if args.batch_size < 1:
        raise ValueError("--batch-size deve ser positivo.")
    state = args.state.strip().upper()
    if len(state) != 2 or len(args.city_ibge_code) != 7:
        raise ValueError("UF ou código IBGE inválido.")

    with SessionLocal() as session:
        city = session.get(CityModel, args.city_ibge_code)
        if city is None or city.state != state:
            raise ValueError("A cidade/UF deve existir e estar coerente na base AVM.")

    source_hash = file_sha256(path)
    with SessionLocal() as session:
        registry = start_cnefe_import(
            session,
            dataset_version=args.dataset_version,
            source_file_sha256=source_hash,
            source_filename=path.name,
            city_ibge_code=args.city_ibge_code,
            state=state,
        )
    import_id = registry.import_id

    def records() -> Iterable[dict[str, object]]:
        with path.open("r", encoding=args.encoding, newline="") as source:
            reader = csv.DictReader(source, delimiter=";")
            if reader.fieldnames is None:
                raise ValueError("CSV sem cabeçalho.")
            for line_number, row in enumerate(reader, start=2):
                try:
                    yield build_record(
                        row,
                        import_id=import_id,
                        dataset_version=args.dataset_version,
                        source_hash=source_hash,
                        city_ibge_code=args.city_ibge_code,
                        state=state,
                    )
                except ValueError as error:
                    raise ValueError(f"Linha {line_number}: {error}") from error

    try:
        imported = import_records(records(), args.batch_size, import_id)
        with SessionLocal() as session:
            activate_cnefe_import(session, import_id)
    except Exception as error:
        with SessionLocal() as session:
            fail_cnefe_import(session, import_id, error)
        raise
    print()
    print(f"Registro da importacao: {import_id} (ACTIVE)")
    print(f"Importação concluída: {imported} novo(s) endereço(s).")
    print(f"SHA-256 da fonte: {source_hash}")


if __name__ == "__main__":
    main()
