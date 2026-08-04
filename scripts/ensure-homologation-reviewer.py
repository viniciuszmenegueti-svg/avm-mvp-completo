"""Ensure that homologation has independent trainer/reviewer credentials.

The script never prints credential values and preserves every unrelated line.
The generated file remains ignored by Git.
"""

import argparse
import json
import os
import secrets
from pathlib import Path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env.homologation"))
    return parser.parse_args()


def ensure_reviewer(path: Path) -> tuple[int, bool]:
    if not path.is_file():
        raise RuntimeError(f"Arquivo de ambiente não encontrado: {path}")
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    prefix = "ADMIN_CREDENTIALS_JSON="
    index = next(
        (position for position, line in enumerate(lines) if line.startswith(prefix)),
        None,
    )
    if index is None:
        raise RuntimeError("ADMIN_CREDENTIALS_JSON não foi encontrado.")
    try:
        credentials = json.loads(lines[index][len(prefix) :])
    except json.JSONDecodeError as error:
        raise RuntimeError("ADMIN_CREDENTIALS_JSON contém JSON inválido.") from error
    if not isinstance(credentials, dict) or not credentials:
        raise RuntimeError("ADMIN_CREDENTIALS_JSON deve conter um treinador.")
    if any(not isinstance(key, str) for key in credentials.values()):
        raise RuntimeError("ADMIN_CREDENTIALS_JSON contém chave inválida.")
    changed = False
    if len(credentials) < 2:
        actor = "model-reviewer"
        suffix = 1
        while actor in credentials:
            suffix += 1
            actor = f"model-reviewer-{suffix}"
        generated = secrets.token_urlsafe(36)
        while generated in credentials.values():
            generated = secrets.token_urlsafe(36)
        credentials[actor] = generated
        lines[index] = prefix + json.dumps(
            credentials,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        changed = True
    return len(credentials), changed


def main() -> None:
    args = parse_arguments()
    count, changed = ensure_reviewer(args.env_file.resolve())
    action = "adicionada" if changed else "já configurada"
    print(f"Credencial independente de revisão {action}.")
    print(f"Identidades administrativas configuradas: {count}")
    print("Valores secretos não foram exibidos.")


if __name__ == "__main__":
    main()
