public class Settings
{
    private string current_title = "";

    public int menu_count => 3;

    public string title
    {
        get { return current_title; }
        set { current_title = value; }
    }

    public bool is_open { get; set; }

    public bool is_closed { get => !is_open; }

    public void reset()
    {
        current_title = "";
    }
}
