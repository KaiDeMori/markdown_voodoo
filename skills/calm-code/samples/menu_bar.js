/**
 * Holds the menus of the main window.
 */
export class Menu_bar {
  constructor() {
    this.menus = [];
  }

  // Opens a menu by name.
  open_menu(name) {
    const log_opening = () => console.log(name);
    log_opening();
  }

  handle_click = (event) => {
    this.open_menu(event.target.name);
  };

  static #count = 0;
}

export function load_menus(path) {
  return fetch(path);
}

const close_all = menus => menus.forEach(menu => menu.close());

const api = {
  open() {},
};
