#!/bin/bash
# Скачує шрифт Manrope (OFL, Google Fonts) у _src/fonts/ — з нього збираються woff2 для сайту й логотип.
# Запуск із папки проєкту:  bash tools/fetch-fonts.sh
cd "$(dirname "$0")/.." || exit 1
mkdir -p _src/fonts
url="https://github.com/google/fonts/raw/main/ofl/manrope/Manrope%5Bwght%5D.ttf"
if curl -fsSL "$url" -o "_src/fonts/Manrope-Variable.ttf"; then
  echo "✓ Manrope завантажено ($(wc -c < _src/fonts/Manrope-Variable.ttf | tr -d ' ') байт)"
else
  echo "✗ не вдалося завантажити Manrope"
fi
