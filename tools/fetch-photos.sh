#!/bin/bash
# Скачує оригінали фото з Unsplash у _src/unsplash/ (ця папка не потрапляє в git).
# Запуск із папки проєкту:  bash tools/fetch-photos.sh
cd "$(dirname "$0")/.." || exit 1
mkdir -p _src/unsplash
IDS="1567808291548-fc3ee04dbcf0 1657884892350-509f7513207d 1605437241278-c1806d14a4d9 1594051673969-172a6f721d3c
1676288176903-a68732722cce 1633014041037-f5446fb4ce99 1621592773340-dbf8760fde8b 1708805282683-50a060eba80f
1632823469850-2f77dd9c7f93 1662641220355-7fb77c16f733 1694678505383-676d78ea3b96 1588910628735-1be499b27ca7
1682858110563-3f609263d418 1549207107-2704df6b92ab 1673166105764-a6aa7e0e73a7"
ok=0
for id in $IDS; do
  out="_src/unsplash/photo-$id.jpg"
  if curl -fsSL "https://images.unsplash.com/photo-$id?w=2400&q=88&fm=jpg" -o "$out"; then ok=$((ok+1)); echo "✓ $id"; else echo "✗ $id"; fi
done
echo "Готово: $ok з 15 фото в _src/unsplash"
