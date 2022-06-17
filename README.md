# Требования

* poetry (>= 1.0)

## Установка зависимостей

### poetry
```
curl -sSL https://install.python-poetry.org | python3 -
```

# Запуск

```
poetry install
poetry run start --host=0.0.0.0 --port=8080
```

# Конфигурация среды разработки

Для поддержания единого стиля кода были созданы pre-commit хуки, которые устанавливаются следующим образом:

```
poetry run pre-commit install
```