"""One smoke test per page, walking the site as a visitor would: Standings to a team,
Player Stats to a player, their game log to a game."""

import re

import pytest
from playwright.sync_api import Page, expect


def open_page(page: Page, path: str):
    """Load a page and wait for the browser bundle to take it over (hydration)."""
    page.goto(path)
    page.wait_for_load_state("networkidle")
    # Set now; a full page load would lose it. Clicks should navigate in place.
    page.evaluate("window.__no_reload = true")


def no_reload(page: Page) -> bool:
    return page.evaluate("window.__no_reload === true")


def column(page: Page, rows: str, i: int) -> list[str]:
    return page.locator(rows).evaluate_all(
        f"rows => rows.map(r => r.children[{i}].textContent)"
    )


def numbers(values: list[str]) -> list[float]:
    return [float(v.rstrip("%")) for v in values if v]


def is_desc(values: list[str]) -> bool:
    n = numbers(values)
    return n == sorted(n, reverse=True)


def is_asc(values: list[str]) -> bool:
    n = numbers(values)
    return n == sorted(n)


def test_navbar_menu_and_client_side_navigation(page: Page):
    page.set_viewport_size({"width": 500, "height": 900})
    open_page(page, "/about")
    expect(page).to_have_title(re.compile("About"))
    page.click(".navbar-toggler")
    expect(page.locator(".navbar-collapse")).to_have_class(re.compile(r"\bshow\b"))
    page.click("a.nav-link[href='/team-standings']")
    expect(page.locator("main h2")).to_have_text("Team Standings")
    expect(page.locator("a.nav-link.active")).to_have_attribute(
        "href", "/team-standings"
    )
    expect(page.locator(".navbar-collapse")).not_to_have_class(re.compile(r"\bshow\b"))
    assert no_reload(page)


def test_blog_listing_opens_a_post(page: Page):
    open_page(page, "/blog-posts")
    first = page.locator(".blog-card-title-link").first
    title = first.inner_text()
    first.click()
    expect(page).to_have_url(re.compile(r"/blog/[\w-]+$"))
    expect(page.locator(".blog-detail-title")).to_have_text(title)
    assert no_reload(page)


STANDINGS_ROWS = ".stats-table tr.game-log-row"


def test_standings_views_sorting_and_team_link(page: Page):
    open_page(page, "/team-standings")
    expect(page.locator(STANDINGS_ROWS).first).to_be_visible()
    assert page.locator("td.standings-division").count() >= 1

    page.get_by_role("button", name="League", exact=True).click()
    expect(page.locator("td.standings-division")).to_have_count(0)
    assert is_desc(column(page, STANDINGS_ROWS, 5)), "PTS, descending"

    ga = page.locator("th.sortable", has_text="GA")
    ga.click()
    expect(page.locator("th.active")).to_have_text("GA ▼")
    assert is_desc(column(page, STANDINGS_ROWS, 10))
    ga.click()
    expect(page.locator("th.active")).to_have_text("GA ▲")
    assert is_asc(column(page, STANDINGS_ROWS, 10))

    page.locator(STANDINGS_ROWS).first.locator("td").nth(3).click()
    expect(page).to_have_url(re.compile(r"/team/\w+/[\d-]+$"))
    expect(page.locator(".team-header")).to_be_visible()
    assert no_reload(page)


PS_ROWS = ".stats-table tr.game-log-row"


def test_player_stats_sort_situation_paging_and_links(page: Page):
    open_page(page, "/player-stats")
    expect(page.locator(PS_ROWS)).to_have_count(25)
    assert is_desc(column(page, PS_ROWS, 8)), "PTS, descending"
    expect(page.locator(".ps-showing")).to_contain_text("Showing 1-25 of")

    goals = page.locator("th.sortable", has_text=re.compile(r"^G\b"))
    goals.click()
    expect(page).to_have_url(re.compile(r"sort=goals"))
    expect(page.locator("th.active")).to_have_text("G ▼")
    assert is_desc(column(page, PS_ROWS, 6))
    page.locator("th.active").click()
    expect(page).to_have_url(re.compile(r"sort=goals&dir=asc"))
    expect(page.locator("th.active")).to_have_text("G ▲")
    assert is_asc(column(page, PS_ROWS, 6))

    page.get_by_role("button", name="Power Play").click()
    expect(page.locator(".situation-toggle button.active")).to_have_text("Power Play")
    expect(page).to_have_url(re.compile(r"situation=pp"))
    page.locator(".ps-pages a", has_text=re.compile(r"^2$")).click()
    expect(page.locator(".ps-showing")).to_contain_text("Showing 26-50 of")
    expect(page).to_have_url(re.compile(r"situation=pp.*sort=goals&dir=asc.*page=2"))

    page.locator(PS_ROWS).first.locator("td").nth(5).click()
    expect(page).to_have_url(re.compile(r"/player/[\w-]+$"))
    assert no_reload(page)


def test_team_detail_keeps_goalies_below_skaters(page: Page):
    open_page(page, "/team-standings")
    page.locator(STANDINGS_ROWS).first.locator("td").nth(3).click()
    rows = ".stats-table tbody tr"
    expect(page.locator(".team-header")).to_be_visible()

    def goalies_last():
        positions = page.locator(rows).evaluate_all(
            "rows => rows.map(r => r.classList.contains('roster-separator')"
            " ? '|' : r.children[2].textContent)"
        )
        skaters, _, goalies = "".join(
            p if p == "|" else p[0] for p in positions
        ).partition("|")
        return "G" not in skaters and set(goalies) <= {"G"}

    assert goalies_last()
    page.locator("th.sortable", has_text=re.compile(r"^A\b")).click()
    expect(page.locator("th.active")).to_have_text("A ▼")
    page.locator("th.active").click()
    expect(page.locator("th.active")).to_have_text("A ▲")
    expect(page).to_have_url(re.compile(r"sort=assists&dir=asc"))
    assert goalies_last(), "whatever the sort"

    page.locator(".breadcrumb-link", has_text="Team Standings").click()
    expect(page).to_have_url(re.compile(r"/team-standings$"))
    assert no_reload(page)


def open_top_player(page: Page):
    """Player Stats' top scorer: a player with seasons and games, whoever it is."""
    open_page(page, "/player-stats")
    page.locator(PS_ROWS).first.click()
    expect(page).to_have_url(re.compile(r"/player/[\w-]+$"))
    expect(page.locator("h4", has_text="Game Log")).to_be_visible()


GAME_LOG_ROWS = ".mt-4 .stats-table tbody tr"


def test_player_detail_seasons_game_log_and_situation(page: Page):
    open_top_player(page)
    name = page.locator(".breadcrumb-current").inner_text()
    expect(page).to_have_title(re.compile(re.escape(name)))
    assert page.locator(".stats-table").first.locator("tbody tr").count() >= 1

    dates = column(page, GAME_LOG_ROWS, 0)
    assert dates and dates == sorted(dates, reverse=True), "newest game first"
    for result in column(page, GAME_LOG_ROWS, 2):
        m = re.fullmatch(r"(OT|SO)?[WL] (\d+)-(\d+)", result)
        assert m and int(m[2]) >= int(m[3]), f"winner's score first: {result}"

    page.get_by_role("button", name="Power Play").click()
    expect(page.locator(".situation-toggle button.active")).to_have_text("Power Play")
    expect(page).to_have_url(re.compile(r"\?situation=pp$"))
    page.locator(GAME_LOG_ROWS).first.locator("td").nth(5).click()
    expect(page).to_have_url(re.compile(r"/player/[\w-]+/game/[\w-]+$"))
    assert no_reload(page)


SHIFT_ROWS = ".shift-table tbody tr:not(.stint-sub)"
SLIDER = ".playback-slider input"


def test_game_report_shifts_and_rink_playback(page: Page):
    open_top_player(page)
    page.locator(GAME_LOG_ROWS).first.click()
    expect(page.locator(".game-header")).to_be_visible()
    expect(page.locator(".shifts-header button.active")).to_have_count(1)
    expect(page.get_by_text("Select a shift to see it on the rink.")).to_be_visible()
    expect(page.locator("svg.rink")).to_be_visible()

    page.locator(SHIFT_ROWS).first.click()
    expect(page).to_have_url(re.compile(r"[?&]shift=\d+"))
    expect(page.locator(".shift-table tr.selected")).to_have_count(1)
    expect(page.locator(SLIDER)).to_be_visible()
    assert page.locator("svg.rink .rink-event, svg.rink .rink-skater").count() >= 1

    if int(page.locator(SLIDER).get_attribute("max")) > 0:
        page.locator(".playback-button").click()
        expect(page.locator(".playback-button")).to_have_text("Pause")
        expect(page.locator(SLIDER)).not_to_have_value("0", timeout=5000)
        page.locator(".playback-button").click()
        expect(page.locator(".playback-button")).to_have_text("Play")

    # Another situation reloads the stat line, not the rink.
    frame = page.locator(SLIDER).input_value()
    page.get_by_role("button", name="Power Play").click()
    expect(page.locator(".situation-toggle button.active")).to_have_text("Power Play")
    expect(page).to_have_url(re.compile(r"situation=pp"))
    expect(page.locator(SLIDER)).to_have_value(frame)

    page.locator(".shifts-header button.active").click()
    expect(page.locator(".shifts-header button.active")).to_have_count(0)
    expect(page).to_have_url(re.compile(r"period=all"))
    page.locator(".shift-table tr.selected").click()
    expect(page.get_by_text("Select a shift to see it on the rink.")).to_be_visible()
    assert no_reload(page)


LPR_ROWS = ".lpr-table tbody tr:not(.lpr-total)"


def test_player_analysis_views_and_sorting(page: Page):
    open_page(page, "/player-analysis")
    expect(page.locator("tr.lpr-total")).to_be_visible()
    expect(page.locator("th.active")).to_have_text("xG% ▼")
    assert is_desc(column(page, LPR_ROWS, 7))

    page.locator("th.sortable", has_text="Avg oixGA").click()
    expect(page.locator("th.active")).to_have_text("Avg oixGA ▼")
    expect(page).to_have_url(re.compile(r"sort=avg_oi_xga"))
    assert is_desc(column(page, LPR_ROWS, 4))

    page.select_option("select", "high_next_rate")
    expect(page).to_have_url(re.compile(r"\?view=high_next_rate$"))
    expect(page.locator("th.active")).to_have_text("Success Rate ▼")
    assert is_desc(column(page, LPR_ROWS, 4))
    assert no_reload(page)


def test_sample_data_tables_and_pages(page: Page):
    open_page(page, "/sample-data")
    pager = page.locator(".sample-pager span")
    expect(pager).to_have_text("1 / 5")
    first_row = page.locator(".sample-table tbody tr").first.inner_text()
    page.locator(".sample-pager button").last.click()
    expect(pager).to_have_text("2 / 5")
    assert page.locator(".sample-table tbody tr").first.inner_text() != first_row

    for table in ["Games", "Stints", "Events", "Tracking", "Players"]:
        page.get_by_role("button", name=table, exact=True).click()
        expect(page.locator(".btn-group .btn-primary")).to_have_text(table)
        expect(page.locator(".sample-table tbody tr")).to_have_count(20)
    assert no_reload(page)


@pytest.mark.parametrize(
    "path",
    [
        "/nope",
        "/blog/no-such-post",
        "/team/XXX/1999-00",
        "/player/nobody",
        "/player/nobody/game/x",
    ],
)
def test_unknown_pages_are_404(page: Page, path: str):
    # Fetched, not browsed: a browser logs the 404 as a console error.
    assert page.request.get(path).status == 404
