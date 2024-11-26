import sys
import copy
import argparse
import hashlib
import json
import tqdm
import PyPDF2
import pandas as pd
from pathlib import Path
from shutil import rmtree

REPO_ROOT = Path("./").absolute()
sys.path.append(str(REPO_ROOT))

from jamdb.db import DBHandler

SRC_DATA_DIR = REPO_ROOT / "data" / "source_data"


def row_to_hash(row):
    return hashlib.md5(str(row.to_dict().values()).encode()).hexdigest()


def normalize_song_name(song_name):
    song_name = song_name.lower().strip()
    for start in ["a ", "an ", "the "]:
        if song_name.startswith(start):
            song_name = song_name[len(start):]

    puncts = list("[](){},.?!';:-+=") + ['"']
    for punct in puncts:
        song_name = song_name.replace(punct, "")
    song_name = song_name.strip()
    song_name = song_name.replace(" ", "_")
    return song_name


def parse_ireal_playlist_html(html_file):
    # export playlist from iReal and save to disk to get the html file
    songs = []
    host = "irealb://"

    if not isinstance(html_file, Path):
        html_file = Path(html_file)

    content = html_file.read_text()
    content = content[content.find("<body"):]
    content = content[:content.find("</body>")] + "</body>"
    for br in ["<br>", "<br/>", "<br />"]:
        content = content.replace(br, " ")
    
    content = content.strip()
        
    _, content = content.split("<h3>", 1)
    a_href, content = content.split("</h3>")
    _, a_href = a_href.split(host)
    a_href = a_href.split('">')[0].strip()
    a_hrefs = [f"{host}{href}" for href in a_href.split("===")]
    # always appear to be 1 more than expected, and last is very small and not a song -- maybe playist name?    
    a_hrefs = a_hrefs[:-1]    
    
    names = content.split("</p>")[0].split("<p>")[-1].strip()

    if names.startswith("1. "):
        names = names[3:]

    names += f" {len(a_hrefs) + 1}. "

    for idx, href in tqdm.tqdm(enumerate(a_hrefs)):
        split_point = f" {idx + 2}. "
        name, names = names.split(split_point)
        name = name.strip()

        for ex_name in ["Blues", "Modal"]:
            if name.startswith(f"{ex_name} - "):
                name = name.replace(f"{ex_name} - ", f"{ex_name} : ")
        try:
            song_name, composers = name.split(" - ", 1)
        except ValueError as exc:
            print(f"{name}; {exc}")
            song_name = name.strip()
            composers = ""
        song_name = song_name.strip()
        song_name = song_name.replace("(RBB)", "").strip()
        if song_name.endswith(", The"):
            song_name = ("The " + song_name[:-len(", The")]).strip()
            
        composers = composers.strip()
        songs.append(
            {
                "song_name": song_name,
                "composers": composers,
                "i_real_href": href,
                "dirty_name": name,
                "normalized_name": normalize_song_name(song_name)
            }
        )
    return songs


def write_charts(pdf_file, ireal_songs_list, jam_songs, charts_dir):
    charts_dir = Path(charts_dir)

    with open(pdf_file, 'rb') as fh:
        pdf_reader = PyPDF2.PdfReader(fh)
        num_pages = len(pdf_reader.pages)
        assert len(ireal_songs_list) == num_pages
        
        for page_num in tqdm.tqdm(range(num_pages)):
            ireal_song = ireal_songs_list[page_num]
            normalized_name = ireal_song["normalized_name"]

            song_id = None
            for id_, song in jam_songs.items():
                for ireal in song.get("from_ireal", []):
                    if normalized_name == ireal["normalized_name"]:
                        song_id = id_
                        break
                if song_id is not None:
                    break
                # If we've already found it, stop looking

            if song_id is None:
                # if we haven't found it, then don't write pdfs
                continue

            ireal_song_name = ireal_song["normalized_name"]
            song_dir = charts_dir / song_id
            song_dir.mkdir(parents=True, exist_ok=True)
            output_filestem = song_dir / f"{ireal_song_name}_ireal"
            
            pdf_writer = PyPDF2.PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[page_num])

            with open(f"{output_filestem}.pdf", 'wb') as fh:
                pdf_writer.write(fh)
            with open(f"{output_filestem}.json", 'w') as fh:
                json.dump(ireal_song, fh)


def append_from_ireal(song, ireal_song):
    if "from_ireal" not in song:
        song["from_ireal"] = []
    
    if ireal_song["i_real_href"] not in {x["i_real_href"] for x in song["from_ireal"]}:
        song["from_ireal"].append(copy.deepcopy(ireal_song))


def create_charts_from_ireal(db_handler, source_dir, output_data_dir):
    """
    On recurring basis, 
    1. Go into iReal and create a playlist with ALL songs.
    2. Then **Share** and select "Save to Disk", this will save an html file, rename to `ireal_charts.html`
    3. The repeat, but second time, save as pdf, and name `ireal_charts.pdf`
    4. This function will TRY to match db songs to the iReal songs, but matching won't be perfect.
       Thus, we use `ireal_name_mapping.csv` for pairs that are not auto-matched.
    These 3 files all need to be placed in `source_dir`.

    When this job runs, it will report on which jam db songs don't have matching iReal.
    Review this report on recurring basis, both the append name matches when needed AND
    to inform which iReal charts need to be creaed.    
    """

    # TODO - gracefully fail if ireal charts are not provided
    
    source_dir = Path(source_dir)
    output_data_dir = Path(output_data_dir)
    
    html_playlist = source_dir / "ireal_charts.html"
    pdf_playlist = source_dir / "ireal_charts.pdf"
    name_mapping_file = source_dir / "ireal_name_mapping.csv"

    charts_dir = output_data_dir / "charts"
    if charts_dir.exists():
        print(f"Removing {charts_dir}")
        rmtree(charts_dir)

    
    reports_dir = output_data_dir / "reports"


    songs_from_ireal_list = parse_ireal_playlist_html(html_playlist)
    assert len({row["normalized_name"] for row in songs_from_ireal_list}) == len(songs_from_ireal_list)
    songs_from_ireal = {row["normalized_name"]: row for row in songs_from_ireal_list}

    songs_in_jam_db = {
        row["id"]: {
            "song_name_in_jam_db": row["song"],
            "normalized_name": normalize_song_name(row["song"])
        }
        for _, row in db_handler.read_table("Song")[["id", "song"]].iterrows()
    }
    
    name_mapping = pd.read_csv(name_mapping_file).to_numpy().tolist()

    for song_id, song in songs_in_jam_db.items():
        if song["normalized_name"] in songs_from_ireal:
            name_mapping.append([song_id, song["normalized_name"]])
    
    for row in name_mapping:
        song = songs_in_jam_db[row[0]]
        i_real_song = songs_from_ireal[row[1]]
        append_from_ireal(song, i_real_song)

    write_charts(pdf_playlist, songs_from_ireal_list, songs_in_jam_db, charts_dir)

    no_ireal = sorted(list({id_ for id_, song in songs_in_jam_db.items() if song.get("from_ireal", []) == []}))
    
    reports_dir.mkdir(parents=True, exist_ok=True)
    no_ireal_file = reports_dir / "song_ids_with_no_ireal_charts.txt"

    if len(no_ireal) > 0:
        print(f"{len(no_ireal)} songs with no ireal chart.\nCheck {no_ireal_file}")
    
    with open(no_ireal_file, "w") as fh:
        fh.write("\n".join(no_ireal))


def process_charts(data_dir, charts_df):
    ireal_charts = []
    for song_dir in (data_dir / "charts").glob("*"):
        for chart_file in song_dir.glob("*"):
            chart = {"song_id": song_dir.stem}
            if chart_file.suffix == ".pdf":
                chart["source_id"] = "pdf"
                chart["link"] = str(chart_file.relative_to(data_dir))
                chart["display_name"] = chart_file.stem
            elif chart_file.suffix == ".json" and chart_file.stem.endswith("_ireal"):
                data = json.loads(chart_file.read_text())
                chart["source_id"] = "ireal"
                chart["link"] = data["i_real_href"]
                chart["display_name"] = f"{data['song_name']} (click to download into iReal)"            
            else:
                print(f"Unkown chart format:  {chart_file}")
                continue
            ireal_charts.append(copy.deepcopy(chart))
    ireal_charts = pd.DataFrame(ireal_charts)

    ireal_charts["id"] = ireal_charts.apply(row_to_hash, axis=1)
    print(f"    Original size of Charts df:  {charts_df.shape}")
    print(f"    Size of iReal Charts:        {ireal_charts.shape}")
    already_seen_charts = set(charts_df["id"])
    charts_df = (
        ireal_charts.loc[
            ireal_charts["id"].apply(lambda x: x not in already_seen_charts)
        ]
    )
    print(f"    Number of NEW charts:        {charts_df.shape}")    
    return charts_df


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='insert for ireal charts')
    parser.add_argument('data_dir')
    parser.add_argument('--db_file')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    db_file = args.db_file
    if db_file is None:
        db_file = data_dir / "jamming.db"
    db_file = Path(db_file)
    db_handler = DBHandler.from_db_file(db_file)

    create_charts_from_ireal(
        db_handler=db_handler,
        source_dir=SRC_DATA_DIR,
        output_data_dir=data_dir
    )
    table_name = "Chart"

    existing_charts = db_handler.read_table(table_name)

    df = process_charts(data_dir, existing_charts)
    db_handler.insert(table_name, df.to_dict(orient="records"))
            
    print(f"{table_name} table updated!")
