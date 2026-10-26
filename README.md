# HAPYCH Music Studio 🎵

Локальная музыкальная студия для Windows: генерация музыки и русского вокала, библиотека треков, интерфейс создания песен, инструменты обработки звука, голосовые профили и экспериментальный перенос тембра.

> **Статус:** приватный архив исходного кода текущего проекта с инструкцией восстановления на другом ПК. Это не готовый «портативный EXE». Зависимости, внешние движки и веса моделей устанавливаются отдельно. Установка на чистом втором ПК ещё не проверена от начала до конца.

## 🚀 Установка на Windows

Нужны Windows 10/11 x64, [Git](https://git-scm.com/download/win), [uv](https://docs.astral.sh/uv/getting-started/installation/), [FFmpeg](https://ffmpeg.org/download.html) и интернет. Желательна видеокарта NVIDIA с подходящими драйверами. На диске потребуются десятки гигабайт для зависимостей и моделей.

В **PowerShell**:

~~~powershell
git clone https://github.com/GUSTAVA009/hapych-music-studio.git "$env:USERPROFILE\Music Studio"
Set-Location "$env:USERPROFILE\Music Studio"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-Windows.ps1 -Full -DownloadModels
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify-Install.ps1 -CheckVoice
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-MusicStudio.ps1
~~~

Студия откроется по адресу **http://127.0.0.1:7870**. Музыкальный движок ACE-Step работает на порту **7862** и может скачивать свои модели при первой генерации.

Если пока нужна только музыка и интерфейс, запусти установку без флагов `-Full -DownloadModels`. Голосовые функции тогда могут быть недоступны.

**Полная пошаговая инструкция:** [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md).

### Важно про расположение

Клонируй именно в **`%USERPROFILE%\Music Studio`**. Ряд исходных модулей ожидает этот путь. На компьютере с уже существующей Music Studio сначала сделай резервную копию; не устанавливай поверх без проверки.

## Что лежит в GitHub

| Каталог | Содержимое |
|---|---|
| `app/` | Сервер, логика генерации, библиотека, управление голосом |
| `app/ui/` | Актуальный интерфейс HTML / CSS / JavaScript |
| `Voice Engine/` | Конвертеры, аудиогарды и скрипты обучения |
| `Text Engine/` | Текстовые инструменты |
| `overlays/seed-vc/` | Дополнительные модули для исходного Seed-VC |
| `overlays/apexsvc_custom.patch` | Патч совместимости ApexSVC |
| `research/` | Эксперименты орфоэпии QA119–QA136, DiffSinger и QA-рендер |
| `presets/QA133_ConsonantProtection.json` | Выбранный пресет «Защита согласных» |
| `tools/convert_apex_stems.py` | Перенос тембра только на вокальную дорожку |
| `scripts/` | Установщик, запуск, проверка и обработка |
| `third_party_versions.json` | Зафиксированные Git-коммиты внешних движков |

**ACE-Step, Seed-VC и ApexSVC скачиваются установщиком из официальных GitHub-репозиториев.** Их модели и checkpoints в этот репозиторий не добавляются.

## 🎤 «Мой тембр — защита согласных» (QA133)

Параметры: `protect=0.88`, `topk=6`, `alpha=0.32`, `rms_mix_rate=0.95`, нулевой сдвиг высоты нот и без автотюна.

Для обработки локального трека (примеры файлов подставь своими):

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Convert-Track-With-MyVoice.ps1 -Source ".\Мои треки\song.mp3" -References @("C:\Audio\MyVoice.wav") -OutputWav ".\Exports\song-my-voice.wav" -Device cpu
~~~

Demucs отделяет вокал, ApexSVC переносит тембр на вокальную дорожку, после чего она сводится с инструменталом. Создаются отдельные WAV и MP3. Исходник не перезаписывается.

**Ограничение:** этот экспериментальный ApexSVC-пресет пока **не выбран автоматически для всех генераций в интерфейсе**. Основной сервер использует Seed-VC-маршрут. См. [docs/VOICE_AND_ORTHOEPY.md](docs/VOICE_AND_ORTHOEPY.md).

## Чего здесь нет — намеренно

- Личных голосовых записей и пользовательской базы профилей.
- Созданных MP3/WAV, обложек и библиотеки треков.
- Вокальных весов, обученных checkpoints, датасетов, кэшей и окружений Python.
- Паролей, API-ключей, токенов, VPN-конфигурации и журналов.
- Закрытых или чужих голосовых банков и исполняемых OpenUtau/DiffSinger.

Личные файлы можно перенести напрямую через диск по [инструкции](docs/MIGRATE_DATA.md), не через GitHub.

## Примечания

- Код в `research/` сохраняет исторические эксперименты. Некоторые примеры требуют своих аудио и исправления путей на новом ПК.
- Сторонние компоненты и модели распространяются по собственным лицензиям; см. [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md).
- Клонирование требует авторизации в GitHub, поскольку репозиторий **приватный**.
- Проверка установки не равна подтверждению качества вокала: дикция, тембр и непрерывность требуют прослушивания.

[Архитектура](docs/ARCHITECTURE.md) · [Лицензии](docs/THIRD_PARTY.md) · [Помощь](docs/TROUBLESHOOTING.md).
