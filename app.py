from collections import defaultdict
from flask import Flask, request, render_template
from wtforms import Form, SelectField, SubmitField

from jamdb.db import db_factory
from jamdb.resolvers import Resolver
from jamdb.globals import DATA_DIR

app = Flask(__name__) 

def init_db_handler():
    return db_factory(data_dir=DATA_DIR)

class GetRowForm(Form):

    table_name = SelectField("table_name")
    primary_key = SelectField("primary_key")
    submit = SubmitField("submit")

    def possible_table_choices(self):
        db_handler = init_db_handler()
        choices = [("", "--choose--")]
        choices.extend(
            [
                (table_name, table_name) for table_name in db_handler.table_names()
            ]
        )
        return choices

    def possible_pk_choices(self, table_name):
        db_handler = init_db_handler()
        choices = [("", "--choose--")]
        ent = db_handler.entities.get(table_name)
        if ent is not None:
            pk_name = ent.primary_key
            pks = list(db_handler.query(f"SELECT {pk_name} FROM {table_name}")[pk_name])
            choices.extend([(pk, pk) for pk in pks])
        return choices


@app.route('/', methods=["GET", "POST"])
def index():
    print(f"index:  {request.method}")
    return render_template("index.html")


@app.route('/get-row/', methods=["GET", "POST"])
def get_row():
    form = GetRowForm(request.form)
    print(f"get-row:  {request.method}")
    form.table_name.choices = form.possible_table_choices()
    if request.method == "POST" and form.table_name.data:
        form.primary_key.choices = form.possible_pk_choices(form.table_name.data)
    return render_template("get_row.html", form=form)


@app.route("/performed-songs-summaries/", methods=["GET"])
def performed_songs_summaries():

    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    summaries = [
        resolver.summarize_performed_song(id_)
        for id_ in resolver.db_handler.query("SELECT * FROM SongPerform ORDER BY song_id")["id"]
    ]
    summaries = sorted(
        summaries,
        key=lambda song: (song["event_occ"]["event_occ_date"], song["song"]["song"])
    )
    summaries_by_event = defaultdict(list)
    for summary in summaries:
        summaries_by_event[summary["event_occ"]["event"]].append(summary)
    summaries_by_event = list(summaries_by_event.values())
    summaries_by_event = sorted(
        summaries_by_event,
        key=lambda event: event[0]["event_occ"]["event_occ_date"]
    )

    return render_template("performed_songs_summaries.html", summaries_by_event=summaries_by_event)


@app.route('/get-row-read/', methods=['POST']) 
def get_row_read():
    db_handler = init_db_handler()
    print(f"get-row-read:  {request.method}")    
    data = request.form
    print(data)
    result = db_handler.get_row(
        table_name=data["table_name"],
        primary_key=data["primary_key"]
    )

    return result

@app.route("/overview-event-occs/", methods=["GET"])
def overview_event_occs():
    db_handler = init_db_handler()
    resolver = Resolver(db_handler)
    summaries = resolver.overview_event_occs().to_dict(orient="records")
    return render_template("overview_event_occs.html", summaries=summaries)


# @app.route("/overview-performed-songs/", methods=["GET"])
# def overview_performed_songs():
#     db_handler = init_db_handler()
#     resolver = Resolver(db_handler)
#     summaries = resolver.overview_performed_songs().to_dict(orient="records")
#     return render_template("overview_performed_songs.html", summaries=summaries)


# @app.route("/overview-songs/", methods=["GET"])
# def overview_songs():
#     db_handler = init_db_handler()
#     resolver = Resolver(db_handler)
#     summaries = resolver.overview_songs().to_dict(orient="records")
#     return render_template("overview_songs.html", summaries=summaries)


# @app.route("/overview-people/", methods=["GET"])
# def overview_people():
#     db_handler = init_db_handler()
#     resolver = Resolver(db_handler)
#     summaries = resolver.overview_people().to_dict(orient="records")
#     return render_template("overview_people.html", summaries=summaries)


# @app.route("/detail-event-occ/", methods=["GET", "POST"])
# def detail_event_occ():
#     db_handler = init_db_handler()
#     return render_template("detail_event_occ.html")


# @app.route("/detail-performed-song/", methods=["GET", "POST"])
# def detail_performed_song():
#     db_handler = init_db_handler()
#     return render_template("detail_performed_song.html")


# @app.route("/detail-song/", methods=["GET", "POST"])
# def detail_performed_song():
#     db_handler = init_db_handler()
#     return render_template("detail_song.html")


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
    
    return render_template("detail_person.html", person=person)

# @app.route("/detail-venue/", methods=["GET", "POST"])
# def detail_venue():
#     db_handler = init_db_handler()
#     return render_template("detail_venue.html")


if __name__ == '__main__':
    app.run()
