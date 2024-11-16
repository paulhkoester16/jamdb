import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType

from .globals import DB_FILE
from .transformations import format_id_as_str, create_embed_link


def _automap_sqlalchemy_models(sqlalchemy_engine):
    # step 1
    AutomappedBase = automap_base()
    AutomappedBase.prepare(autoload_with=sqlalchemy_engine)
    
    model_classes = dict(AutomappedBase.classes)

    # TODO -- fix these names in the underlying DB
    if "Charts" in model_classes:
        model_classes["Chart"] = model_classes.pop("Charts")
    if "SubGenre" in model_classes:
        model_classes["Subgenre"] = model_classes.pop("SubGenre")
    if "RefRecs" in model_classes:
        model_classes["RefRec"] = model_classes.pop("RefRecs")
    if "SetlistSongs" in model_classes:
        model_classes["SetlistSong"] = model_classes.pop("SetlistSongs")

    return model_classes
        
def _create_qraphene_objects(model_classes):
    # step 2
    # TODO -- this could benefit from some "meta-programming"
    #      For each key, value we create class
    #
    # ```
    # @register_gql("{snake_case(key)}"):
    # class {key}GQL(SQLAlchemyObjectType):
    #     class Meta:
    #         model = {value}
    # ```
    #
    # Further, if `{item}_collection` is in `{key}`'s table/metadata then we add attr
    # ```
    #     {snake_case(item)}s = graphen.List(lambda: CamelCase(item)GQL)
    # ```
    # and resolver 
    # ```
    #     def resolve_{snake_case(item)}s(root, info):
    #         return root.{item}_collection
    # ```
    # 
    # If we can create a derived class of SQLAlchemyObjectType or some meta class or factory
    # then we should be able to get rid of LOTs of boiler plate and only need direct code in 
    # a few places like `def resolve_google_map_string(root, info)` in `Venue`
    
    _REGISTRY = {}

    def register_gql(name):
        def __inner_factory_function(cls):
            _REGISTRY[name] = cls
            return cls
        return __inner_factory_function


    def _personinstruments_to_instruments(personinstruments):
        insts = {
            pers_inst.instrument.id: pers_inst.instrument
            for pers_inst in personinstruments
        }
        insts = sorted(list(insts.values()), key=lambda inst: inst.id)
        return insts


    class PlayerGQL(graphene.ObjectType): 
        person = graphene.Field(lambda: PersonGQL)
        instruments = graphene.List(lambda: InstrumentGQL)
        instrument_list = graphene.List(graphene.String)

        def resolve_instrument_list(root, info):
            return [inst.instrument for inst in root.instruments]


    @register_gql("chart")
    class ChartGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Chart"]

        embeddable_link = graphene.String()
        
        def resolve_embeddable_link(root, info):
            return create_embed_link(root.source, root.link)

    
    @register_gql("composer") 
    class ComposerGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Composer"]
    
        songs = graphene.List(lambda: SongGQL)
        
        def resolve_songs(root, info):
            return root.song_collection

    
    @register_gql("contact")
    class ContactGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Contact"]
    

    @register_gql("event_gen")
    class EventGenGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["EventGen"]
    
        event_occs = graphene.List(lambda: EventOccGQL)
    
        def resolve_event_occs(root, info):
            return root.eventocc_collection

    
    @register_gql("event_occ")
    class EventOccGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["EventOcc"]
    
        song_performs = graphene.List(lambda: SongPerformGQL)
        venue = graphene.Field(lambda: VenueGQL)
        players = graphene.List(lambda: PlayerGQL)
        
        def resolve_song_performs(root, info):
            return root.songperform_collection

        def resolve_venue(root, info):
            return root.eventgen.venue

        def resolve_players(root, info):
            # TODO:  refactor using `_personinstruments_to_instruments`
            
            players_dict = {}
            for song in root.songperform_collection:        
                for perf in song.songperformer_collection:
                    pers_ins = perf.personinstrument
                    person_id = pers_ins.person.id
                    if person_id not in players_dict:
                        players_dict[person_id] = {
                            "person": pers_ins.person,
                            "instruments": {}
                        }
                    inst = pers_ins.instrument
                    players_dict[person_id]["instruments"][inst.id] = inst
            for player in players_dict.values():
                player["instruments"] = sorted(
                    list(player["instruments"].values()),
                    key=lambda inst: inst.id
                )
            players = [PlayerGQL(**player) for player in players_dict.values()]
            return players

    
    @register_gql("genre")
    class GenreGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Genre"]
    
        event_gens = graphene.List(lambda: EventGenGQL)
        subgenres = graphene.List(lambda: SubgenreGQL)
    
        def resolve_event_gens(root, info):
            return root.eventgen_collection
    
        def resolve_subgenres(root, info):
            return root.subgenre_collection
    

    @register_gql("instrument")
    class InstrumentGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Instrument"]
    
        person_instruments = graphene.List(lambda: PersonInstrumentGQL)
        setlist_songs = graphene.List(lambda: SetlistSongGQL)
    
        def resolve_person_instruments(root, info):
            return root.personinstrument_collection
    
        def resolve_setlist_songs(root, info):
            return root.setlistsongs_collection
    

    @register_gql("key")
    class KeyGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Key"]
    
        key_name = graphene.String()
    
        def resolve_key_name(root, info):
            return f"{root.root} {root.mode.mode}"
    
        setlist_songs = graphene.List(lambda: SetlistSongGQL)
        songs = graphene.List(lambda: SongGQL)
        song_learns = graphene.List(lambda: SongLearnGQL)
        song_performs = graphene.List(lambda: SongPerformGQL)
    
        def resolve_setlist_songs(root, info):
            return root.setlistsongs_collection
    
        def resolve_songs(root, info):
            return root.song_collection
    
        def resolve_song_learns(root, info):
            return root.songlearn_collection
    
        def resolve_song_performs(root, info):
            return root.songperform_collection
    

    @register_gql("mode")
    class ModeGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Mode"]
    
        keys = graphene.List(lambda: KeyGQL)
    
        def resolve_keys(root, info):
            return root.key_collection


    @register_gql("performance_video")
    class PerformanceVideoGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["PerformanceVideo"]

        embeddable_link = graphene.String()

        def resolve_embeddable_link(root, info):
            return create_embed_link(root.source, root.link)

    @register_gql("person")
    class PersonGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Person"]
    
        contacts = graphene.List(lambda: ContactGQL)
        event_gens = graphene.List(lambda: EventGenGQL)
        person_instruments = graphene.List(lambda: PersonInstrumentGQL)
        instruments = graphene.List(lambda: InstrumentGQL)
        instrument_list = graphene.List(graphene.String)
        combined_name = graphene.String()

        events_attended = graphene.List(lambda: EventOccGQL)        
        song_performs = graphene.List(lambda: SongPerformGQL)
        songs_performed_with = graphene.Field(
            graphene.List(lambda: SongPerformGQL),
            other_person_id=graphene.ID()
        )
        songs_performed_without = graphene.Field(
            graphene.List(lambda: SongPerformGQL),
            other_person_id=graphene.ID()
        )

        def resolve_contacts(root, info):
            return root.contact_collection
    
        def resolve_event_gens(root, info):
            return root.eventgen_collection
    
        def resolve_person_instruments(root, info):
            return root.personinstrument_collection

        def resolve_combined_name(root, info):
            result = root.public_name
            if root.full_name != root.public_name:
                result += f" ({root.full_name})"
            return result

        def resolve_instruments(root, info):
            insts = _personinstruments_to_instruments(root.personinstrument_collection)            
            return insts

        def resolve_instrument_list(root, info):
            insts = _personinstruments_to_instruments(root.personinstrument_collection)
            return [inst.instrument for inst in insts]

        def resolve_song_performs(root, info):
            perfs = {}
            for persinst in root.personinstrument_collection:
                for perf in persinst.songperformer_collection:
                    songperf = perf.songperform
                    perfs[songperf.id] = songperf
            return sorted(list(perfs.values()), key=lambda x: (x.eventocc.date, x.song_id))

        def resolve_events_attended(root, info):
            events = {}
            for persinst in root.personinstrument_collection:
                for perf in persinst.songperformer_collection:
                    event = perf.songperform.eventocc
                    events[event.id] = event
            return sorted(list(events.values()), key=lambda x: x.date)

        def resolve_songs_performed_with(root, info, other_person_id):
            # TODO - refactor commonalities out of `resolve_songs_performed_with`
            #        and `resolve_songs_performed_without`
            all_performed_songs = PersonGQL.resolve_song_performs(root, info)
            with_other = []
            for song in all_performed_songs:
                song_players = [
                    performer.personinstrument.person.id
                    for performer in song.songperformer_collection
                ]
                if other_person_id in song_players:
                    with_other.append(song)
            return with_other

        def resolve_songs_performed_without(root, info, other_person_id):
            all_performed_songs = PersonGQL.resolve_song_performs(root, info)
            without_other = []
            for song in all_performed_songs:
                song_players = [
                    performer.personinstrument.person.id
                    for performer in song.songperformer_collection
                ]
                if other_person_id not in song_players:
                    without_other.append(song)
            return without_other

    @register_gql("person_instrument")
    class PersonInstrumentGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["PersonInstrument"]
    
        song_performers = graphene.List(lambda: SongPerformerGQL)
        song_performs = graphene.List(lambda: SongPerformGQL)
        events_attended = graphene.List(lambda: EventOccGQL)
        
        def resolve_song_performers(root, info):
            return root.songperformer_collection

        def resolve_song_performs(root, info):
            return [x.songperform for x in root.songperformer_collection]

        def resolve_events_attended(root, info):
            events = {}
            for perf in root.songperformer_collection:
                event = perf.songperform.eventocc
                events[event.id] = event
            return sorted(list(events.values()), key=lambda x: x.date)

    
    @register_gql("ref_ref")
    class RefRecGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["RefRec"]

        embeddable_link = graphene.String()

        def resolve_embeddable_link(root, info):
            return create_embed_link(root.source, root.link)
    

    @register_gql("setlist")
    class SetlistGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Setlist"]
    
        setlist_songs = graphene.List(lambda: SetlistSongGQL)
    
        def resolve_setlist_songs(root, info):
            return root.setlistsongs_collection


    @register_gql("setlist_song")
    class SetlistSongGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["SetlistSong"]
    

    @register_gql("song")
    class SongGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Song"]
    
        charts = graphene.List(lambda: ChartGQL)
        ref_recs = graphene.List(lambda: RefRecGQL)
        setlist_songs = graphene.List(lambda: SetlistSongGQL)
        song_learns = graphene.List(lambda: SongLearnGQL)
        song_performs = graphene.List(lambda: SongPerformGQL)
    
        def resolve_charts(root, info):
            return root.charts_collection
    
        def resolve_ref_recs(root, info):
            return root.refrecs_collection
    
        def resolve_setlist_songs(root, info):
            return root.setlistsongs_collection
        
        def resolve_song_learns(root, info):
            return root.songlearns_collection
    
        def resolve_song_performs(root, info):
            return root.songperform_collection


    @register_gql("song_learn")
    class SongLearnGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["SongLearn"]


    @register_gql("song_perform")
    class SongPerformGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["SongPerform"]
    
        performance_videos = graphene.List(lambda: PerformanceVideoGQL)
        song_performers = graphene.List(lambda: SongPerformerGQL)
        song_perform_name = graphene.String()
        players = graphene.List(lambda: PlayerGQL)
        
        def resolve_performance_videos(root, info):
            return root.performancevideo_collection
    
        def resolve_song_performers(root, info):
            return root.songperformer_collection

        def resolve_song_perform_name(root, info):
            return f"{root.song.song} ({root.eventocc.name})"

        def resolve_players(root, info):
            # TODO:  refactor using `_personinstruments_to_instruments`            
            players_dict = {}
            for perf in root.songperformer_collection:
                pers_ins = perf.personinstrument
                person_id = pers_ins.person.id
                if person_id not in players_dict:
                    players_dict[person_id] = {
                        "person": pers_ins.person,
                        "instruments": {}
                    }
                inst = pers_ins.instrument
                players_dict[person_id]["instruments"][inst.id] = inst
            for player in players_dict.values():
                player["instruments"] = sorted(
                    list(player["instruments"].values()),
                    key=lambda inst: inst.id
                )
            players = [PlayerGQL(**player) for player in players_dict.values()]
            return players
                


    @register_gql("song_performer")
    class SongPerformerGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["SongPerformer"]


    @register_gql("subgenre")
    class SubgenreGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Subgenre"]
    
        subgenre_name = graphene.String()
        songs = graphene.List(lambda: SongGQL)
    
        def resolve_subgenre_name(root, info):
            genre = root.genre.genre
            sub = root.subgenre
            output = genre
            if genre != sub:
                output += ": " + sub
            return output
    
        def resolve_songs(root, info):
            return root.song_collection    
    

    @register_gql("venue")
    class VenueGQL(SQLAlchemyObjectType):
    
        class Meta:
            model = model_classes["Venue"]
    
        zip = graphene.Int()
        address_string = graphene.String()
        google_map_string = graphene.String()
        hosted_event_series = graphene.List(lambda: EventGenGQL)
    
        def resolve_zip(root, info):
            return format_id_as_str(root.zip)
        
        def resolve_address_string(root, info):
            return f"{root.address}, {root.city}, {root.state}, {VenueGQL.resolve_zip(root, info)}"
    
        def resolve_google_map_string(root, info):
            address_string = VenueGQL.resolve_address_string(root, info)
            return f"https://www.google.com/maps/place/{address_string}".replace(" ", "+")
        
        def resolve_hosted_event_series(root, info):
            return root.eventgen_collection

    return _REGISTRY


def _query_factory(gql_classes):
    # step 3

    ChartGQL = gql_classes["chart"]
    ComposerGQL = gql_classes["composer"]
    ContactGQL = gql_classes["contact"]
    EventGenGQL = gql_classes["event_gen"]
    EventOccGQL = gql_classes["event_occ"]
    GenreGQL = gql_classes["genre"]
    InstrumentGQL = gql_classes["instrument"]
    KeyGQL = gql_classes["key"]
    ModeGQL = gql_classes["mode"]
    PerformanceVideoGQL = gql_classes["performance_video"]
    PersonGQL = gql_classes["person"]
    PersonInstrumentGQL = gql_classes["person_instrument"]
    RefRecGQL = gql_classes["ref_ref"]
    SetlistGQL = gql_classes["setlist"]
    SetlistSongGQL = gql_classes["setlist_song"]
    SongGQL = gql_classes["song"]
    SongLearnGQL = gql_classes["song_learn"]
    SongPerformGQL = gql_classes["song_perform"]
    SongPerformerGQL = gql_classes["song_performer"]
    SubgenreGQL = gql_classes["subgenre"]
    VenueGQL = gql_classes["venue"]
    
    class Query(graphene.ObjectType):
        # There has got to be a way to meta-program this thing.
        # I just wanna have a function that takes a dict of 
        # {"chart": ChartGQL, "composer": ComposergQL, } etc and for each key-value
        # it creates the var declaration and resolver for both singular and plural version
    
        charts = graphene.List(ChartGQL)
        chart = graphene.Field(ChartGQL, id=graphene.ID())
    
        composers = graphene.List(ComposerGQL)
        composer = graphene.Field(ComposerGQL, id=graphene.ID())
    
        contacts = graphene.List(ContactGQL)
        contact = graphene.Field(ContactGQL, id=graphene.ID())
    
        event_gens = graphene.List(EventGenGQL)
        event_gen = graphene.Field(EventGenGQL, id=graphene.ID())
    
        event_occs = graphene.List(EventOccGQL)
        event_occ = graphene.Field(EventOccGQL, id=graphene.ID())
    
        genres = graphene.List(GenreGQL)
        genre = graphene.Field(GenreGQL, id=graphene.ID())
    
        instruments = graphene.List(InstrumentGQL)
        instrument = graphene.Field(InstrumentGQL, id=graphene.ID())
    
        keys = graphene.List(KeyGQL)
        key = graphene.Field(KeyGQL, id=graphene.ID())
    
        modes = graphene.List(ModeGQL)
        mode = graphene.Field(ModeGQL, id=graphene.ID())
    
        performance_videos = graphene.List(PerformanceVideoGQL)
        performance_video = graphene.Field(PerformanceVideoGQL, id=graphene.ID())
    
        person_instruments = graphene.List(PersonInstrumentGQL)
        person_instrument = graphene.Field(PersonInstrumentGQL, id=graphene.ID())
    
        ref_recs = graphene.List(RefRecGQL)
        ref_rec = graphene.Field(RefRecGQL, id=graphene.ID())
    
        setlists = graphene.List(SetlistGQL)
        setlist = graphene.Field(SetlistGQL, id=graphene.ID())
    
        setlist_songs = graphene.List(SetlistSongGQL)
        setlist_song = graphene.Field(SetlistSongGQL, id=graphene.ID())
    
        songs = graphene.List(SongGQL)
        song = graphene.Field(SongGQL, id=graphene.ID())
    
        song_learns = graphene.List(SongLearnGQL)
        song_learn = graphene.Field(SongLearnGQL, id=graphene.ID())
    
        song_performs = graphene.List(SongPerformGQL)
        song_perform = graphene.Field(SongPerformGQL, id=graphene.ID())
    
        song_performers = graphene.List(SongPerformerGQL)
        song_performer = graphene.Field(SongPerformerGQL, id=graphene.ID())
    
        subgenres = graphene.List(SubgenreGQL)
        subgenre = graphene.Field(SubgenreGQL, id=graphene.ID())
        
        persons = graphene.List(PersonGQL)
        person = graphene.Field(PersonGQL, id=graphene.ID())
    
        venues = graphene.List(VenueGQL)
        venue = graphene.Field(VenueGQL, id=graphene.ID())
    
        def resolve_charts(root, info):
            return ChartGQL.get_query(info).all()
    
        def resolve_chart(root, info, id):
            return ChartGQL.get_node(info, id)
    
        def resolve_composers(root, info):
            return ComposerGQL.get_query(info).all()
    
        def resolve_composer(root, info, id):
            return ComposerGQL.get_node(info, id)
    
        def resolve_contacts(root, info):
            return ContactGQL.get_query(info).all()
    
        def resolve_contact(root, info, id):
            return ContactGQL.get_node(info, id)
    
        def resolve_event_gens(root, info):
            return EventGenGQL.get_query(info).all()
    
        def resolve_event_gen(root, info, id):
            return EventGenGQL.get_node(info, id)
    
        def resolve_event_occs(root, info):
            return EventOccGQL.get_query(info).all()
    
        def resolve_event_occ(root, info, id):
            return EventOccGQL.get_node(info, id)
    
        def resolve_genres(root, info):
            return GenreGQL.get_query(info).all()
    
        def resolve_genre(root, info, id):
            return GenreGQL.get_node(info, id)
    
        def resolve_instruments(root, info):
            return InstrumentGQL.get_query(info).all()
    
        def resolve_instrument(root, info, id):
            return InstrumentGQL.get_node(info, id)
    
        def resolve_keys(root, info):
            return KeyGQL.get_query(info).all()
    
        def resolve_key(root, info, id):
            return KeyGQL.get_node(info, id)
    
        def resolve_modes(root, info):
            return ModeGQL.get_query(info).all()
    
        def resolve_mode(root, info, id):
            return ModeGQL.get_node(info, id)
    
        def resolve_performance_videos(root, info):
            return PerformanceVideoGQL.get_query(info).all()
    
        def resolve_performance_video(root, info, id):
            return PerformanceVideoGQL.get_node(info, id)
    
        def resolve_person_instruments(root, info):
            return PersonInstrumentGQL.get_query(info).all()
    
        def resolve_person_instrument(root, info, id):
            return PersonInstrumentGQL.get_node(info, id)
    
        def resolve_ref_recs(root, info):
            return RefRecGQL.get_query(info).all()
    
        def resolve_ref_rec(root, info, id):
            return RefRecGQL.get_node(info, id)
    
        def resolve_setlists(root, info):
            return SetlistGQL.get_query(info).all()
    
        def resolve_setlist(root, info, id):
            return SetlistGQL.get_node(info, id)
    
        def resolve_setlist_songs(root, info):
            return SetlistSongGQL.get_query(info).all()
    
        def resolve_setlist_song(root, info, id):
            return SetlistSongGQL.get_node(info, id)
    
        def resolve_songs(root, info):
            return SongGQL.get_query(info).all()
    
        def resolve_song(root, info, id):
            return SongGQL.get_node(info, id)
    
        def resolve_song_learns(root, info):
            return SongLearnGQL.get_query(info).all()
    
        def resolve_song_learn(root, info, id):
            return SongLearnGQL.get_node(info, id)
    
        def resolve_song_performs(root, info):
            return SongPerformGQL.get_query(info).all()
    
        def resolve_song_perform(root, info, id):
            return SongPerformGQL.get_node(info, id)
    
        def resolve_song_performers(root, info):
            return SongPerformerGQL.get_query(info).all()
    
        def resolve_song_performer(root, info, id):
            return SongPerformerGQL.get_node(info, id)
    
        def resolve_subgenres(root, info):
            return SubgenreGQL.get_query(info).all()
    
        def resolve_subgenre(root, info, id):
            return SubgenreGQL.get_node(info, id)
        
        def resolve_persons(root, info):
            return PersonGQL.get_query(info).all()
    
        def resolve_person(root, info, id):
            return PersonGQL.get_node(info, id)
    
        def resolve_venues(root, info):
            return VenueGQL.get_query(info).all()
    
        def resolve_venue(root, info, id):
            return VenueGQL.get_node(info, id)

    return Query


def get_graphene_schema(sqlalchemy_engine):
    sqlalchemy_models = _automap_sqlalchemy_models(sqlalchemy_engine)
    graphene_objects = _create_qraphene_objects(sqlalchemy_models)
    graphene_query_cls = _query_factory(graphene_objects)
    graphene_schema = graphene.Schema(query=graphene_query_cls)
    return graphene_schema


class GrapheneSQLSession:

    def __init__(self, session, schema):
        self.session = session
        self.schema = schema

    @classmethod
    def from_sqlite_file(cls, sqlite_file=DB_FILE):
        engine = sqlalchemy.create_engine(
            f'sqlite:///{sqlite_file}',
            connect_args={'check_same_thread': False}
        )
        schema = get_graphene_schema(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()

        return cls(session=session, schema=schema)

    def execute(self, query, variables=None):
        return self.schema.execute(query, variables=variables, context_value={'session': self.session})



def _query_factory_broken(gql_classes):
    # Trying to do some meta-programming to reduce the boilerplate
    # oh, so much boilerplate....

    ChartGQL = gql_classes["chart"]
    ComposerGQL = gql_classes["composer"]
    ContactGQL = gql_classes["contact"]
    EventGenGQL = gql_classes["event_gen"]
    EventOccGQL = gql_classes["event_occ"]
    GenreGQL = gql_classes["genre"]
    InstrumentGQL = gql_classes["instrument"]
    KeyGQL = gql_classes["key"]
    ModeGQL = gql_classes["mode"]
    PerformanceVideoGQL = gql_classes["performance_video"]
    PersonGQL = gql_classes["person"]
    PersonInstrumentGQL = gql_classes["person_instrument"]
    RefRecGQL = gql_classes["ref_ref"]
    SetlistGQL = gql_classes["setlist"]
    SetlistSongGQL = gql_classes["setlist_song"]
    SongGQL = gql_classes["song"]
    SongLearnGQL = gql_classes["song_learn"]
    SongPerformGQL = gql_classes["song_perform"]
    SongPerformerGQL = gql_classes["song_performer"]
    SubgenreGQL = gql_classes["subgenre"]
    VenueGQL = gql_classes["venue"]

    class Query(graphene.ObjectType):        
        # There has got to be a way to meta-program this thing.
        # I just wanna have a function that takes a dict of 
        # {"chart": ChartGQL, "composer": ComposergQL, } etc and for each key-value
        # it creates the var declaration and resolver for both singular and plural version

        @classmethod
        def thing(cls):
            for cls_name, g_cls in gql_classes.items():
                setattr(g_cls, cls_name, graphene.Field(g_cls, id=graphene.ID()))
                setattr(g_cls, f"{cls_name}s", graphene.List(cls))
            return cls
    
        def resolve_charts(root, info):
            return ChartGQL.get_query(info).all()
    
        def resolve_chart(root, info, id):
            return ChartGQL.get_node(info, id)
    
        def resolve_composers(root, info):
            return ComposerGQL.get_query(info).all()
    
        def resolve_composer(root, info, id):
            return ComposerGQL.get_node(info, id)
    
        def resolve_contacts(root, info):
            return ContactGQL.get_query(info).all()
    
        def resolve_contact(root, info, id):
            return ContactGQL.get_node(info, id)
    
        def resolve_event_gens(root, info):
            return EventGenGQL.get_query(info).all()
    
        def resolve_event_gen(root, info, id):
            return EventGenGQL.get_node(info, id)
    
        def resolve_event_occs(root, info):
            return EventOccGQL.get_query(info).all()
    
        def resolve_event_occ(root, info, id):
            return EventOccGQL.get_node(info, id)
    
        def resolve_genres(root, info):
            return GenreGQL.get_query(info).all()
    
        def resolve_genre(root, info, id):
            return GenreGQL.get_node(info, id)
    
        def resolve_instruments(root, info):
            return InstrumentGQL.get_query(info).all()
    
        def resolve_instrument(root, info, id):
            return InstrumentGQL.get_node(info, id)
    
        def resolve_keys(root, info):
            return KeyGQL.get_query(info).all()
    
        def resolve_key(root, info, id):
            return KeyGQL.get_node(info, id)
    
        def resolve_modes(root, info):
            return ModeGQL.get_query(info).all()
    
        def resolve_mode(root, info, id):
            return ModeGQL.get_node(info, id)
    
        def resolve_performance_videos(root, info):
            return PerformanceVideoGQL.get_query(info).all()
    
        def resolve_performance_video(root, info, id):
            return PerformanceVideoGQL.get_node(info, id)
    
        def resolve_person_instruments(root, info):
            return PersonInstrumentGQL.get_query(info).all()
    
        def resolve_person_instrument(root, info, id):
            return PersonInstrumentGQL.get_node(info, id)
    
        def resolve_ref_recs(root, info):
            return RefRecGQL.get_query(info).all()
    
        def resolve_ref_rec(root, info, id):
            return RefRecGQL.get_node(info, id)
    
        def resolve_setlists(root, info):
            return SetlistGQL.get_query(info).all()
    
        def resolve_setlist(root, info, id):
            return SetlistGQL.get_node(info, id)
    
        def resolve_setlist_songs(root, info):
            return SetlistSongGQL.get_query(info).all()
    
        def resolve_setlist_song(root, info, id):
            return SetlistSongGQL.get_node(info, id)
    
        def resolve_songs(root, info):
            return SongGQL.get_query(info).all()
    
        def resolve_song(root, info, id):
            return SongGQL.get_node(info, id)
    
        def resolve_song_learns(root, info):
            return SongLearnGQL.get_query(info).all()
    
        def resolve_song_learn(root, info, id):
            return SongLearnGQL.get_node(info, id)
    
        def resolve_song_performs(root, info):
            return SongPerformGQL.get_query(info).all()
    
        def resolve_song_perform(root, info, id):
            return SongPerformGQL.get_node(info, id)
    
        def resolve_song_performers(root, info):
            return SongPerformerGQL.get_query(info).all()
    
        def resolve_song_performer(root, info, id):
            return SongPerformerGQL.get_node(info, id)
    
        def resolve_subgenres(root, info):
            return SubgenreGQL.get_query(info).all()
    
        def resolve_subgenre(root, info, id):
            return SubgenreGQL.get_node(info, id)
        
        def resolve_persons(root, info):
            return PersonGQL.get_query(info).all()
    
        def resolve_person(root, info, id):
            return PersonGQL.get_node(info, id)
    
        def resolve_venues(root, info):
            return VenueGQL.get_query(info).all()
    
        def resolve_venue(root, info, id):
            return VenueGQL.get_node(info, id)

    return Query.thing()

