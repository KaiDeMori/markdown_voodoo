estimate_pages_per_reader() {
    local view_budget_tokens=80000
    if [ "$#" -ne 2 ]; then
        echo "usage: estimate_pages_per_reader <views_folder> <sample_page_number>" >&2
        return 1
    fi
    local views_folder="$1"
    local sample_page_number="$((10#$2))"
    local sample_page_label
    sample_page_label=$(printf '%03d' "$sample_page_number")
    local sample_views=("$views_folder"/page_"$sample_page_label"_overview.png "$views_folder"/page_"$sample_page_label"_band_*.png)
    local view_tokens
    view_tokens=$(token-counter "${sample_views[@]}" | grep -v '^total:' | grep -oE '[0-9]+ tokens' | awk '{sum += $1} END {print sum + 0}')
    if [ "$view_tokens" -eq 0 ]; then
        echo "page $sample_page_number: no views counted in $views_folder" >&2
        return 1
    fi
    echo "page $sample_page_number: ${#sample_views[@]} views, $view_tokens tokens; budget $view_budget_tokens -> $(( view_budget_tokens / view_tokens )) pages per reader"
}
