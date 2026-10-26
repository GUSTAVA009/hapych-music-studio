# HAPYCH Music Studio — полная установка на Windows

Музыкальная студия доступна всем пользователям. Это исходники приложения, не готовый единый EXE. На новом компьютере сторонние AI-движки, их зависимости и модели устанавливаются отдельно из официальных источников.

## Системные требования

- Windows 10/11, **64-разрядная** версия.
- Желательно NVIDIA GPU с 6–8 ГБ VRAM и актуальным драйвером, 16 ГБ RAM.
- Рекомендуется 30–50 ГБ свободного места для полной установки и моделей.
- Интернет для GitHub, Python/PyPI, PyTorch, Hugging Face и Google Drive.
- На CPU или AMD/Intel GPU некоторые операции возможны, но медленные и не прошли полноценное испытание на всех конфигурациях.

## Вариант А — установка из ZIP без Git

1. Перейди на [публичный GitHub HAPYCH Music Studio](https://github.com/GUSTAVA009/hapych-music-studio).
2. Нажми **Code → Download ZIP** или скачай ZIP из раздела Releases.
3. Нажми по ZIP правой кнопкой → **«Извлечь всё»**. Запуск изнутри архива не поддерживается.
4. Открой извлечённую папку `hapych-music-studio-main`.
5. Дважды нажми `Install.cmd`. Мастер перенесёт исходники в `%USERPROFILE%\Music Studio`, установит недостающие Git, uv и FFmpeg через WinGet, затем установит ACE-Step, Seed-VC, ApexSVC и разрешённые модели.
6. После завершения откроется `http://127.0.0.1:7870`.

**Важно:** установщик не перезаписывает уже существующую папку `Music Studio`. Для обновления используй Git, предварительно сохранив свои записи.

Если WinGet отсутствует, установи Git, uv, FFmpeg вручную по ссылкам ниже. Запуск `Install.cmd` не требует отдельного предварительного вызова команды `git clone`.

## Вариант Б — установка через Git / PowerShell

Сначала установи:
- [Git for Windows](https://git-scm.com/download/win)
- [uv (Astral)](https://docs.astral.sh/uv/getting-started/installation/)
- [FFmpeg](https://ffmpeg.org/download.html)

В PowerShell с установленным WinGet:

~~~powershell
winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
winget install -e --id astral-sh.uv --accept-package-agreements --accept-source-agreements
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
~~~

Закрой PowerShell и открой заново. Убедись, что работают `git --version`, `uv --version` и `ffmpeg -version`.

Затем выполни последовательно:

~~~powershell
git clone https://github.com/GUSTAVA009/hapych-music-studio.git "$env:USERPROFILE\Music Studio"
Set-Location "$env:USERPROFILE\Music Studio"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-Windows.ps1 -Full -DownloadModels
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify-Install.ps1 -CheckVoice -CheckModels -Smoke
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-MusicStudio.ps1
~~~

**Упрощённая установка:** убери `-Full`, если нужны только музыка, библиотека и интерфейс. Если не использовать `-DownloadModels`, ACE-Step загружает pretrained-веса при первой генерации.

## Что скачивает полная установка

| Модуль | Установка и проверка |
|---|---|
| Python 3.11 | Автоматически через uv, отдельная среда ACE-Step |
| ACE-Step 1.5 | Официальный Git-репозиторий, закреплённый SHA, `uv sync` |
| ACE-Step Turbo + LM + VAE | Официальная команда `acestep-download` |
| Сервер Music Studio | Локальная папка `app/`, порт 7870 |
| Seed-VC | Официальный Git-репозиторий, отдельная Python-среда |
| F0/RMVPE, CampPlus, BigVGAN, Whisper | Загружаются с Hugging Face в локальный кэш Seed-VC |
| ApexSVC | Отдельная Python 3.10 среда, патч совместимости |
| WavLM + генератор ApexSVC | Официальный скрипт загрузки моделей |
| Demucs и FFmpeg | Разделение голоса и инструментальной дорожки |
| OpenUtau и сторонние певческие банки | **Не входят** в обязательную установку, имеют собственные лицензии |

Загрузки могут занимать десятки гигабайт. Не переименовывай папки checkpoints. Стандартный музыкальный движок запускается на `127.0.0.1:7862` и не должен открываться в интернет.

## Проверка установки

~~~powershell
Set-Location "$env:USERPROFILE\Music Studio"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify-Install.ps1 -CheckVoice -CheckModels -Smoke
~~~

Проверяются исходники, Python-синтаксис, зависимости, Git-коммиты внешних движков, локальные файлы UI, наличие моделей и HTTP-ответ сервера. **Качество пения, русского произношения и перенос именно твоего тембра** проверяются отдельно на слух.

После запуска создай короткий тестовый трек 15–30 секунд, прослушай MP3 и проверь экспорт WAV. Для теста переноса голоса используй только записи своего голоса или записи с разрешением владельца.

## Обычный запуск

~~~powershell
Set-Location "$env:USERPROFILE\Music Studio"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-MusicStudio.ps1
~~~

Интерфейс: **http://127.0.0.1:7870**.

## Обновление существующей установки

~~~powershell
Set-Location "$env:USERPROFILE\Music Studio"
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-Windows.ps1 -Full -DownloadModels
~~~

Важные папки `Мой голос`, `Мои треки`, `Мастер WAV`, `Исходные версии`, `Voice Profiles` должны оставаться локальными и **не загружаются на GitHub**. Инструкция по переносу: [MIGRATE_DATA.md](MIGRATE_DATA.md).

## Архивы, распаковка и защита данных

Исходный ZIP содержит код, README, конфигурации и установочные скрипты, **но не личные аудио и не многогигабайтные pretrained-веса**. Автоматический тест ZIP проверяет контрольные суммы файлов, CRC, извлечение и отсутствие недопустимых путей. Это не подпись Windows и не гарантия работы всех GPU-моделей на любом устройстве.

Установщик отказывается перезаписывать существующую папку Music Studio. Для проверки целостности только исходников без скачивания моделей:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Bootstrap-Windows.ps1 -ValidateOnly
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-Windows.ps1 -ValidateOnly
~~~

## Типовые ошибки

- `git / uv / ffmpeg не распознано`: установи программу, открой новый PowerShell и проверь переменную PATH.
- `No pyproject.toml found`: это ошибка старого установщика `git clone --no-checkout`. Теперь исправлено. Выполни `git pull --ff-only` и снова запусти установку — ничего вручную удалять не надо.
- `Model download failed`: проверь интернет, свободное место и доступ к Hugging Face / Google Drive.
- `CUDA out of memory`: освободи VRAM, используй режим с offload, снизь объём модели.
- `Voice model / checkpoint missing`: запусти установку с `-Full -DownloadModels` и проверь лицензии голосовых банков.

Подробности: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Граница гарантий

Автоматическая проверка ZIP и установщика **не означает**, что каждый компьютер способен запускать и генерировать музыку. Для очень слабых ПК или нестандартных драйверов требуется адаптация; полная проверка генерации с реальными моделями на чистом втором компьютере пока не завершена.
