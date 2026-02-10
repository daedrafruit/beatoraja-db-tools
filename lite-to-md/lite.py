from bs4 import BeautifulSoup
from pathlib import Path

HTML_FILE = "input.html"
OUT_MD = "output.md"

def clean(text):
    return " ".join(text.split())

def parse_html(html):
    soup = BeautifulSoup(html, "lxml")
    out = []

    for year_block in soup.select("dt.rowgroup"):
        year = year_block.get_text(strip=True).split()[0]

        table = year_block.find_next_sibling("dd", class_="tbody")
        if not table:
            continue

        rows = table.find_all("dl", recursive=False)

        out.append(f"\n## {year}\n")
        out.append("| Event | Organizer | Start | End | Days | Works | Description |")
        out.append("|------|-----------|-------|-----|------|-------|-------------|")

        for r in rows:
            cells = r.find_all(["dt", "dd"], recursive=False)
            if len(cells) < 7:
                continue

            # Event (with link)
            title_tag = cells[0].find("a")
            if title_tag:
                title = f"[{clean(title_tag.text)}]({title_tag['href']})"
            else:
                title = clean(cells[0].text)

            organizer = clean(cells[1].text)
            start = clean(cells[2].text)
            end = clean(cells[3].text).lstrip("/")
            days = clean(cells[4].text).strip("()")
            works = clean(cells[5].text) or "—"

            # Description: merge <p> tags
            desc_ps = cells[6].find_all("p")
            if desc_ps:
                desc = "<br>".join(clean(p.text) for p in desc_ps)
            else:
                desc = clean(cells[6].text) or "—"

            out.append(
                f"| {title} | {organizer} | {start} | {end} | {days} | {works} | {desc} |"
            )

    return "\n".join(out)

if __name__ == "__main__":
    html = Path(HTML_FILE).read_text(encoding="utf-8")
    md = parse_html(html)
    Path(OUT_MD).write_text(md, encoding="utf-8")
    print("Markdown written to output.md")
