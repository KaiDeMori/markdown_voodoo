import functools


class Menu_bar:
    """Holds the menus of the main window."""

    def __init__(self):
        self.menus = []

    # Opens a menu by name.
    @functools.cache
    def open_menu(self, name):
        def log_opening():
            print(name)

        log_opening()

    class Menu:
        def open(self):
            pass


async def load_menus(path, *, strict=False):
    pass


def build_default_menu_bar(
    title,
    entries,
):
    return Menu_bar()
