import asyncio
import os
import subprocess
import sys
from typing import Optional

from Source import parsing
from Source.database.models import init_db


def ensure_dependencies_installed(requirements_file: Optional[str] = "requirements.txt") -> None:
  
    if not requirements_file:
        return

    if not os.path.exists(requirements_file):
        return

    try:
        with open(os.devnull, "wb") as devnull:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file],
                stdout=devnull,
                stderr=devnull,
            )
    except Exception:
        return


def show_help() -> None:
    print(
        """Российский геокодер.

Ввод:
    Одна строка в свободной форме, например:
        Екатеринбург, Белинского 86
        Москва, Тверская 10
        56.8225650, 60.6177568
        56.8225650 60.6177568

Программа сама определит, ввели вы координаты или адрес.

Специальные команды:
    --help      — показать эту справку
    --examples  — показать примеры запросов
    exit / выход — завершить работу
"""
    )


def show_examples() -> None:
    """Выводит примеры запросов и ожидаемого результата."""
    print(
        """Пример 1 — поиск координат по адресу

Ввод:
    Екатеринбург, Белинского 86

Вывод (примерно, формат JSON):
    {
        Широта: 56.7928003,
        Долгота: 60.6165292,
        Полный адрес: "86 Белинского улица; Екатеринбург; Свердловская область; 620089; Россия"
    }


Пример 2 — поиск по уже известным координатам

Ввод:
    56.8225650, 60.6177568
"""
    )


async def handle_query(query: str) -> None:
    """Обрабатывает одну строку запроса: адрес или координаты."""
    await parsing.handle_free_query(query)


async def interactive_mode() -> None:
    print("Введите 'exit' или 'выход' для завершения, '--help' для справки.")

    prompt = "Введите адрес в свободной форме (например: 'Екатеринбург, Белинского 86' или '56.8225650, 60.6177568'): "

    try:
        while True:
            raw = input(f"\n{prompt}").strip()
            lower = raw.lower()

            if not raw:
                continue
            if lower in ("exit", "выход"):
                print("Завершение работы.")
                return
            if lower in ("--help", "-h"):
                show_help()
                continue
            if lower == "--examples":
                show_examples()
                continue

            await handle_query(raw)
    except (EOFError, KeyboardInterrupt):
        print("\nЗавершение работы.")


async def main() -> None:
    await init_db()

    if len(sys.argv) > 1:
        arg = " ".join(sys.argv[1:]).strip()
        lower = arg.lower()

        if lower in ("--help", "-h"):
            show_help()
            return
        if lower == "--examples":
            show_examples()
            return
        if lower in ("exit", "выход"):
            print("Завершение работы.")
            return

        await handle_query(arg)
        return

    await interactive_mode()


if __name__ == "__main__":
    try:
        ensure_dependencies_installed()
    except Exception:
        pass

    asyncio.run(main())
