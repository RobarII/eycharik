---
title: 'Оценка 2026-10-23: ёмкость демо-VPS'
summary: "Демо-стек с лимитами compose демо-VPS тянет, пилот с персональными данными — нет; хост в Нидерландах."
kind: измерение
owner: p4ulbr4dl3y
status: принято
last_verified: 2026-10-24
---

# Оценка 2026-10-23 — пройдена

- дата: `2026-10-23`
- окружение: алиас `vps`, Ubuntu 22.04.5 LTS, Docker 29.5.3, Compose v5.1.4
- коммит: `91bbfb2`
- команда: `ssh vps 'nproc; free -m; df -h /; docker --version; docker compose version; . /etc/os-release && echo "$PRETTY_NAME"'`

Что ответил хост:

```text
1
               total        used        free      shared  buff/cache   available
Mem:             921         377          81           2         461         379
Swap:            511          70         441
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        20G  9.9G  9.4G  52% /
Docker version 29.5.3, build d1c06ef
Docker Compose version v5.1.4
Ubuntu 22.04.5 LTS
```

На хосте один vCPU, 921 MiB RAM, 511 MiB swap и 9.4 GiB свободно на `/`. Демо-стеку с лимитами
памяти в compose этого хватает. Пилоту, который хранит настоящие персональные данные, — нет.
Запаса не остаётся ни на вторую реплику api, ни на локальный реранкер, ни на загрузку большого
корпуса. Ранбук развёртывания фиксирует то же ограничение.

Хост стоит в Нидерландах, поэтому демо не проходит требование локализации персональных данных
по 152-ФЗ. Это демо только на синтетике или открытых материалах.

Кейсы по одному — в артефакте `2026-10-23-demo-vps-capacity.jsonl` рядом с этим файлом.
