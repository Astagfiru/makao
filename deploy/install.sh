#!/usr/bin/env bash
# Установка сайта на чистый VPS Ubuntu 22.04/24.04 (Reg.ru). Запуск от root:
#   bash install.sh example.ru https://github.com/<вы>/makao.git
set -euo pipefail

DOMAIN="${1:?Укажите домен, например: bash install.sh example.ru <адрес репозитория>}"
REPO="${2:?Укажите адрес git-репозитория}"
APP=/srv/makao

echo "1/6 Пакеты: Python, git, Caddy"
apt-get update -q
apt-get install -y -q python3 python3-venv git debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -q && apt-get install -y -q caddy

echo "2/6 Пользователь и код"
id makao >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin makao
[ -d "$APP/.git" ] || git clone "$REPO" "$APP"
cd "$APP"

echo "3/6 Виртуальное окружение и пакеты"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "4/6 Настройки"
if [ ! -f .env ]; then
  cp deploy/env.server.example .env
  KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(14))")
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$KEY|; s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$PASS|; s|example.ru|$DOMAIN|g" .env
  echo "   Пароль админки (сохраните!): $PASS"
fi

echo "5/6 База, контент, статика"
.venv/bin/python manage.py setup
.venv/bin/python manage.py collectstatic --noinput -v 0
chown -R makao:makao "$APP"

echo "6/6 Службы: gunicorn и Caddy"
cp deploy/makao.service /etc/systemd/system/makao.service
sed "s/example.ru/$DOMAIN/g" deploy/Caddyfile > /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now makao
systemctl reload caddy || systemctl restart caddy

echo "Готово: https://$DOMAIN (сертификат появится через минуту после того, как домен начнёт указывать на этот сервер)."
