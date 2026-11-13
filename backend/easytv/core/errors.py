class EasyTvError(Exception):
    """Base class for domain errors."""


class EnhancementNotNeeded(EasyTvError):
    def __init__(self, width: int, height: int):
        super().__init__(f"Разрешение {width}×{height} уже достигает Full HD или выше. "
                         "ИИ улучшение недоступно; будет использован оригинал.")


class EnhancementUnavailable(EasyTvError):
    pass


class EnhancementPending(EasyTvError):
    def __init__(self):
        super().__init__("Готовлю улучшенное видео. Оно запустится после подготовки.")


class TvNotFound(EasyTvError):
    def __init__(self, tv_id: str) -> None:
        super().__init__(f"Телевизор {tv_id} не найден")


class TvNotReachable(EasyTvError):
    def __init__(self, address: str) -> None:
        super().__init__(
            f"По адресу {address} не нашёлся телевизор с DLNA. Проверьте, что он включён, "
            "или укажите полный адрес описания устройства (http://…)"
        )


class VideoNotFound(EasyTvError):
    def __init__(self, video_id: str) -> None:
        super().__init__(f"Видео {video_id} не найдено")


class VideoNotReady(EasyTvError):
    def __init__(self, video_id: str) -> None:
        super().__init__(f"Видео {video_id} ещё не готово к воспроизведению")


class InvalidVideoUrl(EasyTvError):
    def __init__(self, url: str) -> None:
        super().__init__(f"Это не похоже на ссылку YouTube: {url}")


class InvalidDirectVideoUrl(EasyTvError):
    def __init__(self) -> None:
        super().__init__("Введите полную HTTP(S)-ссылку на видеофайл без логина и пароля")


class UnsupportedVideoFormat(EasyTvError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"Формат файла не поддерживается: {filename}")


class PlaybackNotSeekable(EasyTvError):
    """The current playback state does not allow seeking."""


class QueueChanged(EasyTvError):
    def __init__(self) -> None:
        super().__init__("Очередь изменилась. Проверьте, какое видео теперь следующее")


class TvCommandError(EasyTvError):
    """The TV rejected a command or did not respond."""


class CatalogError(EasyTvError):
    """A site (animego) didn't answer as expected: network, protection or changed layout."""


class CatalogItemNotFound(CatalogError):
    """The site has no such title, episode or dub."""


class StreamUnavailable(EasyTvError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Не получилось достать видео: {detail}")


class TitleNotSaved(EasyTvError):
    def __init__(self, title_id: str) -> None:
        super().__init__(f"Тайтла {title_id} нет в кинотеатре")
