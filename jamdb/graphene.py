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

    return model_classes
        
def _create_qraphene_objects(model_classes):
    # step 2
    
    _REGISTRY = {}

    def register_gql(name):
        def __inner_factory_function(cls):
            _REGISTRY[name] = cls
            return cls
        return __inner_factory_function

    def add_for_collections(field_name, cls_fnc, collection_name=None):
        # SQLAlchemyObjectType automatically adds {x}_collection field when refered via FK
        # But the name is not always sensible, so for any such collection, we add
        # field and resolver
        if collection_name is None:
            collection_name = field_name[:-1].replace("_", "")

        def _factory_resolver(collection_name):
            def inner_func(root, info):
                return getattr(root, f"{collection_name}_collection")
            return inner_func

        def inner_function(cls):
            cls._meta.fields[field_name] = graphene.Field(graphene.List(cls_fnc))
            setattr(cls, f"resolve_{field_name}", _factory_resolver(collection_name))        
            return cls
    
        return inner_function


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
    @add_for_collections("songs", lambda: SongGQL)
    class ComposerGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Composer"]

    
    @register_gql("contact")
    class ContactGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Contact"]
    

    @register_gql("event_gen")
    @add_for_collections("event_occs", lambda: EventOccGQL)
    class EventGenGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["EventGen"]

    
    @register_gql("event_occ")
    @add_for_collections("song_performs", lambda: SongPerformGQL)
    class EventOccGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["EventOcc"]
    
        venue = graphene.Field(lambda: VenueGQL)
        players = graphene.List(lambda: PlayerGQL)
        
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
    @add_for_collections("event_gens", lambda: EventGenGQL)
    @add_for_collections("subgenres", lambda: SubgenreGQL)
    class GenreGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Genre"]


    @register_gql("instrument")
    @add_for_collections("person_instruments", lambda: PersonInstrumentGQL)
    @add_for_collections("setlist_songs", lambda: SetlistSongGQL)
    class InstrumentGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Instrument"]
    

    @register_gql("key")
    @add_for_collections("setlist_songs", lambda: SetlistSongGQL)
    @add_for_collections("songs", lambda: SongGQL)
    @add_for_collections("song_learns", lambda: SongLearnGQL)
    @add_for_collections("song_performs", lambda: SongPerformGQL)
    class KeyGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Key"]
    
        key_name = graphene.String()
    
        def resolve_key_name(root, info):
            return f"{root.root} {root.mode.mode}"


    @register_gql("mode")
    @add_for_collections("keys", lambda: KeyGQL)
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
    @add_for_collections("contacts", lambda: ContactGQL)
    @add_for_collections("event_gens", lambda: EventGenGQL)
    @add_for_collections("person_instruments", lambda: PersonInstrumentGQL)
    class PersonGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Person"]
    
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
    @add_for_collections("song_performers", lambda: SongPerformerGQL)
    class PersonInstrumentGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["PersonInstrument"]
    
        song_performs = graphene.List(lambda: SongPerformGQL)
        events_attended = graphene.List(lambda: EventOccGQL)
        
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
    @add_for_collections("setlist_songs", lambda: SetlistSongGQL)
    class SetlistGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Setlist"]


    @register_gql("setlist_song")
    class SetlistSongGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["SetlistSong"]
    

    @register_gql("song")
    @add_for_collections("charts", lambda: ChartGQL)
    @add_for_collections("ref_recs", lambda: RefRecGQL)
    @add_for_collections("setlist_songs", lambda: SetlistSongGQL)
    @add_for_collections("song_learns", lambda: SongLearnGQL)
    @add_for_collections("song_performs", lambda: SongPerformGQL)
    class SongGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Song"]


    @register_gql("song_learn")
    class SongLearnGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["SongLearn"]


    @register_gql("song_perform")
    @add_for_collections("performance_videos", lambda: PerformanceVideoGQL)
    @add_for_collections("song_performers", lambda: SongPerformerGQL)
    class SongPerformGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["SongPerform"]
    
        song_perform_name = graphene.String()
        players = graphene.List(lambda: PlayerGQL)

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
    @add_for_collections("songs", lambda: SongGQL)
    class SubgenreGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Subgenre"]
    
        subgenre_name = graphene.String()
    
        def resolve_subgenre_name(root, info):
            genre = root.genre.genre
            sub = root.subgenre
            output = genre
            if genre != sub:
                output += ": " + sub
            return output
    

    @register_gql("venue")
    @add_for_collections("hosted_event_series", lambda: EventGenGQL, "eventgen")
    class VenueGQL(SQLAlchemyObjectType):
        class Meta:
            model = model_classes["Venue"]
    
        zip = graphene.Int()
        address_string = graphene.String()
        google_map_string = graphene.String()
    
        def resolve_zip(root, info):
            return format_id_as_str(root.zip)
        
        def resolve_address_string(root, info):
            return f"{root.address}, {root.city}, {root.state}, {VenueGQL.resolve_zip(root, info)}"
    
        def resolve_google_map_string(root, info):
            address_string = VenueGQL.resolve_address_string(root, info)
            return f"https://www.google.com/maps/place/{address_string}".replace(" ", "+")

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
