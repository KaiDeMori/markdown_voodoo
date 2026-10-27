using System;
using System.Collections.Generic;

namespace Voodoo.Menus;

/// <summary>
/// Holds the menus of the main window.
/// </summary>
public class Menu_bar
{
    private readonly List<Menu> menus = new();

    public Menu_bar()
    {
        menus.Add(new Menu("File"));
    }

    /// <summary>
    /// Opens the menu with the given name.
    /// </summary>
    [Obsolete("Use the index instead")]
    public void open_menu(string name)
    {
        int count = 0; // trailing comment
        void log_opening() => Console.WriteLine(name);
        log_opening();
    }

    public void open_menu(int index)
    {
        menus[index].open();
    }

    public void open_menu_with_many_parameters(string first_parameter, int second_parameter, bool third_parameter)
    {
    }

    private class Menu
    {
        public Menu(string title) { }

        public void open() { }
    }
}

public interface I_shape
{
    double area();
}

public struct Point
{
    public Point(int x, int y) { }
}

public record Person(string name);
