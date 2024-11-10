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


@app.route('/', methods=["GET", "POST"])
def index():
    print(f"index:  {request.method}")
    page_name = "index"
    return render_template(f"{page_name}.html", page_name=page_name)


@app.route("/overview-event-occs/", methods=["GET"])
def overview_event_occs():
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    summaries = resolver.overview_event_occs().to_dict(orient="records")
    page_name = "overview_event_occs"
    return render_template(f"{page_name}.html", page_name=page_name, summaries=summaries)


@app.route("/overview-event-series/", methods=["GET"])
def overview_event_series():
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    summaries = resolver.get_denormalized_event_gen_df().to_dict(orient="records")
    page_name = "overview_event_series"
    return render_template(f"{page_name}.html", page_name=page_name, summaries=summaries)


@app.route("/overview-players/", methods=["GET"])
def overview_players():
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    summaries = resolver.get_denormalized_persons_df().to_dict(orient="records")
    page_name = "overview_players"
    return render_template(f"{page_name}.html", page_name=page_name, summaries=summaries)    


@app.route("/overview-songs/", methods=["GET"])
def overview_songs():
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    summaries = resolver.get_denormalized_songs_df().to_dict(orient="records")
    page_name = "overview_songs"
    return render_template(f"{page_name}.html", page_name=page_name, summaries=summaries)


@app.route("/overview-performance_videos/", methods=["GET"])
def overview_performance_videos():
    resolver = init_resolver()
    summaries = resolver.get_denormalized_performance_videos_df().to_dict(orient="records")
    page_name = "overview_performance_videos"
    return render_template(f"{page_name}.html", page_name=page_name, summaries=summaries)


# @app.route("/overview-performed-songs/", methods=["GET"])
# def overview_performed_songs():
#     db_handler = init_db_handler()
#     resolver = Resolver(db_handler)
#     summaries = resolver.overview_performed_songs().to_dict(orient="records")
#     return render_template("overview_performed_songs.html", summaries=summaries)



@app.route("/detail-event-occ/<string:event_occ_id>")
def detail_event_occ(event_occ_id):
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    event = resolver.get_denormalized_event_occ_df().loc[event_occ_id].to_dict()
    page_name = "detail_event_occ"
    return render_template(f"{page_name}.html", page_name=page_name, event=event)


@app.route("/detail-event-gen/<string:event_gen_id>")
def detail_event_gen(event_gen_id):
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    event = resolver.get_denormalized_event_gen_df().loc[event_gen_id].to_dict()
    page_name = "detail_event_gen"
    return render_template(f"{page_name}.html", page_name=page_name, event=event)


@app.route("/detail-performed-song/<string:song_perform_id>")
def detail_performed_song(song_perform_id):
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    song = resolver.get_denormalized_song_perform_df().loc[song_perform_id].to_dict()
    page_name = "detail_performed_song"
    return render_template(f"{page_name}.html", page_name=page_name, song=song)


@app.route("/detail-song/<string:song_id>")
def detail_song(song_id):
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    song = resolver.get_denormalized_songs_df().loc[song_id].to_dict()
    page_name = "detail_song"
    return render_template(f"{page_name}.html", page_name=page_name, song=song)


@app.route("/detail-person/<string:person_id>")
def detail_person(person_id):
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
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

    page_name = "detail_person"
    return render_template(f"{page_name}.html", page_name=page_name, person=person)


@app.route("/detail-venue/<string:venue_id>")
def detail_venue(venue_id):
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    venue = resolver.get_denormalized_venue_df().loc[venue_id].to_dict()
    page_name = "detail_venue"
    return render_template(f"{page_name}.html", page_name=page_name, venue=venue)


if __name__ == '__main__':
    app.run()
