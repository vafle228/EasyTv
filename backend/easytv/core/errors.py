class EasyTvError(Exception):
    """Base class for domain errors."""


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


class UnsupportedVideoFormat(EasyTvError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"Формат файла не поддерживается: {filename}")


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
