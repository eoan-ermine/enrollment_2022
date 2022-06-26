# Что внутри?

Приложение упаковано в docker-контейнер и разворачивается с помощью [ansible](https://www.ansible.com/) ([инструкция по установке](https://www.ansible.com/)).
Внутри docker-контейнера доступны две команды: `analyzer-db` — утилита для управления состоянием базы данных и `analyzer-api` — утилита для запуска REST API сервиса.

# Как использовать?

## Как применить миграции

```bash
docker run -it \
    -e ANALYZER_PG_URL=postgresql://analyzer:root@localhost/analyzer \
    patriotrossii/enrollment_2020 analyzer-db upgrade head
```

## Как запустить REST API сервис локально на порту 80:

```bash
docker run -it -p 80:80 \
    -e ANALYZER_PG_URL=postgresql://analyzer:root@localhost/analyzer \
    patriotrossii/enrollment_2020
```

Все доступные опции запуска любой команды можно получить с помощью аргумента `--help`:

```bash
docker run patriotrossii/enrollment_2020 analyzer-db --help
docker run patriotrossii/enrollment_2020 analyzer-api --help
```

## Как развернуть?

Чтобы развернуть и запустить сервис на серверах, добавьте список серверов (с установленной Ubuntu) в файл `deploy/hosts.ini` и выполните команды:

``` bash
cd deploy
ansible-playbook -i hosts.ini --user=root deploy.yml
```

# Разработка

Требования: установленный [python](https://python.org) (3.8+) и [poetry](https://python-poetry.org/) ([инструкция по установке](https://python-poetry.org/docs/))

## Быстрые команды

-   `make` — отобразить список доступных команд
-   `make devenv` — создать и настроить виртуальное окружение для разработки
-   `make postgres` — поднять Docker-контейнер с PostgreSQL
-   `make format` — проверить на соответствие стандартам и отформатировать код с помощью `isort`, `black` и `flake8`
-   `make clean` — удалить файлы, созданные модулем [distutils](https://docs.python.org/3/library/distutils.html)
-   `make test` — запустить тесты
-   `make sdist` — создать [source distribution](https://packaging.python.org/glossary/)
-   `make docker` — собрать Docker-образ
-   `make upload` — загрузить docker-образ на ghcr.io (требуется авторизация)

## Как подготовить окружение для разработки?

``` bash
make devenv
make postgres
poetry run analyzer-db update head
poetry run analyzer-api
```

После запуска команд приложение начнет слушать запросы на `127.0.0.1:80`.

## Как запустить тесты локально?

```bash
make devenv
make postgres
poetry run pytest
```

## Как запустить нагрузочное тестирование?

Для запуска [locust](https://locust.io) необходимо выполнить следующие команды:

```bash
make devenv
poetry run locust {scenario_name} --web-host=127.0.0.1
```

Где `{scenarion_name}` — название сценария. Доступные сценарии:

| Название сценария | Описание сценарий |
| ------- | --- |
| ImportUser | Сценарий для измерения общей производительности импорта |
| HierarchyStressUser | Сценарий для измерения производительности механизма создания иерархий |

После этого станет доступен веб-интерфейс по адресу <http://localhost:8089>