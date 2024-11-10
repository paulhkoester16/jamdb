# DB data is heavily normalized, which means downstream code needs to jump through multiple
# merges anytime making a useful query.
# We wrap all those into this `Resolver` class.
# TODO -- 
#   Where possible, replace resolver methods here with VIEWS in the DB.
#   And are the remaining resolvers a good use case for graphene / graphql?

# 
# Also want:   
#   Song Summary page
#     Song info, like name, key, links to charts
#     What playlists does it belong to?
#     When/where have I performed it.


from collections import defaultdict
import pandas as pd
import copy
import json
from .globals import _format_id_as_str

def youtube_link_to_embed(link):
    embed_pref = "https://youtube.com/embed/"
    for prefix in ["https://youtu.be/", "https://youtube.com/"]:
        if link.startswith(prefix):
            embed_link = link.replace(prefix, embed_pref)
            if "?" in embed_link:
                embed_link, params = embed_link.split("?")
                params = params.split("&")
                for idx, param in enumerate(params):
                    if param.startswith("t="):
                        params[idx] = param.replace("t=", "start=")
                embed_link = embed_link + "?" + "&".join(params)
            return embed_link
    return ""

def _fill_na_to_list(df, col, tmp_fill=""):
    df[col] = df.fillna({col: tmp_fill})[col].apply(lambda x: [] if x == tmp_fill else x)

def _group_lists(df, group_by_cols, dedup=True):
    dg = df.copy()
    if isinstance(group_by_cols, (tuple, list)):
        if len(group_by_cols) == 1:
            composite_key = False
        else:
            composite_key = True
    else:
        composite_key = False
        group_by_cols = [group_by_cols]
        
    new_cols = [f"{col}s" for col in df.columns if col not in group_by_cols]
    for col in new_cols:
        dg[col] = dg[col[:-1]].apply(lambda x: [x])

    dg = dg.groupby(group_by_cols)[new_cols].sum().reset_index()
    if dedup:
        for col in new_cols:
            dg[col] = dg[col].apply(lambda x: sorted(list(set(x))))

    if composite_key:
        dg.index = dg[group_by_cols]
    else:
        group_by_cols = group_by_cols[0]
        dg.index = list(dg[group_by_cols])
    return dg


def _apply_lookup_on_lists_col(df, lookup_df, col):
    def intersection(x):
        if not isinstance(x, (list, set)):
            x = [x]
        return lookup_df.index.intersection(x)

    result = df[col].apply(lambda x: list(lookup_df.loc[intersection(x)]))
    return result

class Resolver:

    def __init__(self, db_handler):
        self.db_handler = db_handler

    def _processed_perf_videos(self):
        def add_embed(row):
            if row["source"].lower() == "youtube":
                embed = youtube_link_to_embed(row["link"])
                if embed != "":
                    row["embed_link"] = embed
            return row

        videos = (
            self.db_handler.query("SELECT * FROM PerformanceVideoView")
            .set_index("performance_video_id")
            .apply(lambda x: add_embed(x.to_dict()), axis=1)
            .reset_index()
            .rename(columns={0: "video"})            
        )
        return videos

    def _processed_ref_recordings(self):
        def add_embed(row):
            if row["source"].lower() == "youtube":
                embed = youtube_link_to_embed(row["link"])
                if embed != "":
                    row["embed_link"] = embed
            return row

        ref_recs = (
            self.db_handler.query("SELECT * FROM RefRecsView")
            .set_index("song_id")
            .apply(lambda x: add_embed(x.to_dict()), axis=1)
            .reset_index()
            .rename(columns={0: "reference_recording"})            
        )
        
        return ref_recs


    def get_denormalized_persons_df(self):
        try:
            return self.__denormalized_persons_df
        except AttributeError:

            def get_pics_for_person_id(person_id):
                return [
                    img_link
                    for img_link in list(self.db_handler.get_person_dir(person_id).glob("*"))
                    if img_link.suffix in [".jpeg", ".png"]
                ]

            contacts_lookup_df = (
                self.db_handler.query("SELECT * FROM ContactView").set_index("person_id")
                .drop(columns=["contact_id"]).apply(lambda x: x.to_dict(), axis=1)
            )
            
            insts_dict = (
                self.db_handler.query("SELECT * FROM PersonInstrumentView")
                .set_index("person_id")["instrument"].apply(lambda x: [x])
                .groupby("person_id").sum().to_dict()
            )

            songs_lookup_df = _group_lists(
                self.db_handler.query("SELECT * FROM SongView")[["song_id", "song"]],
                "song_id"
            ).apply(lambda x: x.to_dict(), axis=1)

            event_occ_lookup_df = (
                self.db_handler.query("SELECT event_occ_id as idx, * FROM EventOccView")
                .set_index("idx")[["event_occ_id", "event_occ", "event_occ_date"]]
                .apply(lambda x: x.to_dict(), axis=1)
            )

            song_perform_lookup_df = (
                self.db_handler.query("SELECT song_perform_id as idx, * FROM SongPerformView")
                .set_index("idx")[["song_perform_id", "event_occ_id", "song", "event_occ", "event_occ_date"]]
                .apply(lambda x: x.to_dict(), axis=1)
            )
            
            spv = _group_lists(
                (
                    self.db_handler.query("SELECT * FROM SongPerformerView")
                    [["person_id", "song_id", "event_occ_id", "song_perform_id"]]
                ),
                "person_id"
            )

            my_song_perform_ids = set(spv.loc[self.db_handler.me]["song_perform_ids"])
            spv["with_me_song_perform_ids"] = (
                spv["song_perform_ids"].apply(
                    lambda x: sorted(list(my_song_perform_ids.intersection(x)))
                )
            )

            output = (
                self.db_handler.query("SELECT * FROM PersonView")
                .rename(columns={"id": "person_id"})
            ).merge(
                spv, on="person_id", how="left"
            )

            for col in spv.columns:
                if col == "person_id":
                    continue
                _fill_na_to_list(output, col, tmp_fill="")

            output["contacts"] = _apply_lookup_on_lists_col(output, contacts_lookup_df, "person_id")

            output["instruments"] = output["person_id"].apply(
                lambda x: insts_dict.get(x, [])
            )
            output["pictures"] = output["person_id"].apply(get_pics_for_person_id)
            output["songs"] = _apply_lookup_on_lists_col(
                output, songs_lookup_df, "song_ids"
            )
            output["event_occs"] = _apply_lookup_on_lists_col(
                output, event_occ_lookup_df, "event_occ_ids"
            )
            output["songs_perform"] = _apply_lookup_on_lists_col(
                output, song_perform_lookup_df, "song_perform_ids"
            )
            output["songs_performed_with_me"] = _apply_lookup_on_lists_col(
                output, song_perform_lookup_df, "with_me_song_perform_ids"
            )
            
            output.index = list(output["person_id"])
            self.__denormalized_persons_df = output            
            return self.__denormalized_persons_df

    def get_denormalized_song_perform_df(self):
        try:
            return self.__denormalized_song_perform_df
        except AttributeError:
            def to_list(x):
                return [x]

            song_performer = self.db_handler.query(
                f"""
                SELECT
                    sp.song_perform_id,
                    sp.person_instrument_id,
                    sp.person_id,
                    p.public_name,
                    p.full_name,
                    i.instrument
                FROM
                    SongPerformerView as sp
                INNER JOIN InstrumentView as i
                   ON sp.instrument_id = i.instrument_id
                INNER JOIN PersonView as p
                   ON sp.person_id = p.person_id
                ;
                """
            )
            agg_players = _group_lists(
                (
                    _group_lists(
                        song_performer,
                        ["song_perform_id",  "person_id", "public_name", "full_name"]
                    )
                    .set_index("song_perform_id")
                    .apply(lambda x: x.to_dict(), axis=1)
                    .reset_index()
                    .rename(columns={0: "player"})
                ),
                "song_perform_id",
                dedup=False
            )
            
            videos = self._processed_perf_videos()
            videos["song_perform_id"] = videos["video"].apply(lambda x: x["song_perform_id"])
            videos = _group_lists(
                videos.set_index("song_perform_id")[["video"]],
                "song_perform_id",
                dedup=False
            )

            output = (
                self.db_handler.query("SELECT * FROM SongPerformView").merge(
                    agg_players,
                    on="song_perform_id",
                    how="left"
                ).merge(
                    videos,
                    on="song_perform_id",
                    how="left"
                )
            )
            for col in list(agg_players.columns) + list(videos.columns):
                if col == "song_perform_id":
                    continue
                _fill_na_to_list(output, col, tmp_fill="")

            for col in ["i_played", "has_video"]:
                output[col] = output[col].apply(lambda x: bool(x))

            output.index = list(output["song_perform_id"])
            self.__denormalized_song_perform_df = output
            return self.__denormalized_song_perform_df

    def get_denormalized_songs_df(self):
        try:
            return self.__denormalized_songs_df
        except AttributeError:
            ref_recs = self._processed_ref_recordings()
            ref_recs = _group_lists(
                ref_recs.set_index("song_id")[["reference_recording"]],
                "song_id",
                dedup=False
            )
            
            song_perfs = _group_lists(
                (
                    self.db_handler.query("SELECT song_id, song_perform_id, event_occ FROM SongPerformView")
                    .set_index("song_id")
                    .apply(lambda x: x.to_dict(), axis=1)
                    .reset_index()
                    .rename(columns={0: "song_perform"})
                ),
                "song_id",
                dedup=False
            )

            charts_dict = (
                self.db_handler.query("SELECT * FROM ChartsView").set_index("song_id")
                .apply(lambda row: [{"source": row["source"], "link": row["link"]}], axis=1)
                .groupby("song_id").sum().to_dict()
            )

            output = self.db_handler.query("SELECT * FROM SongView").merge(
                ref_recs,
                how="left",
                on="song_id"
            ).merge(
                song_perfs,
                how="left",
                on="song_id"
            )

            # output["reference_recordings"] =  output["song_id"].apply(lambda x: ref_recs_dict.get(x, []))
            output["charts"] =  output["song_id"].apply(lambda x: charts_dict.get(x, []))

            _fill_na_to_list(output, "reference_recordings", tmp_fill="")
            _fill_na_to_list(output, "song_performs", tmp_fill="")
            
            output.fillna("", inplace=True)
            for col in output.columns:
                output[col] = output[col].apply(lambda x: "" if x is None else x)

            output.index = list(output["song_id"])
            self.__denormalized_songs_df = output            
            return self.__denormalized_songs_df

    def get_denormalized_event_occ_df(self):
        try:
            return self.__denormalized_event_occ_df
        except AttributeError:

            sp = self.db_handler.query(
                f"""
                SELECT
                    sp.event_occ_id,
                    sp.person_id,
                    sp.song_id,
                    sp.song_perform_id,
                    p.public_name,
                    p.full_name,
                    i.instrument,
                    s.song
                FROM
                    SongPerformerView as sp
                INNER JOIN InstrumentView as i
                   ON sp.instrument_id = i.instrument_id
                INNER JOIN PersonView as p
                   ON sp.person_id = p.person_id
                INNER JOIN SongView as s
                   ON sp.song_id = s.song_id
                ;
                """
            )
            
            players_lookup_df =  _group_lists(
                (
                    _group_lists(
                        sp[["event_occ_id", "person_id", "public_name", "full_name", "instrument"]],
                        ["event_occ_id", "person_id", "public_name", "full_name"]
                    ).set_index("event_occ_id")
                    .apply(lambda x: x.to_dict(), axis=1)
                    .reset_index()
                    .rename(columns={0: "player"})
                ),
                "event_occ_id",
                dedup=False
            )
            songs_lookup_df = _group_lists(
                (
                    sp[["event_occ_id", "song_perform_id", "song_id", "song"]]
                    .drop_duplicates()
                    .set_index("event_occ_id")
                    .apply(lambda x: x.to_dict(), axis=1)
                    .reset_index()
                    .rename(columns={0: "song"})
                ),
                ["event_occ_id"],
                dedup=False
            )
            
            output = (
                self.db_handler.query("SELECT * FROM EventOccView").merge(
                    songs_lookup_df,
                    how="left",
                    on="event_occ_id"
                ).merge(
                    players_lookup_df,
                    on="event_occ_id",
                    how="left"
                )
            )
            
            for col in ["songs", "players"]:
                _fill_na_to_list(output, col, tmp_fill="")

            output.index = list(output["event_occ_id"])
            self.__denormalized_event_occ_df = output
            return self.__denormalized_event_occ_df

    def get_denormalized_event_gen_df(self):
        try:
            return self.__denormalized_event_gen_df
        except AttributeError:
            event_occ_df = _group_lists(
                (
                    self.get_denormalized_event_occ_df()[["event_gen_id", "event_occ_id", "event_occ"]]
                    .set_index("event_gen_id")
                    .apply(lambda x: x.to_dict(), axis=1)
                    .reset_index()
                    .rename(columns={"index": "event_gen_id", 0: "event_occ"})
                ),
                "event_gen_id",
                dedup=False
            )
            
            output = (
                self.db_handler.query("SELECT * FROM EventGenView").merge(
                    event_occ_df,
                    on="event_gen_id",
                    how="left"
                )
            )            
            _fill_na_to_list(output, "event_occs", tmp_fill="")
            
            output.index = list(output["event_gen_id"])
            self.__denormalized_event_gen_df = output
            return self.__denormalized_event_gen_df

    def get_denormalized_venue_df(self):
        try:
            return self.__denormalized_venue_df
        except AttributeError:
            event_gen_df = _group_lists(
                (
                    self.get_denormalized_event_gen_df()[["venue_id", "event_gen_id", "event_gen"]]
                    .set_index("venue_id")
                    .apply(lambda x: x.to_dict(), axis=1)
                    .reset_index()
                    .rename(columns={"index": "venue_id", 0: "event_gen"})
                ),
                "venue_id",
                dedup=False
            )

            output = self.db_handler.query("SELECT * FROM VenueView")
            output["zip"] = output["zip"].apply(_format_id_as_str)
            output["address_string"] = output.apply(
                lambda x: f"{x['address']}, {x['city']}, {x['state']}, {x['zip']}",
                axis=1
            )        
            output["google_map_string"] = output["address_string"].apply(
                lambda x: f"https://www.google.com/maps/place/{x}".replace(" ", "+")
            )

            output = output.merge(
                event_gen_df,
                on="venue_id",
                how="left"
            )
            _fill_na_to_list(output, "event_gens", tmp_fill="")            

            output.index = list(output["venue_id"])
            self.__denormalized_venue_df = output
            return self.__denormalized_venue_df

    def get_denormalized_performance_videos_df(self):
        spv = self.get_denormalized_song_perform_df()
        spv = (
            spv[spv["videos"].apply(lambda x: x != [])]
            .explode("videos").rename(columns={"videos": "video"})
        ).sort_values(["event_occ_date", "song"])        
        return spv
    
    def overview_event_occs(self):
        simp_event_occ = self.get_denormalized_event_occ_df().copy()
        
        simp_event_occ["event"] = simp_event_occ.apply(
            lambda x: {
                "event_occ_id": x["event_occ_id"],
                "event_name": x["event_occ"],
                "event_occ_date": x["event_occ_date"]
            },
            axis=1
        )
        
        simp_event_occ["event"] = (
            simp_event_occ[["event_occ_id", "event_occ", "event_occ_date"]]
            .apply(lambda x: x.to_dict(), axis=1)
        )
        
        
        simp_event_occ["venue"] = (
            simp_event_occ[["venue_id", "venue_name"]]
            .apply(lambda x: x.to_dict(), axis=1)
        )
        
        
        simp_event_occ = (
            simp_event_occ.sort_values("event_occ_date")
            [["event", "venue", "players", "songs"]]
        )

        return simp_event_occ
