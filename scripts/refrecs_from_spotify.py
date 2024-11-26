from pathlib import Path
import io
import argparse
import pandas as pd
import sys
import hashlib
import os
import copy
import tqdm
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth

REPO_ROOT = Path("./").absolute()
sys.path.append(str(REPO_ROOT))
from jamdb.db import DBHandler

SRC_DATA_DIR = REPO_ROOT / "data" / "source_data"
PLAYLIST_ID = "12euvBPoe0YGjQaC6OwtVf"


def row_to_hash(row):
    return hashlib.md5(str(row.to_dict().values()).encode()).hexdigest()

    
def normalize_song_name(song_name):
    song_name = song_name.lower().strip()
    for start in ["a ", "an ", "the "]:
        if song_name.startswith(start):
            song_name = song_name[len(start):]

    song_name = song_name.split("-")[0].strip()
    puncts = list("[](){},.?!';:-+=") + ['"']
    for punct in puncts:
        song_name = song_name.replace(punct, "")
    song_name = song_name.strip()
    song_name = song_name.replace(" ", "_")
    return song_name


def create_spotipy_conn():
    """
    Instantiates a `spotipy.Spotify`
    """
    # See
    #   https://developer.spotify.com/dashboard/applications/a7e542bfc30547f48b034ecb3c745435    
    # In particular, go to settings to regirster a redirect_uri
    spotify_client_id = os.environ["SPOTIFY_CLIENT_ID"]
    spotify_client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    spotify_client_uri = os.environ["SPOTIFY_REDIRECT_URI"]
    scope = "playlist-read-private,user-read-recently-played"

    spotipy_auth_manager = SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=spotify_client_uri,
        scope=scope
    )
    spotipy_conn = spotipy.Spotify(auth_manager=spotipy_auth_manager)
    return spotipy_conn


def get_tracks_for_playlist(spotipy_conn, playlist_uri):
    print("Downloading track info from Spotify...")
    tracks = []
    batch_size = 50
    offset = 0
    keep_going = True

    while keep_going:
        if offset % 200 == 0:
            print(offset)
        result = spotipy_conn.playlist_tracks(
            playlist_id=playlist_uri,
            limit=batch_size,
            offset=offset
        )
        offset += batch_size
        tracks.extend(result["items"])
        total = result["total"]

        if result["next"] is None:
            keep_going = False
        if offset >= result["total"]:
            keep_going = False

    return tracks


def simplify_tracks(tracks):
    return [
        {
            "source_id": "spotify",
            "link": track["track"]["external_urls"]["spotify"],
            "song_name_spotify": track["track"]["name"],
            "normalized_name": normalize_song_name(track["track"]["name"])
        }
        for track in tracks
    ]


def get_name_mapping(name_mapping_file, db_handler, songs_from_spotify, output_data_dir):
    reports_dir = output_data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    songs_in_jam_db = [
        {
            "id": row["id"],
            "song_name_in_jam_db": row["song"],
            "normalized_name": normalize_song_name(row["song"])
        }
        for _, row in db_handler.read_table("Song").iterrows()
    ]
    
    assert len({row["normalized_name"] for row in songs_in_jam_db}) == len(songs_in_jam_db)
    songs_in_jam_db = {row["normalized_name"]: row for row in songs_in_jam_db}
    
    name_mapping = pd.read_csv(name_mapping_file).to_numpy().tolist()
    already_seen = {row[2] for row in name_mapping}

    in_spotify_no_jamdb_match = []
    for song in songs_from_spotify:
        if song["link"] in already_seen:
            continue
        if song["normalized_name"] in songs_in_jam_db:
            db_song = songs_in_jam_db[song["normalized_name"]]
            song_id = db_song["id"]
            name_mapping.append([song_id, song["normalized_name"], song["link"]])
            already_seen.update([song["link"]])
        else:
            in_spotify_no_jamdb_match.append(["", song["normalized_name"], song["link"]])

    # === Report on songs in spotify playlist but no jamdb match =================
    in_spotify_no_jamdb_match = pd.DataFrame(
        in_spotify_no_jamdb_match,
        columns=["song_id", "spotify_normalized_name", "link"]
    ).sort_values("spotify_normalized_name")    

    in_spotify_no_jamdb_match_file = reports_dir / "songs_in_spotify_but_no_jamdb_match.csv"

    if len(in_spotify_no_jamdb_match) > 0:
        print(f"\n{len(in_spotify_no_jamdb_match)} songs in spotify playlist but no match to jamdb.")
        print(f"\tCheck {in_spotify_no_jamdb_match_file}")
    in_spotify_no_jamdb_match.to_csv(in_spotify_no_jamdb_match_file, index=None)
    # ============================================================================

    # === Report on songs in jamdb but no spotify playlist =======================
    ids_in_jamdb = {row["id"] for row in songs_in_jam_db.values()}
    ids_matched_in_spotify = {row[0] for row in name_mapping}
    in_jamdb_no_spotify = sorted(list(ids_in_jamdb.difference(ids_matched_in_spotify)))

    in_jambd_no_spotify_match_file = reports_dir / "songs_in_jamdb_but_no_spotify_match.txt"
    if len(in_jamdb_no_spotify) > 0:
        print(f"\n{len(in_jamdb_no_spotify)} songs in jambd but no match in spotify playlist.")
        print(f"\tCheck {in_jambd_no_spotify_match_file}")
    with open(in_jambd_no_spotify_match_file, "w") as fh:
        fh.write("\n".join(in_jamdb_no_spotify))
    # ============================================================================    

    # assert should be unnecessary as previous loop should have been deduping
    assert len({row[2] for row in name_mapping}) == len(name_mapping)
    
    name_mapping = {row[2]: row[0] for row in name_mapping}
    return name_mapping


def get_tracks_from_spotify(playlist_id):

    def write_spotify_payload(playlist_id, snapshot_id, simplified_tracks, payload_file):
        payload = {
            "playlist_id": playlist_id,
            "snapshot_id": snapshot_id,
            "tracks": simplified_tracks,
        }
        with open(payload_file, "w") as fh:
            json.dump(payload, fh)

    payload_file = SRC_DATA_DIR / "tmp_previous_spotify_playlist.json"    

    spotipy_conn = create_spotipy_conn()
    new_snapshot_id = spotipy_conn.playlist(playlist_id)["snapshot_id"]

    snapshot_id = new_snapshot_id
    songs_from_spotify = []
    try:
        with open(payload_file, "r") as fh:
            payload = json.load(fh)
            songs_from_spotify = payload["tracks"]
            snapshot_id = payload["snapshot_id"]
    except FileNotFoundError:
        pass

    if snapshot_id != new_snapshot_id or len(songs_from_spotify) == 0:
        if snapshot_id != new_snapshot_id:
            print("    Spotify snapshot id has updated, will download track info afresh from Spotify.")
        elif len(songs_from_spotify) == 0:
            print("    Cached spotify track info not found, will download track info afresh from Spotify.")

        tracks = get_tracks_for_playlist(spotipy_conn, playlist_id)
        songs_from_spotify = simplify_tracks(tracks)

        write_spotify_payload(playlist_id, new_snapshot_id, songs_from_spotify, payload_file)
    else:
        print("No changes to playlist detected, will use cached version.")

    return songs_from_spotify


def get_new_ref_recs(db_handler, table_name, output_data_dir):

    songs_from_spotify = get_tracks_from_spotify(PLAYLIST_ID)
    
    current_ref_recs = db_handler.read_table(table_name).query("source_id == 'spotify'")["link"].tolist()
    # check should be unnecessary as DB has a uniqueness constraint on link
    assert len(current_ref_recs) == len(set(current_ref_recs))
    current_ref_recs = set(current_ref_recs)

    name_mapping_file = SRC_DATA_DIR / "spotify_ref_rec_name_mapping.csv"
    name_mapping = get_name_mapping(name_mapping_file, db_handler, songs_from_spotify, output_data_dir)
        
    new_ref_recs = []
    for song in songs_from_spotify:    
        link = song["link"]
        if link in current_ref_recs:
            # skip those that are already in db
            continue
        try:
            song_id = name_mapping[link]
        except KeyError:
            print(f"{link} not found in name_mapping, skipping it.")
            continue
        new_ref_recs.append(
            {
                "song_id": song_id,
                "source_id": "spotify",
                "link": link
            }
        )
    
    new_ref_recs = pd.DataFrame(new_ref_recs)
    new_ref_recs["id"] = new_ref_recs.apply(row_to_hash, axis=1)
    return new_ref_recs


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='insert for spotify ref recs')
    parser.add_argument('data_dir')
    parser.add_argument('--db_file')
    args = parser.parse_args()
    
    table_name = "RefRec"
    
    data_dir = Path(args.data_dir)
    db_file = args.db_file
    if db_file is None:
        db_file = data_dir / "jamming.db"
    db_file = Path(db_file)
    db_handler = DBHandler.from_db_file(db_file)
    
    new_ref_recs = get_new_ref_recs(db_handler, table_name, output_data_dir=data_dir)


    if len(new_ref_recs) > 0:
        db_handler.insert(table_name, new_ref_recs.to_dict(orient="records"))        
        print(f"{table_name} table updated with new data")
    else:
        print(f"No new data detected for {table_name}, nothing to do!")
