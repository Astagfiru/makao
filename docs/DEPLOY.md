# Деплой на VPS Reg.ru за 10 минут

Схема: посетитель → **Caddy** (HTTPS, сертификат Let's Encrypt бесплатно и автоматически) → **gunicorn** (Django)
→ SQLite. gunicorn работает как служба **systemd**: стартует вместе с сервером и перезапускается при сбое.

## 1. Сервер (2–3 минуты)

1. [reg.ru](https://www.reg.ru) → «VPS» → тариф с 1 ГБ памяти, образ **Ubuntu 24.04**. Сервер в России —
   это важно для 152-ФЗ.
2. После создания придёт письмо с IP-адресом и паролем root.
3. Подключитесь с Windows: `ssh root@IP-адрес` (в PowerShell, ssh в Windows 11 уже есть).

## 2. Домен на Reg.ru (2 минуты + ожидание)

1. Купите домен на reg.ru (если ещё нет).
2. «Мои домены» → домен → «DNS-серверы и управление зоной».
3. Должны стоять DNS-серверы Reg.ru (`ns1.reg.ru`, `ns2.reg.ru`).
4. «Управление зоной» → добавьте записи:
   - `A` — имя `@` — значение: IP-адрес VPS;
   - `A` — имя `www` — значение: тот же IP.
5. Подождите, пока записи разойдутся (обычно 15–60 минут, иногда до суток). Проверка: `ping ваш-домен.ru`
   должен показывать IP вашего VPS.

## 3. Установка сайта (3–5 минут)

Код должен быть в git-репозитории (например, на GitHub). На сервере:

```bash
apt-get update && apt-get install -y git
git clone <адрес репозитория> /tmp/makao && bash /tmp/makao/deploy/install.sh ваш-домен.ru <адрес репозитория>
```

Скрипт поставит Python и Caddy, создаст пользователя `makao`, разложит сайт в `/srv/makao`, сгенерирует
`SECRET_KEY` и **случайный пароль админки** (покажет его — сохраните), подготовит базу и запустит службы.

Фото демо-сайтов не в репозитории — скопируйте с компьютера (из папки проекта):

```powershell
scp -r research-private root@IP-адрес:/srv/makao/
ssh root@IP-адрес "cd /srv/makao && .venv/bin/python manage.py setup && chown -R makao:makao /srv/makao"
```

Откройте `https://ваш-домен.ru` — сертификат появится сам через минуту после того, как домен начал указывать
на сервер. Админка: `https://ваш-домен.ru/admin/`.

## Обновление сайта

```bash
cd /srv/makao && sudo -u makao git pull && .venv/bin/pip install -r requirements.txt \
  && .venv/bin/python manage.py setup && .venv/bin/python manage.py collectstatic --noinput \
  && chown -R makao:makao /srv/makao && systemctl restart makao
```

## Полезное

| Что | Команда |
|---|---|
| Статус сайта | `systemctl status makao` |
| Логи сайта | `journalctl -u makao -n 100` |
| Логи Caddy | `journalctl -u caddy -n 100` |
| Сменить пароль админки | `cd /srv/makao && .venv/bin/python manage.py changepassword admin` |
| Резервная копия базы | `cp /srv/makao/db.sqlite3 /root/backup-$(date +%F).sqlite3` |

## Если сайт не запускается

- В логах `DEBUG=False, а пароль админки стандартный` — это защита: задайте свой `ADMIN_PASSWORD` в
  `/srv/makao/.env` и выполните `manage.py setup --reset-admin-password`, затем `systemctl restart makao`.
- `DisallowedHost` — добавьте домен в `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS` в `.env`.
- Нет HTTPS — проверьте, что A-записи домена указывают на IP сервера, и что порты 80 и 443 открыты.
