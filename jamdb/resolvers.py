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

def fill_na_to_list(df, col, tmp_fill=""):
    df[col] = df.fillna({col: tmp_fill})[col].apply(lambda x: [] if x == tmp_fill else x)


class Resolver:
    # TODO -- How much of these should be defined as VIEWS in the DB?

    def __init__(self, db_handler):
        self.db_handler = db_handler
    
    def _create_song_perform(self):
        df = self.db_handler.query("SELECT * FROM SongPerform").set_index("id")

        def _create_player_insts(row):
            pis = []
            if row["instrument_id"] is not None:
                me_id = self.db_handler.me
                my_inst_id = row["instrument_id"]
                my_person_inst_id = self.db_handler.query(
                    f"""SELECT id FROM PersonInstrument WHERE
                    person_id = '{me_id}' AND instrument_id = '{my_inst_id}'"""
                )["id"][0]  # DB constraint enures this is singleton
                pis.append(my_person_inst_id)
            pis.extend(
                [
                    val for col, val in row.items()
                    if col.startswith("other_player") and val is not None
                ]
            )
            return pis
            
        df["players_insts"] = df.apply(_create_player_insts, axis=1)

        pis = self.db_handler.query("SELECT * FROM PersonInstrument").set_index("id")
        pi_to_p = pis["person_id"].to_dict()
        pi_to_i = pis["instrument_id"].to_dict()

        df["players"] = df["players_insts"].apply(
            lambda pis: [pi_to_p[pi] for pi in pis]
        )
        df["instruments"] = df["players_insts"].apply(
            lambda pis: [pi_to_i[pi] for pi in pis]
        )
        self.__song_perform_df = df

    @property
    def _song_perform_df(self):
        try:
            return self.__song_perform_df
        except AttributeError:
            self._create_song_perform()
            return self.__song_perform_df
    
    def _create_song_person_mappings(self):
        song_to_players = defaultdict(list)
        player_to_songs = defaultdict(list)
        player_to_events = defaultdict(set)
        event_to_players = defaultdict(set)
        
        for song_perf_id, row in self._song_perform_df.iterrows():
            players = row["players"]
            song_to_players[song_perf_id].extend(players)
            event_to_players[row["event_occ_id"]].update(players)
            for player_id in players:
                player_to_songs[player_id].append(song_perf_id)
                player_to_events[player_id].update({row["event_occ_id"]})

        
        self.__players_on_song_perf = song_to_players
        self.__songs_perf_by_player = player_to_songs
        self.__players_at_event = {k: sorted(list(v)) for k, v in event_to_players.items()}
        self.__events_attended_by_player = {k: sorted(list(v)) for k, v in player_to_events.items()}

    @property
    def _songs_perf_by_player(self):
        try:
            return self.__songs_perf_by_player
        except AttributeError:
            self._create_song_person_mappings()
            return self.__songs_perf_by_player            

    @property
    def _players_on_song_perf(self):
        try:
            return self.__players_on_song_perf
        except AttributeError:
            self._create_song_person_mappings()
            return self.__players_on_song_perf

    @property
    def _players_at_event_perf(self):
        try:
            return self.__players_at_event
        except AttributeError:
            self._create_song_person_mappings()
            return self.__players_at_event

    @property
    def _events_attended_by_player(self):
        try:
            return self.__events_attended_by_player
        except AttributeError:
            self._create_song_person_mappings()
            return self.__events_attended_by_player

    def get_song_by_song_id(self, song_id):
        return self.db_handler.get_row("Song", song_id)
    
    def get_person_inst_by_person_inst_id(self, person_inst_id):
        return self.db_handler.get_row("PersonInstrument", person_inst_id)
    
    def get_person_by_person_inst_id(self, person_inst_id):
        return self.get_person_by_person_id(
            self.get_person_inst_by_person_inst_id(person_inst_id)["person_id"]
        )

    def get_inst_by_person_inst_id(self, person_inst_id):
        return self.get_insts_by_inst_id(
            self.get_person_inst_by_person_inst_id(person_inst_id)["instrument_id"]
        )

    def get_insts_by_inst_id(self, inst_id):
        return self.db_handler.get_row("Instrument", inst_id)
    
    def get_insts_by_person_id(self, person_id):
        inst_ids = list(
            self.db_handler.query(
                f"""SELECT instrument_id FROM PersonInstrument
                WHERE person_id == '{person_id}'"""
            )["instrument_id"].drop_duplicates().sort_values()
        )
        return [self.get_insts_by_inst_id(inst_id) for inst_id in inst_ids]
    
    def get_people_by_instrument_id(self, instrument_id):
        people_ids = list(
            self.db_handler.query(
                f"""SELECT person_id FROM PersonInstrument
                WHERE instrument_id == '{instrument_id}'"""
            )["person_id"].drop_duplicates().sort_values()
        )
        return [self.get_person_by_person_id(person_id) for person_id in person_ids]

    def get_song_perf_by_song_perf_id(self, song_perf_id):
        result = {"id": song_perf_id}
        for k, v in self._song_perform_df.loc[song_perf_id].items():
            if not k.startswith("other_player"):
                result[k] = v
        
        return result

    def get_person_insts_by_song_perf_id(self, song_perf_id):
        return [
            v for k, v in self.get_song_perf_by_song_perf_id(song_perf_id).items()
            if k.startswith("other_player_") and v is not None
        ]
    
    def get_songs_perf_by_person_id(self, person_id):
        results = []
        for song_perf_id in self._songs_perf_by_player[person_id]:
            result = self.get_song_perf_by_song_perf_id(song_perf_id)
            result["player_id"] = person_id
            idx = result["players"].index(person_id)
            result["their_instrument_id"] = result["instruments"][idx]
            results.append(result)
        return results
    
    def get_event_occ_by_event_occ_id(self, event_occ_id):
        return self.db_handler.get_row("EventOcc", event_occ_id)
    
    def get_event_occs_attended_by_person_id(self, person_id):
        return [
            self.get_event_occ_by_event_occ_id(event_occ_id)
            for event_occ_id in self._events_attended_by_player[person_id]
        ]
    
    def get_players_by_song_perf_id(self, song_perf_id):
        return self._players_on_song_perf[song_perf_id]
    
    def _get_players_by_song_perf_id(self, song_perf_id):
        return [
            self.get_person_by_person_inst_id(pi)
            for pi in self.get_person_insts_by_song_perf_id(song_perf_id)
        ]

    def get_players_at_event_occ(self, event_occ_id):
        return [
            self.get_person_by_person_id(person_id)
            for person_id in self._players_at_event_perf[event_occ_id]
        ]
    
    def get_person_by_person_id(self, person_id):
        return self.db_handler.get_row("Person", person_id)

    def did_i_play_on_song_perf(self, song_perf_id):
        return self.get_song_perf_by_song_perf_id(song_perf_id) is not None
    
    def get_songs_person_played_with_me(self, person_id):
        songs_they_played = self.get_songs_perf_by_person_id(person_id)
        return [
            song_perf for song_perf in songs_they_played
            if self.did_i_play_on_song_perf(song_perf["id"])
        ]

    def did_i_attend_event_occ(self, event_occ_id):
        return len(
            self._song_perform_df.query(f'event_occ_id == "{event_occ_id}"')
            ["instrument_id"].dropna()
        ) > 0

    def get_event_occ_i_seen_person_at(self, person_id):
        events_they_attended = self.get_event_occs_attended_by_person_id(person_id)
        return [
            event_occ for event_occ in events_they_attended
            if self.did_i_attend_event_occ(event_occ["id"])
        ]

    def get_simplified_event_occ_df(self):
        df = self.db_handler.query("SELECT * FROM EventOccView")
        df.index = list(df["event_occ_id"])
        return df
    
    def get_simplified_persons_df(self):
        try:
            return self.__simplified_persons_df
        except AttributeError:
            contacts_dict = (
                self.db_handler.query("SELECT * FROM Contact")
                .set_index("id")        # to pop off the contact id before indexing with person
                .set_index("person_id")
                .apply(lambda x: [x.to_dict()], axis=1)
                .groupby("person_id").sum().to_dict()
            )

            output = (
                self.db_handler.query("SELECT * FROM Person")
                .rename(columns={"id": "person_id"})
            )
            output["contacts"] =  output["person_id"].apply(lambda x: contacts_dict.get(x, []))
            output.index = list(output["person_id"])
            self.__simplified_persons_df = output
            
            return self.__simplified_persons_df

    def get_simplified_subgenre_df(self):
        df = self.db_handler.query("SELECT * FROM SubgenreView")
        df.index = list(df["subgenre_id"])
        return df

    def get_simplified_key_df(self):
        df = self.db_handler.query("SELECT * FROM KeyView")
        df.index = list(df["key_id"])
        return df

    def get_simplified_songs_df(self):
        try:
            return self.__simplified_songs_df
        except AttributeError:
            ref_recs_dict = (
                self.db_handler.query("SELECT * FROM RefRecs").set_index("song_id")
                .apply(lambda row: [{"source": row["source"], "link": row["link"]}], axis=1)
                .groupby("song_id").sum().to_dict()
            )
            charts_dict = (
                self.db_handler.query("SELECT * FROM Charts").set_index("song_id")
                .apply(lambda row: [{"source": row["source"], "link": row["link"]}], axis=1)
                .groupby("song_id").sum().to_dict()
            )

            output = self.db_handler.query("SELECT * FROM SongView")

            output["reference_recordings"] =  output["song_id"].apply(lambda x: ref_recs_dict.get(x, []))
            output["charts"] =  output["song_id"].apply(lambda x: charts_dict.get(x, []))

            output.index = list(output["song_id"])
            self.__simplified_songs_df = output            
            return self.__simplified_songs_df

    def get_simplified_instruments_df(self):
        df = self.db_handler.query("SELECT id as instrument_id, instrument FROM Instrument")
        df.index = list(df["instrument_id"])
        return df

    def get_simplified_person_instrument_df(self):
        df = (
            self.db_handler.query("SELECT * FROM PersonInstrumentView")
            .rename(columns={"id", "person_instrument_id"})
        )
        df.index = list(df["person_instrument_id"])
        return df

    def summarize_person(self, person_id):

        ## Instead, get list of hyperlinks to their photos,
        # try:
        #     img = Image.open(f"data/paul_k_db/people/{person_id}.png")
        #     new_size = (400, 400) 
        #     img = img.resize(new_size)        
        #     display(img)
        # except FileNotFoundError:
        #     pass
        
        person_info = self.get_person_by_person_id(person_id)
        their_insts = [
            row["instrument"] for row in self.get_insts_by_person_id(person_id)
        ]
        events_ive_seen_them_at = (
            self.get_simplified_event_occ_df().merge(
                pd.DataFrame(self.get_event_occ_i_seen_person_at(person_id))[["id"]],
                left_on="event_occ_id",
                right_on="id"
            )
        ).drop(columns=["id"])

        songs_they_played_with_me = (
            pd.DataFrame(self.get_songs_person_played_with_me(person_id))[[
                "id", "event_occ_id", "song_id", "instrument_id",
                "video", "player_id", "their_instrument_id"
            ]]
            .rename(columns={"id": "performance_id", "instrument_id": "my_instrument_id"})        
        ).merge(
            self.get_simplified_songs_df()[["song_id", "song"]],
            on="song_id"
        ).merge(
            self.get_simplified_instruments_df().rename(
                columns={"instrument": "my_instrument", "instrument_id": "my_instrument_id"}
            ),
            on="my_instrument_id"
        ).merge(
            self.get_simplified_instruments_df().rename(
                columns={"instrument": "their_instrument", "instrument_id": "their_instrument_id"}
            ),
            on="their_instrument_id"
        ).merge(
            self.get_simplified_event_occ_df(),
            on="event_occ_id"
        ).sort_values("event_occ_date")[
        ["song", "my_instrument", "their_instrument", "event_occ", "venue_name", "event_occ_date", "video"]
        ]

        return {
            "person_info": person_info,
            "their_instruments": their_insts,
            "songs_played_with_me": songs_they_played_with_me,
            "events_ive_seen_them_at": events_ive_seen_them_at
        }
        
    def summarize_performed_song(self, song_perf_id):
        # Song level info, like key
        # Who were all the players and their instruments
        # Video if available        
        performed_song = self.get_song_perf_by_song_perf_id(song_perf_id)
        event_occ_id = performed_song.pop("event_occ_id")
        song_id = performed_song.pop("song_id")
        event_occ = self.get_simplified_event_occ_df().loc[event_occ_id].to_dict()
        song = self.get_simplified_songs_df().loc[song_id].to_dict()
        song["genre"] = f'{song.pop("genre")}: {song.pop("subgenre")}'.strip()
        if song["genre"] == ":":
            song["genre"] = ""

        player_ids = performed_song.pop("players")
        _people = (
            self.get_simplified_persons_df().loc[player_ids]
            .to_dict(orient="records")
        )
        _insts = (
            self.get_simplified_instruments_df()
            .loc[performed_song.pop("instruments")].to_dict(orient="records")
        )
        
        people_who_played = []
        # Even though single song, we still allow person to have mult instruments
        # e.g., play guitar and sing.
        for person, inst, player_id in zip(_people, _insts, player_ids):
            person["instruments"] = [inst["instrument"]]
            people_who_played.append(person)
            # TODO : use player ids to lookup people images
        people_who_played = pd.DataFrame(people_who_played)
        aggs = {
            col: "first"
            for col in people_who_played.columns
            if col not in {"full_name", "instruments"}
        }
        aggs["instruments"] = "sum"
        people_who_played = (
            people_who_played.groupby("full_name").agg(aggs).reset_index()
            [["full_name", "public_name", "instruments"]]
            .to_dict(orient="records")
        )

        key_id = (performed_song["key_id"] or "").strip()
        if key_id != "":
            key = self.get_simplified_key_df().loc[key_id].to_dict()["key"]
        else:
            key = song["key"]


        def proc_youtube_link(video):
            if video is None or video.strip() == "":
                return {}
            video = video.strip()
            embeddable = video
            links = {
                "link": video,
            }
            if "/embed/" in embeddable:
                links["embeddable"] = embeddable
                return links
            embed_pref = "https://youtube.com/embed/"
            for prefix in ["https://youtu.be/", "https://youtube.com/"]:
                if embeddable.startswith(prefix):
                    links["embeddable"] = embeddable.replace(prefix, embed_pref)
                    return links

        return {
            "event_occ": event_occ,
            "song": song,
            "people_who_played": people_who_played,
            "video": proc_youtube_link(performed_song.get("video", "")),
            "key_performed": key            
        }

    def summarize_event_occ(self, event_occ_id):
        # when, what, where
        # Who was there
        # What songs were played
        event = self.get_simplified_event_occ_df().loc[event_occ_id].to_dict()

        songs_played = (
            self._song_perform_df.query(f'event_occ_id == "{event_occ_id}"')
            [["song_id", "instrument_id", "video", "players", "instruments"]]
        )
        songs_played["player_public_names"] = songs_played["players"].apply(
            lambda row: list(self.get_simplified_persons_df().loc[row]["public_name"])
        )

        insts = self.get_simplified_instruments_df()["instrument"]
        songs_played["instruments"] = songs_played["instruments"].apply(
            lambda row: list(insts.loc[row])
        )
        songs_played = songs_played.merge(
            self.get_simplified_songs_df()[["song_id", "song"]],
            on="song_id"
        )
        songs_played = songs_played[["song", "player_public_names", "instruments", "video"]]

        players_at_event = (
            pd.DataFrame(self.get_players_at_event_occ(event_occ_id))[["id", "full_name"]]
        )

        return {
            "event": event,
            "songs_played": songs_played,
            "players_at_event": players_at_event
        }
        # people_who_played = (
        #     jamming_db.entities["PersonInstrument"].data.loc[list(set(songs_played["players"].sum()))]
        #     [["person_id", "instrument_id"]].merge(
        #        simplified_persons,
        #        left_on="person_id", right_index=True
        #     ).merge(
        #         simplified_instruments,
        #         left_on="instrument_id", right_index=True
        #     )
        # )[["person_id", "full_name", "instrument"]].drop_duplicates()
        # people_who_played["instrument"] = people_who_played["instrument"].apply(lambda x: [x])
        # people_who_played = people_who_played.groupby("person_id").agg({"full_name": "first", "instrument": "sum"})
        # songs_played.drop(["players"], axis=1, inplace=True)
        
        # print(event)
        # print("\n\nSongs played at the event.")
        # print(songs_played)
        # print("\n\nPeopled who played at the event.")
    
        # for person_id, row in people_who_played.iterrows():
        #     person = row["full_name"]
        #     insts = row["instrument"]
        #     print(f"Name: {person}\nInstruments: {insts}")
        #     try:
        #         img = Image.open(f"data/paul_k_db/people/{person_id}.png")
        #         new_size = (100, 100) 
        #         img = img.resize(new_size)        
        #         display(img)
        #     except FileNotFoundError:
        #         pass
        #     print("\n")


    def overview_event_occs(self):
        def songs_dicts(songs):
            return (
                self.get_simplified_songs_df().set_index("song_id")
                .loc[songs]["song"].reset_index().to_dict(orient="records")
            )
        
        def players_dicts(players):
            return (
                self.get_simplified_persons_df().loc[players][["public_name", "full_name"]]
                .reset_index().to_dict(orient="records")
            )
        
        songs_at_event = self._song_perform_df[["event_occ_id", "song_id", "players"]].copy()
        songs_at_event["song_id"] = songs_at_event["song_id"].apply(lambda x: [x]) 
        songs_at_event = songs_at_event.groupby("event_occ_id").sum()
        songs_at_event["players"] = songs_at_event["players"].apply(lambda x: sorted(list(set(x))))
        songs_at_event = songs_at_event.reset_index().rename(columns={"song_id": "songs"})
        
        songs_at_event["songs"] = songs_at_event["songs"].apply(songs_dicts)
        songs_at_event["players"] = songs_at_event["players"].apply(players_dicts)

        simp_event_occ = (
            self.get_simplified_event_occ_df().merge(
                songs_at_event,
                on="event_occ_id",
                how="left"
            )
        )
        fill_na_to_list(simp_event_occ, "players")
        fill_na_to_list(simp_event_occ, "songs")

        simp_event_occ["event"] = simp_event_occ.apply(
            lambda x: {"id": x["event_occ_id"], "event_name": x["event_occ"]},
            axis=1
        )
        
        simp_event_occ["venue"] = simp_event_occ.apply(
            lambda x: {"id": x["venue_id"], "venue_name": x["venue_name"]},
            axis=1
        )

        return simp_event_occ.sort_values("event_occ_date")
        

