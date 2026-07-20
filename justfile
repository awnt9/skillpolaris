lint file=".":
    @uv run ruff check {{file}}

fix file=".":
    @uv run ruff check --fix {{file}}

format file=".":
    @uv run ruff format {{file}}

delete_cache:
    powershell.exe -Command "Get-ChildItem -Path . -Filter '__pycache__' -Recurse | Remove-Item -Force -Recurse"

extract:
    uv run --package pipeline python -m pipeline.extract.main

transform:
    uv run --package pipeline python -m pipeline.transform.main

compose *args:
    docker compose -f infra/docker-compose.yml --env-file .env {{args}}

update_image image:
    @echo "Iniciando proceso para {{image}}..."

    docker build -t antoniobrrg/{{image}}:latest -f apps/pipeline/Dockerfile.{{image}} .

    docker login

    docker push antoniobrrg/{{image}}:latest

    @echo "¡Imagen actualizada y subida con éxito!"
