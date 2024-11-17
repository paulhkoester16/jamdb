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
    # Add fields and resolvers to a Query object.
    #
    # Each item (e.g., ChartGQL) in gql_classes requires adding two fields and two resolvers;
    #         charts = graphene.List(ChartGQL)
    #         chart = graphene.Field(ChartGQL, id=graphene.ID())
    #         def resolve_charts(root, info):
    #             return ChartGQL.get_query(info).all()
    #         def resolve_chart(root, info, id):
    #             return ChartGQL.get_node(info, id)
    # There are > 20 such items, so we use to meta-programming in `add_table_obj_to_query`

    class Query(graphene.ObjectType):
        pass
    
    def _factory_resolver_get_all_from_table(cls):
        def inner_func(root, info):
            return cls.get_query(info).all()
        return inner_func

    def _factory_resolver_get_one_from_table(cls):
        def inner_func(root, info, id):
            return cls.get_node(info, id)
        return inner_func

    def add_table_obj_to_query(table_name, table_cls, query_cls):
        sing = table_name
        plural = f"{sing}s"
        
        # For fields, can't simply `setattr` on the query cls, since the query and schema has to
        # resolve across many objects, thus the fields must be added to the query's _meta.
        
        query_cls._meta.fields[sing] = graphene.Field(cls, id=graphene.ID())
        query_cls._meta.fields[plural] = graphene.Field(graphene.List(cls))

        # add resolvers
        setattr(query_cls, f"resolve_{sing}", _factory_resolver_get_one_from_table(cls))
        setattr(query_cls, f"resolve_{plural}", _factory_resolver_get_all_from_table(cls))


    for name, cls in gql_classes.items():
        if issubclass(cls, SQLAlchemyObjectType):
            add_table_obj_to_query(name, cls, Query)

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
