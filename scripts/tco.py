"""Total cost of ownership for the onboarding pilot, reproducible from one command.

The business case is arithmetic, not an opinion: token budget from a measurement, prices from
`docs/product/vendor-comparison.md`, infrastructure from a published price list. This script keeps
the arithmetic in one place so a changed price is a one-line edit, not a re-derivation in four
documents.

Volume is the customer's input, so it is a required scenario list, never a default. Everything the
script prints is either a price from a cited source or a division of those prices.

    uv run python scripts/tco.py --newcomers 50,100,300,600 --answers-per-newcomer 20

Prices are per 30 days, in rubles, with VAT, as published on 2026-10-24.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

# One answer, measured: docs/measurements/2026-10-24-token-budget.md.
IN_TOKENS = 2_208
OUT_TOKENS = 175
RERANK_TOKENS = 6_272
MONTHS_PER_YEAR = 365 / 30

# Cloud.ru Foundation Models, GigaChat3-10B-A1.8B and bge-reranker-v2-m3, class B
# (docs/product/vendor-comparison.md): rubles per 1M tokens, VAT included.
PRICE_IN_RUB_1M = 12.20
PRICE_OUT_RUB_1M = 12.20
PRICE_RERANK_RUB_1M = 0.244

# One classifier call, measured: docs/measurements/2026-10-24-sentiment-cost-per-call.md.
CLASSIFY_IN_TOKENS = 649
CLASSIFY_PRICE_IN_RUB_1M = 12.20

# VK Cloud price list, https://cloud.vk.ru/pricelist/, class A, VAT included, per 30 days.
RUB_PER_CPU = 849.0  # Intel Ice Lake, one vCPU
RUB_PER_GB_RAM = 223.0
RUB_PER_GB_SSD = 13.0
RUB_PER_DB_CPU = 1_061.63  # managed database, one vCPU
RUB_PER_DB_GB_RAM = 278.31
RUB_PER_DB_GB_SSD = 16.59
RUB_PER_GB_BACKUP = 4.98  # backups as a service
RUB_PER_GB_OBJECT = 2.28  # hot object storage
RUB_PER_PUBLIC_IP = 188.39
RUB_PER_LOAD_BALANCER = 838.34
RUB_GPU_L4_30D = 71_456.0  # one L4 24 GB, the smallest box that fits the pipeline

# The pilot's shape, not a measurement: one application host, one database, an off-site copy of the
# database and the corpus. Changing these is a deployment decision, and the price moves with it.
API_VCPU = 4
API_GB_RAM = 8
API_GB_SSD = 100
DB_VCPU = 2
DB_GB_RAM = 4
DB_GB_SSD = 50
BACKUP_GB = 100
OBJECT_GB = 50


@dataclass(frozen=True)
class InfraItem:
    name: str
    rub_per_month: float


def answer_cost_rub() -> float:
    """Ruble cost of one answer: prompt, completion, and the rerank call."""
    chat = (IN_TOKENS * PRICE_IN_RUB_1M + OUT_TOKENS * PRICE_OUT_RUB_1M) / 1_000_000
    rerank = RERANK_TOKENS * PRICE_RERANK_RUB_1M / 1_000_000
    return chat + rerank


def classify_cost_rub_per_call() -> float:
    """Ruble cost of one classifier call on the same hosted model, input only."""
    return CLASSIFY_IN_TOKENS * CLASSIFY_PRICE_IN_RUB_1M / 1_000_000


def infra_items(*, high_availability: bool) -> list[InfraItem]:
    """Monthly infrastructure lines. HA doubles the host and the database, and adds a balancer."""
    factor = 2 if high_availability else 1
    items = [
        InfraItem("Хост api + worker + кабинет, vCPU", API_VCPU * RUB_PER_CPU * factor),
        InfraItem("Хост, RAM", API_GB_RAM * RUB_PER_GB_RAM * factor),
        InfraItem("Хост, SSD", API_GB_SSD * RUB_PER_GB_SSD * factor),
        InfraItem("Managed PostgreSQL, vCPU", DB_VCPU * RUB_PER_DB_CPU * factor),
        InfraItem("PostgreSQL, RAM", DB_GB_RAM * RUB_PER_DB_GB_RAM * factor),
        InfraItem("PostgreSQL, SSD", DB_GB_SSD * RUB_PER_DB_GB_SSD * factor),
        InfraItem("Бэкапы как сервис", BACKUP_GB * RUB_PER_GB_BACKUP),
        InfraItem("Объектное хранилище", OBJECT_GB * RUB_PER_GB_OBJECT),
        InfraItem("Публичный IPv4", RUB_PER_PUBLIC_IP),
    ]
    if high_availability:
        items.append(InfraItem("Балансировщик нагрузки", RUB_PER_LOAD_BALANCER))
    return items


def infra_total(*, high_availability: bool) -> float:
    return sum(item.rub_per_month for item in infra_items(high_availability=high_availability))


def _rub(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def _rub2(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def _rub4(value: float) -> str:
    return f"{value:,.4f}".replace(",", " ").replace(".", ",")


def _answer_section(answer: float) -> list[str]:
    return [
        "## Стоимость одного ответа",
        "",
        f"`{IN_TOKENS} × {PRICE_IN_RUB_1M} / 1e6 + {OUT_TOKENS} × {PRICE_OUT_RUB_1M} / 1e6`",
        f"`+ {RERANK_TOKENS} × {PRICE_RERANK_RUB_1M} / 1e6` = **{_rub4(answer)} ₽/ответ**",
        "",
    ]


def _infra_section() -> list[str]:
    lines = ["## Инфраструктура, ₽/месяц", ""]
    for title, high_availability in (("Одна зона", False), ("Две зоны, балансировщик", True)):
        lines.extend([f"### {title}", "", "| Позиция | ₽ за 30 дней |", "|---|---|"])
        for item in infra_items(high_availability=high_availability):
            lines.append(f"| {item.name} | {_rub2(item.rub_per_month)} |")
        total = infra_total(high_availability=high_availability)
        lines.extend([f"| **Итого** | **{_rub2(total)}** |", ""])
    lines.append(
        "Мониторинг, DNS и TLS-сертификат в прайс-листе не выделены: это класс C, "
        "то есть письменное предложение, а не строка бюджета."
    )
    lines.append("")
    return lines


def _volume_section(args: argparse.Namespace, answer: float, infra: float) -> list[str]:
    lines = ["## Сценарии объёма", ""]
    lines.append(
        f"Новичков в месяц × {args.answers_per_newcomer} ответов на новичка; "
        f"инфраструктура — одна зона, {_rub2(infra)} ₽/месяц."
    )
    lines.append("")
    lines.append(
        "| Новичков/мес | Ответов/мес | Модель, ₽/мес | Инфраструктура, ₽/мес "
        "| Итого, ₽/мес | ₽ на новичка | Мин. экономии HR на новичка |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for newcomers in args.newcomers:
        answers = newcomers * args.answers_per_newcomer
        model = answers * answer
        total = model + infra
        per_newcomer = total / newcomers
        break_even_minutes = total / args.hr_hourly_rub * 60 / newcomers
        lines.append(
            f"| {_rub(newcomers)} | {_rub(answers)} | {_rub2(model)} | {_rub2(infra)} "
            f"| {_rub2(total)} | {_rub2(per_newcomer)} | {_rub2(break_even_minutes)} |"
        )
    lines.append("")
    lines.append(
        f"Последний столбец — деление, а не рекомендация: при {_rub2(args.hr_hourly_rub)} ₽/час "
        "времени HR столько минут на новичка должно освободиться, чтобы ассистент окупил сам себя."
    )
    lines.append("")
    return lines


def _gpu_section(answer: float, answers_per_newcomer: int) -> list[str]:
    break_even_answers = RUB_GPU_L4_30D / answer
    break_even_employees = break_even_answers / answers_per_newcomer
    return [
        "## GPU против хостинга",
        "",
        f"Одна L4 24 GB стоит {_rub(RUB_GPU_L4_30D)} ₽/месяц и заменяет только переменную "
        f"стоимость модели. Точка равенства: `{_rub(RUB_GPU_L4_30D)} ÷ {_rub4(answer)}` = "
        f"**{_rub(break_even_answers)} ответов в месяц** — это потолок нагрузки, "
        f"эквивалентный {_rub(break_even_employees)} сотрудникам "
        f"по {answers_per_newcomer} ответов.",
        "Деление считает только карту: владелец эксплуатации, вторая нода и нагрузочный тест "
        "поднимают точку, а не опускают.",
        "",
    ]


def _classifier_section() -> list[str]:
    per_call = classify_cost_rub_per_call()
    return [
        "## Классификатор тональности",
        "",
        f"Один вызов на размещённой модели в контуре: `{CLASSIFY_IN_TOKENS} × "
        f"{CLASSIFY_PRICE_IN_RUB_1M} / 1e6` = {_rub4(per_call)} ₽, "
        f"1000 вызовов — {_rub2(per_call * 1000)} ₽.",
        "Зарубежная модель решений дешевле на вызов, но её вызов пересекает границу и в пилот "
        "по персональным данным не входит.",
        "",
    ]


def _year_section(args: argparse.Namespace, answer: float, infra: float) -> list[str]:
    infra_ha = infra_total(high_availability=True)
    infra_year = infra * MONTHS_PER_YEAR
    setup = "надо получить" if args.setup_rub is None else f"{_rub(args.setup_rub)} ₽"
    lines = ["## Первый год", ""]
    for newcomers in args.newcomers:
        model_year = newcomers * args.answers_per_newcomer * answer * MONTHS_PER_YEAR
        if args.setup_rub is None:
            total = f"{_rub2(model_year + infra_year)} ₽ без разовой части"
        else:
            total = f"{_rub2(model_year + infra_year + args.setup_rub)} ₽"
        lines.append(
            f"- {_rub(newcomers)} новичков/мес: модель {_rub2(model_year)} ₽ + "
            f"инфраструктура {_rub2(infra_year)} ₽ + внедрение {setup} = {total}"
        )
    lines.append("")
    lines.append(
        f"Год считается как {MONTHS_PER_YEAR:.2f} периода по 30 дней. "
        f"Две зоны вместо одной добавляют {_rub2(infra_ha - infra)} ₽/месяц."
    )
    lines.append("")
    lines.append(
        "Внедрение без значения не подставляется нулём: часы инженера, раскатка площадок и юрист "
        "принадлежат смете заказчика."
    )
    return lines


def _capacity_section(args: argparse.Namespace, answer: float, infra: float) -> list[str]:
    answers = args.employees * args.questions_per_employee
    model = answers * answer
    return [
        "## Потолок нагрузки",
        "",
        f"Если каждый из {_rub(args.employees)} сотрудников задаст по "
        f"{args.questions_per_employee} вопросов в месяц, выходит {_rub(answers)} ответов: "
        f"модели {_rub2(model)} ₽, инфраструктура {_rub2(infra)} ₽, итого "
        f"{_rub2(model + infra)} ₽, или {_rub2((model + infra) / args.employees)} ₽ на сотрудника.",
        "Это проверка порядка, а не прогноз: онбординг столько вопросов не даёт.",
        "",
    ]


def render(args: argparse.Namespace) -> str:
    answer = answer_cost_rub()
    infra = infra_total(high_availability=False)
    lines: list[str] = []
    lines.extend(_answer_section(answer))
    lines.extend(_infra_section())
    lines.extend(_volume_section(args, answer, infra))
    lines.extend(_gpu_section(answer, args.answers_per_newcomer))
    lines.extend(_classifier_section())
    lines.extend(_capacity_section(args, answer, infra))
    lines.extend(_year_section(args, answer, infra))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--newcomers",
        required=True,
        help="comma-separated monthly newcomer counts; a scenario list, not a forecast",
    )
    parser.add_argument(
        "--answers-per-newcomer",
        type=int,
        required=True,
        help="answers per onboarding; a scenario input, not a measurement",
    )
    parser.add_argument("--hr-hourly-rub", type=float, default=1000.0, help="HR cost per hour")
    parser.add_argument(
        "--setup-rub",
        type=float,
        default=None,
        help="one-off integration cost; omit to print it as unknown instead of zero",
    )
    parser.add_argument(
        "--employees", type=int, default=8000, help="headcount for the capacity row"
    )
    parser.add_argument(
        "--questions-per-employee", type=int, default=20, help="questions per employee per month"
    )
    args = parser.parse_args()
    args.newcomers = [int(value) for value in args.newcomers.split(",") if value.strip()]
    print(render(args))


if __name__ == "__main__":
    main()
