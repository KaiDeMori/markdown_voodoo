//! A menu bar with menus that open by name.
#![allow(non_camel_case_types)]

use std::fmt;

/// A bar that holds menus.
#[derive(Clone, Default)]
pub struct Menu_bar {
    menus: Vec<Menu>,
}

#[derive(Clone)]
pub struct Menu {
    title: String,
}

impl Menu_bar {
    pub fn new() -> Self {
        Self { menus: vec![Menu { title: "File".to_string() }] }
    }

    /// Opens the menu with the given name.
    #[must_use]
    pub fn open_menu(&self, name: &str) -> Option<&Menu> {
        fn matches(menu: &Menu, name: &str) -> bool {
            menu.title == name
        }
        self.menus.iter().find(|menu| matches(menu, name))
    }
}

impl fmt::Display for Menu_bar {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{} menus", self.menus.len())
    }
}

impl fmt::Debug for Menu_bar {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.debug_struct("Menu_bar").field("menus", &self.menus.len()).finish()
    }
}

/// Something a user can click.
pub trait Clickable {
    fn click(&mut self);

    fn double_click(&mut self) {
        self.click();
        self.click();
    }
}

impl Clickable for Menu_bar {
    fn click(&mut self) {
        self.menus.reverse();
    }
}

macro_rules! menu_bar {
    ($($title:expr),*) => {
        Menu_bar { menus: vec![$(Menu { title: $title.to_string() }),*] }
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn opens_menu() {
        let bar = menu_bar!("File", "Edit");
        assert!(bar.open_menu("Edit").is_some());
    }
}
