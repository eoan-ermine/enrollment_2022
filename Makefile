PROJECT_NAME ?= enrollment_2022
VERSION = $(shell poetry version -s)
PROJECT_NAMESPACE ?= patriotrossii

REGISTRY_NAME ?= ghcr.io
REGISTRY_IMAGE ?= $(REGISTRY_NAME)/$(PROJECT_NAMESPACE)/$(PROJECT_NAME)

all:
	@echo "make devenv		- Create & setup development virtual environment"
	@echo "make format		- Format code with pre-commit hooks"
	@echo "make postgres	- Start postgres container"
	@echo "make clean		- Remove files created by distutils"
	@echo "make test		- Run tests"
	@echo "make sdist		- Make source distribution"
	@echo "make docker		- Build a docker image"
	@echo "make upload		- Upload docker image to the registry"
	@exit 0

clean:
	rm -rf dist

devenv: clean
	rm -rf `poetry env info -p`
	poetry install
	poetry run pre-commit install

format:
	poetry run pre-commit run --all-files

postgres:
	docker stop analyzer-postgres || true
	docker run --rm --detach --name=analyzer-postgres \
		--env POSTGRES_USER=analyzer \
		--env POSTGRES_PASSWORD=root \
		--env POSTGRES_DB=analyzer \
		--publish 5432:5432 postgres

test: postgres
	poetry run pytest

sdist: clean
	poetry build

docker: sdist
	docker build --target=final -t $(PROJECT_NAME):$(VERSION) .

upload: docker
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):$(VERSION)
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):latest
	docker push $(REGISTRY_IMAGE):$(VERSION)
	docker push $(REGISTRY_IMAGE):latest
