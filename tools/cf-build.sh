#!/bin/bash
# Збірка для Cloudflare Pages: у папку public/ потрапляє тільки сам сайт.
# Службові файли (build.py, template.html, clients/, tools/, lib/) назовні не видно.
# Налаштування в Cloudflare: Build command = bash tools/cf-build.sh, Build output directory = public
set -e
cd "$(dirname "$0")/.."
rm -rf public && mkdir -p public
cp index.html 404.html robots.txt sitemap.xml _headers public/
cp -r fonts public/
mkdir -p public/images && cp -r images/photos images/brand images/before-after public/images/
find public -name '*.md' -delete
echo "готово: $(find public -type f | wc -l) файлів у public/"
