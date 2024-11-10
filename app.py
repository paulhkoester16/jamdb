from collections import defaultdict
from flask import Flask, request, render_template
from wtforms import Form, SelectField, SubmitField

from jamdb.db import db_factory
from jamdb.resolvers import Resolver
from jamdb.globals import DATA_DIR

app = Flask(__name__) 


def init_db_handler():
    return db_factory(data_dir=DATA_DIR)


def init_resolver(db_handler=None):
    if db_handler is None:
        db_handler = init_db_handler()
    return Resolver(db_handler)

    

def get_index(resolver):
    index = {}

    query = "SELECT id, name FROM EventGen"
    index["Series"] = {
        "overview": {
            "nav_page": "overview_event_series"
        },
        "detail": {
            "nav_page": "detail_event_series",
            "id": "event_gen_id",
            "rows": list(resolver.db_handler.query(query).apply(lambda x: x.to_list(), axis=1))
        }
    }

    
    query = "SELECT id, name FROM EventOcc"
    index["Events"] = {
        "overview": {
            "nav_page": "overview_event_occs"
        },
        "detail": {
            "nav_page": "detail_event_occ",
            "id": "event_occ_id",
            "rows": list(resolver.db_handler.query(query).apply(lambda x: x.to_list(), axis=1))
        }
    }

    query = """
      SELECT
        sp.id, s.song || ' @ ' || e.name as sp_name
      FROM
        SongPerform as sp
      INNER JOIN Song as s
          on s.id = sp.song_id
      INNER JOIN EventOcc as e
          on e.id = sp.event_occ_id
      ORDER BY sp_name
    """
    index["Performed Songs"] = {
        "overview": {
            "nav_page": "overview_performed_songs"
        },
        "detail": {
            "nav_page": "detail_performed_song", 
            "id": "song_perform_id",
            "rows": list(resolver.db_handler.query(query).apply(lambda x: x.to_list(), axis=1))
        }
    }
    
    query = "SELECT id, public_name FROM Person"
    index["Players"] = {
        "overview": {
            "nav_page": "overview_players"
        },        
        "detail": {
            "nav_page": "detail_player",
            "id": "person_id",
            "rows": list(resolver.db_handler.query(query).apply(lambda x: x.to_list(), axis=1))
        }
    }

    query = "SELECT id, song FROM Song"
    index["Songs"] = {
        "overview": {
            "nav_page": "overview_songs"
        },
        "detail": {
            "nav_page": "detail_song",
            "id": "song_id",
            "rows": list(resolver.db_handler.query(query).apply(lambda x: x.to_list(), axis=1))
        }
    }

    query = "SELECT id, venue FROM Venue"
    index["Venues"] = {
        "detail": {
            "nav_page": "detail_venue",
            "id": "venue_id",
            "rows": list(resolver.db_handler.query(query).apply(lambda x: x.to_list(), axis=1))
        }
    }

    index["Videos"] = {
        "overview": {
            "nav_page": "overview_performance_videos"
        }
    }

    for item in index.values():
        if "detail" in item:
            item["detail"]["rows"] = [
                [
                    {
                        item["detail"]["id"]: x[0]
                    },
                    x[1]
                ] for x in item["detail"]["rows"]
            ]

    return index


def my_render_template(resolver, page_name, **kwargs):
    index = get_index(resolver)
    return render_template(f"{page_name}.html", page_name=page_name, index=index, **kwargs)


@app.route('/', methods=["GET", "POST"])
def index():
    page_name = "index"
    resolver = init_resolver()
    return my_render_template(resolver, page_name)


@app.route("/overview-event-occs/", methods=["GET"])
def overview_event_occs():
    page_name = "overview_event_occs"
    resolver = init_resolver()
    summaries = resolver.overview_event_occs().to_dict(orient="records")
    return my_render_template(resolver, page_name, summaries=summaries)


@app.route("/overview-event-series/", methods=["GET"])
def overview_event_series():
    page_name = "overview_event_series"
    resolver = init_resolver()
    summaries = resolver.get_denormalized_event_gen_df().to_dict(orient="records")
    return my_render_template(resolver, page_name, summaries=summaries)


@app.route("/overview-players/", methods=["GET"])
def overview_players():
    page_name = "overview_players"
    resolver = init_resolver()
    summaries = resolver.get_denormalized_persons_df().to_dict(orient="records")
    return my_render_template(resolver, page_name, summaries=summaries)


@app.route("/overview-songs/", methods=["GET"])
def overview_songs():
    page_name = "overview_songs"
    resolver = init_resolver()
    summaries = resolver.get_denormalized_songs_df().to_dict(orient="records")
    return my_render_template(resolver, page_name, summaries=summaries)


@app.route("/overview-performance_videos/", methods=["GET"])
def overview_performance_videos():
    page_name = "overview_performance_videos"
    resolver = init_resolver()
    summaries = resolver.get_denormalized_performance_videos_df().to_dict(orient="records")
    return my_render_template(resolver, page_name, summaries=summaries)


# @app.route("/overview-performed-songs/", methods=["GET"])
# def overview_performed_songs():
#     resolver = init_resolver()
#     summaries = resolver.overview_performed_songs().to_dict(orient="records")
#     return render_template("overview_performed_songs.html", summaries=summaries)



@app.route("/detail-event-occ/<string:event_occ_id>")
def detail_event_occ(event_occ_id):
    page_name = "detail_event_occ"    
    resolver = init_resolver()
    event = resolver.get_denormalized_event_occ_df().loc[event_occ_id].to_dict()
    return my_render_template(resolver, page_name, event=event)


@app.route("/detail-event-series/<string:event_gen_id>")
def detail_event_series(event_gen_id):
    page_name = "detail_event_series"
    resolver = init_resolver()
    event = resolver.get_denormalized_event_gen_df().loc[event_gen_id].to_dict()
    return my_render_template(resolver, page_name, event=event)


@app.route("/detail-performed-song/<string:song_perform_id>")
def detail_performed_song(song_perform_id):
    page_name = "detail_performed_song"
    resolver = init_resolver()
    song = resolver.get_denormalized_song_perform_df().loc[song_perform_id].to_dict()
    return my_render_template(resolver, page_name, song=song)


@app.route("/detail-song/<string:song_id>")
def detail_song(song_id):
    page_name = "detail_song"
    resolver = init_resolver()
    song = resolver.get_denormalized_songs_df().loc[song_id].to_dict()
    return my_render_template(resolver, page_name, song=song)


@app.route("/detail-player/<string:person_id>")
def detail_player(person_id):
    page_name = "detail_player"
    
    resolver = init_resolver()
    person = resolver.get_denormalized_persons_df().loc[person_id].to_dict()
    
    contacts = defaultdict(list)
    orig_contacts = person.pop("contacts", [])
    for contact in orig_contacts:
        if contact.get("link", "").strip() == "":
            continue
        contacts[contact["contact_type"]].append(contact["link"])
    person["contacts"] = contacts

    person["pictures"] = [str(pic_path.absolute()) for pic_path in person["pictures"]]

    with_me_ids = {x["song_perform_id"] for x in person["songs_performed_with_me"]}
    songs_perform = defaultdict(list)
    orig_songs_perform = person.pop("songs_perform", [])
    for sp in orig_songs_perform:
        if sp["song_perform_id"] not in with_me_ids:
            songs_perform[sp["event_occ_id"]].append(sp)
    songs_perform = sorted(
        [[k, v] for k, v in songs_perform.items()],
        key=lambda x: x[1][0]["event_occ_id"]
    )
    person["songs_performed_without_me"] = songs_perform

    songs_performed_with_me = defaultdict(list)
    orig_songs_performed_with_me = person.pop("songs_performed_with_me", [])
    for sp in orig_songs_performed_with_me:
        songs_performed_with_me[sp["event_occ_id"]].append(sp)
    songs_performed_with_me = sorted(
        [[k, v] for k, v in songs_performed_with_me.items()],
        key=lambda x: x[1][0]["event_occ_id"]
    )        
    person["songs_performed_with_me"] = songs_performed_with_me

    return my_render_template(resolver, page_name, person=person)


@app.route("/detail-venue/<string:venue_id>")
def detail_venue(venue_id):
    page_name = "detail_venue"
    resolver = init_resolver()
    venue = resolver.get_denormalized_venue_df().loc[venue_id].to_dict()
    return my_render_template(resolver, page_name, venue=venue)


if __name__ == '__main__':
    app.run()
