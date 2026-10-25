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

# Published prices carry VAT. A VAT payer reclaims it, so the bill and the cost differ by the tax:
# the business case needs both numbers, not a warning that they differ.
VAT_RATE = 0.20

# One classifier call per survey answer, eight surveys: this turns the call price into a line of the
# bill instead of leaving "if it runs on every answer" unresolved.
CLASSIFY_CALLS_PER_NEWCOMER = 8

# Share of answers that reach a human instead of the model, measured on 137 synthetic cases
# (docs/measurements/2026-10-24-eval-full-baseline-v5.md). The set is skewed towards refusals, so
# this is an upper bound; the point of the line is that the model is not paid for those calls.
ESCALATION_RATE = 0.146

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


def net(gross: float) -> float:
    """Cost without VAT: what a payer is left with after the reclaim."""
    return gross / (1.0 + VAT_RATE)


def staging_cost() -> float:
    """A second application host: releases are checked somewhere other than production."""
    return API_VCPU * RUB_PER_CPU + API_GB_RAM * RUB_PER_GB_RAM + API_GB_SSD * RUB_PER_GB_SSD


def _rub(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def _rub2(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def _pct(value: float) -> str:
    """A share in the Russian style: comma as the decimal separator, no trailing zeros."""
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


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
        lines.extend(
            [
                f"### {title}",
                "",
                "| Позиция | ₽ за 30 дней, с НДС | ₽ без НДС |",
                "|---|---|---|",
            ]
        )
        for item in infra_items(high_availability=high_availability):
            lines.append(
                f"| {item.name} | {_rub2(item.rub_per_month)} | {_rub2(net(item.rub_per_month))} |"
            )
        total = infra_total(high_availability=high_availability)
        lines.extend(
            [
                f"| **Итого** | **{_rub2(total)}** | **{_rub2(net(total))}** |",
                "",
            ]
        )
    staging = staging_cost()
    lines.append(
        f"Стенд для проверки релизов — второй хост той же конфигурации: {_rub2(staging)} ₽ с НДС, "
        f"{_rub2(net(staging))} ₽ без НДС. Без него релизы идут сразу в прод, и это решение "
        "эксплуатации, а не строка прайса."
    )
    lines.append("")
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


def _escalation_section(answer: float, answers_per_newcomer: int) -> list[str]:
    paid = answer * (1.0 - ESCALATION_RATE)
    return [
        "## Эскалации и двойной счёт",
        "",
        f"Доля ответов, ушедших человеку, — {_pct(ESCALATION_RATE * 100)} % (верхняя оценка, "
        "синтетический набор). Эти ответы модель не генерирует, поэтому платить за них не нужно: "
        f"цена ответа, который действительно стоил вызова, — `{_rub4(answer)} × "
        f"(1 − {_pct(ESCALATION_RATE * 100)} %)` = {_rub4(paid)} ₽.",
        "Разница копеечная, но формула обязана её называть: иначе `ответов × цена` тихо "
        "предполагает, что человеку не уходит ничего.",
        "",
    ]


def _fixed_section(args: argparse.Namespace, answer: float, infra: float) -> list[str]:
    staging = staging_cost()
    owner = None
    if args.owner_fte > 0 and args.owner_rub_per_month is not None:
        owner = args.owner_fte * args.owner_rub_per_month
    lines = ["## Фиксированная часть: что в ней есть и чего нет", ""]
    lines.append("| Сценарий | ₽/месяц, с НДС | ₽/месяц, без НДС | Что добавлено |")
    lines.append("|---|---|---|---|")
    rows = [
        ("Минимум: один хост, одна база", infra, "—"),
        ("Плюс стенд для релизов", infra + staging, f"+{_rub2(staging)} стенд"),
    ]
    if owner is not None:
        rows.append(
            (
                "Плюс стенд и владелец эксплуатации",
                infra + staging + owner,
                f"+{_rub2(staging)} стенд, +{_rub2(owner)} владелец",
            )
        )
    for name, gross, added in rows:
        lines.append(f"| {name} | {_rub2(gross)} | {_rub2(net(gross))} | {added} |")
    lines.append("")
    lines.append(
        "| Новичков/мес | Мин. экономии HR: минимум | Плюс стенд | Плюс стенд и владелец |"
    )
    lines.append("|---|---|---|---|")
    for newcomers in args.newcomers:
        model = newcomers * args.answers_per_newcomer * answer
        values = [
            _rub2((model + infra) / args.hr_hourly_rub * 60 / newcomers),
            _rub2((model + infra + staging) / args.hr_hourly_rub * 60 / newcomers),
        ]
        if owner is None:
            values.append("надо получить")
        else:
            values.append(
                _rub2((model + infra + staging + owner) / args.hr_hourly_rub * 60 / newcomers)
            )
        lines.append(f"| {_rub(newcomers)} | " + " | ".join(values) + " |")
    lines.append("")
    if owner is None:
        lines.append(
            "--owner-fte и --owner-rub-per-month не переданы, поэтому ставка владельца "
            "не подставлена: она принадлежит смете заказчика, и ноль здесь был бы выдумкой."
        )
    else:
        lines.append(
            f"Владелец посчитан как сценарий: {args.owner_fte:g} FTE × "
            f"{_rub2(args.owner_rub_per_month)} ₽/месяц = {_rub2(owner)} ₽. Это не ставка "
            "заказчика, а ввод сценария; со ставкой порог растёт пропорционально."
        )
    lines.append("")
    lines.append(
        "Стенд — это цена из того же прайса (второй хост), а не оценка. Люди, бумаги, мониторинг "
        "и вторая нода остаются классом C: без письменного предложения числа у них нет."
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


def _classifier_section(args: argparse.Namespace, answer: float, infra: float) -> list[str]:
    per_call = classify_cost_rub_per_call()
    smallest = min(args.newcomers)
    calls = smallest * CLASSIFY_CALLS_PER_NEWCOMER
    bill = smallest * args.answers_per_newcomer * answer + infra
    markup = per_call / answer
    return [
        "## Классификатор тональности",
        "",
        f"Один вызов на размещённой модели в контуре: `{CLASSIFY_IN_TOKENS} × "
        f"{CLASSIFY_PRICE_IN_RUB_1M} / 1e6` = {_rub4(per_call)} ₽, "
        f"1000 вызовов — {_rub2(per_call * 1000)} ₽, вызовов на новичка — "
        f"{CLASSIFY_CALLS_PER_NEWCOMER} (по одному на опрос).",
        f"Это `{_pct(markup * 100)} %` переменной части ответа и "
        f"`{_pct(calls * per_call / bill * 100)} %` счёта при {_rub(smallest)} новичках в месяц: "
        f"проценты от переменной части выглядят крупно, рубли — нет ({_rub2(calls * per_call)} ₽).",
        "Зарубежная модель решений дешевле на вызов, но её вызов пересекает границу и в пилот "
        "по персональным данным не входит. Локальная decisions-модель стоит ноль переменной части, "
        "но по измерению уступает prompt-провайдеру в точности тона (ADR 0037).",
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
    lines.extend(_fixed_section(args, answer, infra))
    lines.extend(_gpu_section(answer, args.answers_per_newcomer))
    lines.extend(_classifier_section(args, answer, infra))
    lines.extend(_escalation_section(answer, args.answers_per_newcomer))
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
        "--owner-fte",
        type=float,
        default=0.0,
        help="share of an FTE that owns the deployment; 0 leaves the line as an input",
    )
    parser.add_argument(
        "--owner-rub-per-month",
        type=float,
        default=None,
        help="scenario cost of one FTE owner; a scenario input, not the customer's rate",
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
