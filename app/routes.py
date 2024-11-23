from collections import defaultdict
import base64
from flask import current_app as app
from flask import Flask, render_template

from jamdb.globals import ME_ID, DATA_DIR, DB_FILE
from jamdb.graphene import GrapheneSQLSession

REDACT_PRIVATE = True     # this should be an env var

def sort_links(links):
    links = sorted(links, key=lambda row: row["linksource"]["rank"])
    return links


def init_graphene_session():
    return GrapheneSQLSession.from_sqlite_file(DB_FILE)


def my_render_template(graphene_session, page_name, **kwargs):
    index = _create_index(graphene_session)
    nav_page_has_my_table = {
        entity["pages"]["overview"]["nav_page"]
        for entity in index.values()
        if "overview" in entity["pages"]
    }
    kwargs.update(
        {"page_name": page_name, "index": index, "nav_page_has_my_table": nav_page_has_my_table}
    )
    return render_template(f"{page_name}.html", **kwargs)


def convert_image_to_base64(image_path):
    """Converts an image to base64 encoding."""

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string        


@app.route('/', methods=["GET", "POST"])
def index():
    page_name = "index"
    g_session = init_graphene_session()    
    return my_render_template(g_session, page_name)


@app.route("/overview-event-occs/", methods=["GET"])
def overview_event_occs():
    page_name = "overview_event_occs"
    g_session = init_graphene_session()
    summaries = g_session.execute(
        """
        query {
          eventOccs {
            id, name, date, venue { id, venue },
            songPerforms { id, song { id, song } }
            players { person { id, publicName } }
            eventgen { name }
          }
        }
        """
    ).data["eventOccs"]
    summaries = sorted(
        summaries,
        key=lambda x: (x["eventgen"]["name"].lower(), x["date"].lower())
    )
    return my_render_template(g_session, page_name, summaries=summaries)


@app.route("/overview-event-series/", methods=["GET"])
def overview_event_series():
    page_name = "overview_event_series"
    g_session = init_graphene_session()
    summaries = g_session.execute(
        """
        query {
          eventGens {
            id, name, genre { genre }, time, date, venue { id, venue },
            person { id, publicName }, eventOccs { id, name }
          }
        }""",
    ).data["eventGens"]
    for event in summaries:
        event["host"] = event.pop("person")
    summaries = sorted(summaries, key=lambda x: x["name"].lower())
    return my_render_template(g_session, page_name, summaries=summaries)


@app.route("/overview-players/", methods=["GET"])
def overview_players():
    page_name = "overview_players"
    g_session = init_graphene_session()
    summaries = g_session.execute(
        """
        query {
          persons {
            id, combinedName, instrumentList, 
            eventsAttended {id, name}, songPerforms {id, song { song } }
          }
        }
        """
    ).data["persons"]
    summaries = sorted(summaries, key=lambda x: x["combinedName"].lower())
    return my_render_template(g_session, page_name, summaries=summaries)


@app.route("/overview-songs/", methods=["GET"])
def overview_songs():
    page_name = "overview_songs"
    g_session = init_graphene_session()
    summaries = g_session.execute(
        """
        query {
          songs {
            id, song, key { keyName }, subgenre { subgenreName }
            songPerforms { id, eventocc { name } }
          }
        }
        """
    ).data["songs"]
    summaries = sorted(summaries, key=lambda x: x["song"].lower())
    return my_render_template(g_session, page_name, summaries=summaries)

    
@app.route("/overview-performance_videos/", methods=["GET"])
def overview_performance_videos():
    page_name = "overview_performance_videos"
    g_session = init_graphene_session()
    summaries = g_session.execute(
        """
        query {
          performanceVideos {
            id, link, embeddableLink,
            songperform {
              id, song { song }, eventocc { id, name, date },
              players { person {id, publicName}, instrumentList }
            }
          }
        }
        """
    ).data["performanceVideos"]
    summaries = sorted(
        summaries,
        key=lambda x: (x["songperform"]["song"]["song"].lower(), x["songperform"]["eventocc"]["date"].lower())
    )
    
    return my_render_template(g_session, page_name, summaries=summaries)


@app.route("/overview-performed-songs/", methods=["GET"])
def overview_performed_songs():
    page_name = "overview_performed_songs"
    g_session = init_graphene_session()
    summaries = g_session.execute(
        """
        query {
          songPerforms {
            id, songPerformName, song { id, song }, eventocc { id, name, date },
            players { person {id, publicName}, instrumentList },
            performanceVideos { songPerformId, sourceId, linksource {rank}, link, embeddableLink, displayName}
          }
        }"""
    ).data["songPerforms"]
    summaries = sorted(
        summaries, key=lambda x: (x["song"]["song"].lower(), x["eventocc"]["date"].lower())
    )
    for song in summaries:
        song["performanceVideos"] = sort_links(song["performanceVideos"])
    return my_render_template(g_session, page_name, summaries=summaries)


@app.route("/detail-event-occ/<string:event_occ_id>")
def detail_event_occ(event_occ_id):
    page_name = "detail_event_occ"    
    g_session = init_graphene_session()
    event = g_session.execute(
        """
        query getEventOcc ($id: ID) {
          eventOcc (id: $id) {
            id, name, date, eventgen { id, name, venue { id, venue } },
            songPerforms { id, song { id, song } },
            players { person {id, publicName}, instrumentList }
          }
        }
        """,
        variables={"id": event_occ_id}
    ).data["eventOcc"]
    return my_render_template(g_session, page_name, event=event)


@app.route("/detail-event-series/<string:event_gen_id>")
def detail_event_series(event_gen_id):
    page_name = "detail_event_series"
    g_session = init_graphene_session()
    event = g_session.execute(
        """
        query getEventGen ($id: ID) {
          eventGen (id: $id) {
            id, name, genre { genre }, time, date, venue { id, venue },
            person { id, publicName }, eventOccs { id, name }
          }
        }""",
        variables={"id": event_gen_id}
    ).data["eventGen"]
    event["host"] = event.pop("person")
    return my_render_template(g_session, page_name, event=event)


@app.route("/detail-performed-song/<string:song_perform_id>")
def detail_performed_song(song_perform_id):
    page_name = "detail_performed_song"
    g_session = init_graphene_session()
    song = g_session.execute(
        """
        query getSongPerform ($id: ID) {
          songPerform (id: $id) {
            id, songPerformName, song { id, song }, eventocc { id, name },
            players { person {id, publicName}, instrumentList },
            performanceVideos { songPerformId, link, embeddableLink}
          }
        }""",
        variables={"id": song_perform_id}
    ).data["songPerform"]
    return my_render_template(g_session, page_name, song=song)


@app.route("/detail-song/<string:song_id>")
def detail_song(song_id):
    page_name = "detail_song"
    g_session = init_graphene_session()
    song = g_session.execute(
        """
        query getSong($id: ID) {
          song(id: $id) {
            id, song, key { keyName }, subgenre { subgenreName }
            songPerforms { id, eventocc { name } }
            charts { sourceId, linksource {rank}, link, embeddableLink, displayName }
            refRecs { sourceId, linksource {rank}, link, embeddableLink, displayName }
          }
        }
        """,
        variables={"id": song_id}
    ).data["song"]
    song["charts"] = sort_links(song["charts"])
    song["refRecs"] = sort_links(song["refRecs"])
    return my_render_template(g_session, page_name, song=song)


@app.route("/detail-player/<string:person_id>")
def detail_player(person_id):
    page_name = "detail_player"
    g_session = init_graphene_session()
    person = g_session.execute(
        """
        query getPerson($id: ID, $otherPersonId: ID) {
          person (id: $id) {
            id, fullName, publicName, instrumentList
            contacts { id, contactTypeId, contacttype {displayName, rank}, link, private, displayName },
            eventsAttended { id, name, date },
            songsPerformedWith(otherPersonId: $otherPersonId) { id, songPerformName },
            songsPerformedWithout(otherPersonId: $otherPersonId) { id, songPerformName },
            personPictures { link }
          }
        }
        """,
        variables={"id": person_id, "otherPersonId": ME_ID}
    ).data["person"]
    
    contacts_by_type = defaultdict(list)
    for contact in person["contacts"]:
        if REDACT_PRIVATE and contact["private"]:
            continue
        contacts_by_type[contact["contactTypeId"]].append(contact)

    contacts_by_type = [
        {
            "contactTypeId": contact_type[0]["contactTypeId"],
            "contactTypeDisplayName": contact_type[0]["contacttype"]["displayName"],
            "contactTypeRank": contact_type[0]["contacttype"]["rank"],
            "contacts": contact_type
        }
        for contact_type in contacts_by_type.values()
        if len(contact_type) > 0
    ]
    contacts_by_type = sorted(contacts_by_type, key=lambda x: x["contactTypeRank"])
    person["contacts_by_type"] = contacts_by_type

    return my_render_template(g_session, page_name, person=person)


@app.route("/detail-venue/<string:venue_id>")
def detail_venue(venue_id):
    page_name = "detail_venue"
    g_session = init_graphene_session()
    venue = g_session.execute(
        """
        query getVenue ($id: ID) {
          venue (id: $id) {
            venue, addressString, googleMapString, web
            hostedEventSeries { id, name }
          }
        }
        """,
        variables={"id": venue_id}
    ).data["venue"]

    return my_render_template(g_session, page_name, venue=venue)


def _create_index(graphene_session):
    result = graphene_session.execute("""query {
        eventGens { id, name }
        eventOccs { id, name, date, eventgen { name } }
        songPerforms { id, songPerformName, eventocc { date }, song { song } }
        persons { id, publicName }
        songs { id, song }
        venues { id, venue }
    }""").data
    result["eventGens"] = sorted(
        result["eventGens"],
        key=lambda x: x["name"].lower()
    )
    result["eventOccs"] = sorted(
        result["eventOccs"],
        key=lambda x: (x["eventgen"]["name"].lower(), x["date"].lower())
    )
    result["songPerforms"] = sorted(
        result["songPerforms"],
        key=lambda x: (x["song"]["song"].lower(), x["eventocc"]["date"].lower())
    )
    result["persons"] = sorted(
        result["persons"],
        key=lambda x: x["publicName"].lower()
    )
    result["songs"] = sorted(
        result["songs"].lower(),
        key=lambda x: x["song"].lower()
    )
    result["venues"] = sorted(
        result["venues"], key=lambda x: x["venue"].lower()
    )
    result = {
        entity_name: [list(row.values()) for row in key_vals]
        for entity_name, key_vals in result.items()
    }
    
    index = {
        "Series": {
            "overview": {
                "nav_page": "overview_event_series"
            },
            "detail": {
                "nav_page": "detail_event_series",
                "id": "event_gen_id",
                "rows": result["eventGens"]
            }
        },
        "Events": {
            "overview": {
                "nav_page": "overview_event_occs"
            },
            "detail": {
                "nav_page": "detail_event_occ",
                "id": "event_occ_id",
                "rows": result["eventOccs"]
            }
        },
        "Performed Songs": {
            "overview": {
                "nav_page": "overview_performed_songs"
            },
            "detail": {
                "nav_page": "detail_performed_song", 
                "id": "song_perform_id",
                "rows": result["songPerforms"]
            }
        },
        "Players": {
            "overview": {
                "nav_page": "overview_players"
            },        
            "detail": {
                "nav_page": "detail_player",
                "id": "person_id",
                "rows": result["persons"]
            }
        },
        "Songs": {
            "overview": {
                "nav_page": "overview_songs"
            },
            "detail": {
                "nav_page": "detail_song",
                "id": "song_id",
                "rows": result["songs"]
            }
        },
        "Venues": {
            "detail": {
                "nav_page": "detail_venue",
                "id": "venue_id",
                "rows": result["venues"]
            }
        },
        "Videos": {
            "overview": {
                "nav_page": "overview_performance_videos"
            }
        }    
    }

    for item in index.values():
        if "detail" in item:
            item["detail"]["rows"] = [
                [{ item["detail"]["id"]: x[0]}, x[1]] for x in item["detail"]["rows"]
            ]

    index = {k: {"pages": v} for k, v in index.items()}
    for display_name, v in index.items():
        v["nav_pages"] = [x["nav_page"] for x in v["pages"].values()]
        if "detail" in v["pages"]:
            detail = v["pages"]["detail"]
            dropdown = []
            if "overview" in v["pages"]:
                overview = v["pages"]["overview"]
                dropdown.append(
                    {
                        "type": "header",
                        "header_name": "Overview"
                    }
                )
                dropdown.append(
                    {
                        "type": "ref",
                        "nav_page": overview["nav_page"],
                        "nav_kwargs": {},
                        "nav_display": f"Overview {display_name}"
                    }
                )
                dropdown.append(
                    {
                        "type": "header",
                        "header_name": "Detail view"
                    }
                )
            for row in detail["rows"]:
                dropdown.append(
                    {
                        "type": "ref",
                        "nav_page": detail["nav_page"],
                        "nav_kwargs": row[0],
                        "nav_display": row[1]
                    }
                )
            v["dropdown"] = dropdown
        else:
            overview = v["pages"]["overview"]
            v["non_dropdown"] = [
                {
                    "type": "ref",
                    "nav_page": overview["nav_page"],
                    "nav_display": display_name
                }
            ]
    return index
